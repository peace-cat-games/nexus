"""
Nexus game engine routes for Nexus Web.
"""

import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user, get_current_user_required
from models import User, Game, Seek, GameMode, GameResult as DBGameResult

# Add parent directory to path to import nexus game engine
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from nexus.game import NexusGame, Player, GameResult, EMPTY, BLACK, WHITE
from nexus.exceptions import (
    IllegalMoveError,
    GameOverError,
    SuicideError,
    OccupiedPointError,
    ForcedUnblockingImpossibleError,
    KoError,
)

router = APIRouter(prefix="/api/nexus", tags=["nexus"])


class NewGameRequest(BaseModel):
    size: int = Field(default=5, ge=3, le=19, description="Board size (3-19)")
    p1: int = Field(default=2, ge=1, description="Debt per captured stone")
    p2: int = Field(default=4, ge=1, description="Debt per forced unblock stone")
    mode: str = Field(
        default="realtime", description="Game mode: realtime or correspondence"
    )


class MoveRequest(BaseModel):
    row: int = Field(ge=0, description="Row coordinate")
    col: int = Field(ge=0, description="Column coordinate")
    stones_to_remove: Optional[List[List[int]]] = Field(
        default=None, description="Stones to remove for debt resolution [[r,c], ...]"
    )
    unblocking_stones: Optional[List[List[int]]] = Field(
        default=None,
        description="Opponent stones to remove for forced unblocking [[r,c], ...]",
    )


class CheckMoveRequest(BaseModel):
    row: int = Field(ge=0, description="Row coordinate")
    col: int = Field(ge=0, description="Column coordinate")


class GameStateResponse(BaseModel):
    game_id: str
    size: int
    board: List[List[int]]
    to_move: str
    debt_black: int
    debt_white: int
    result: str
    legal_moves: List[List[int]]
    p1: int
    p2: int
    mode: str
    player_black_id: Optional[int] = None
    player_black_username: Optional[str] = None
    player_white_id: Optional[int] = None
    player_white_username: Optional[str] = None


class MoveResponse(BaseModel):
    success: bool
    game_state: GameStateResponse
    unblocked_stones: Optional[List[List[int]]] = None
    message: Optional[str] = None


def serialize_game(game: NexusGame) -> str:
    """Serialize a NexusGame to JSON."""
    # Convert position_history tuples to JSON-serializable format
    # Position history is a set of (board_tuple, debt_diff) tuples
    position_history = []
    for board_tuple, debt_diff in game.state.position_history:
        position_history.append([list(row) for row in board_tuple] + [debt_diff])
    return json.dumps(
        {
            "board": game.board,
            "to_move": game.to_move.name,
            "debt_black": game.state.debt_black,
            "debt_white": game.state.debt_white,
            "result": game.result.name,
            "position_history": position_history,
        }
    )


def deserialize_game(state_blob: str, size: int, p1: int, p2: int) -> NexusGame:
    """Deserialize a NexusGame from JSON."""
    data = json.loads(state_blob)
    game = NexusGame(size=size, p1=p1, p2=p2)
    game.state.board[:] = data["board"]
    game.state.to_move = Player[data["to_move"]]
    game.state.debt_black = data["debt_black"]
    game.state.debt_white = data["debt_white"]
    game.state.result = GameResult[data["result"]]
    # Convert position_history back to set of tuples
    position_history = set()
    for item in data["position_history"]:
        # Last element is debt_diff, rest is board rows
        board_tuple = tuple(tuple(row) for row in item[:-1])
        debt_diff = item[-1]
        position_history.add((board_tuple, debt_diff))
    game.state.position_history = position_history
    return game


def game_to_response(
    game_id: str, game: NexusGame, db_game: Optional[Game] = None
) -> GameStateResponse:
    """Convert a NexusGame to a GameStateResponse."""
    return GameStateResponse(
        game_id=game_id,
        size=game.size,
        board=game.board,
        to_move=game.to_move.name,
        debt_black=game.state.debt_black,
        debt_white=game.state.debt_white,
        result=game.result.name,
        legal_moves=[[r, c] for r, c in game.legal_moves()],
        p1=game.state.p1,
        p2=game.state.p2,
        mode=db_game.mode.value if db_game else "realtime",
        player_black_id=db_game.player_black_id if db_game else None,
        player_black_username=(
            db_game.player_black.username if db_game and db_game.player_black else None
        ),
        player_white_id=db_game.player_white_id if db_game else None,
        player_white_username=(
            db_game.player_white.username if db_game and db_game.player_white else None
        ),
    )


@router.post("/games", response_model=GameStateResponse)
def create_game(
    request: NewGameRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameStateResponse:
    """Create a new game."""
    game_id = str(uuid4())
    game = NexusGame(size=request.size, p1=request.p1, p2=request.p2)

    try:
        mode = GameMode(request.mode)
    except ValueError:
        mode = GameMode.REALTIME

    # Create database record
    db_game = Game(
        id=game_id,
        player_black_id=current_user.id if current_user else None,
        player_white_id=None,
        mode=mode,
        board_size=request.size,
        p1=request.p1,
        p2=request.p2,
        state_blob=serialize_game(game),
        result=DBGameResult.ONGOING,
    )
    db.add(db_game)
    db.commit()
    db.refresh(db_game)

    return game_to_response(game_id, game, db_game)


@router.post("/seeks/{seek_id}/accept", response_model=GameStateResponse)
def accept_seek(
    seek_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
) -> GameStateResponse:
    """Accept a seek and create a game."""
    seek = db.query(Seek).filter(Seek.id == seek_id).first()
    if not seek:
        raise HTTPException(status_code=404, detail="Seek not found")

    if seek.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot accept your own seek")

    # Create the game
    game_id = str(uuid4())
    game = NexusGame(size=seek.board_size, p1=seek.p1, p2=seek.p2)

    # Seek owner plays Black, acceptor plays White
    db_game = Game(
        id=game_id,
        player_black_id=seek.owner_id,
        player_white_id=current_user.id,
        mode=seek.mode,
        board_size=seek.board_size,
        p1=seek.p1,
        p2=seek.p2,
        state_blob=serialize_game(game),
        result=DBGameResult.ONGOING,
    )
    db.add(db_game)

    # Delete the seek
    db.delete(seek)
    db.commit()
    db.refresh(db_game)

    return game_to_response(game_id, game, db_game)


@router.get("/games/{game_id}", response_model=GameStateResponse)
def get_game(game_id: str, db: Session = Depends(get_db)) -> GameStateResponse:
    """Get the current state of a game."""
    db_game = db.query(Game).filter(Game.id == game_id).first()
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    game = deserialize_game(
        db_game.state_blob, db_game.board_size, db_game.p1, db_game.p2
    )
    return game_to_response(game_id, game, db_game)


@router.post("/games/{game_id}/move", response_model=MoveResponse)
def make_move(
    game_id: str,
    request: MoveRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MoveResponse:
    """Make a move in the game."""
    db_game = db.query(Game).filter(Game.id == game_id).first()
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    game = deserialize_game(
        db_game.state_blob, db_game.board_size, db_game.p1, db_game.p2
    )

    # Check if it's the current user's turn (if authenticated and playing)
    if current_user:
        if game.to_move == Player.BLACK and db_game.player_black_id != current_user.id:
            if db_game.player_black_id is not None:
                raise HTTPException(status_code=403, detail="Not your turn")
        elif (
            game.to_move == Player.WHITE and db_game.player_white_id != current_user.id
        ):
            if db_game.player_white_id is not None:
                raise HTTPException(status_code=403, detail="Not your turn")

    # Convert stones_to_remove to tuples
    stones_to_remove = None
    if request.stones_to_remove:
        stones_to_remove = [(s[0], s[1]) for s in request.stones_to_remove]

    # Convert unblocking_stones to tuples
    unblocking_stones = None
    if request.unblocking_stones:
        unblocking_stones = [(s[0], s[1]) for s in request.unblocking_stones]

    try:
        unblocked = game.make_move(
            request.row, request.col, stones_to_remove, unblocking_stones
        )
        unblocked_list = [[r, c] for r, c in unblocked] if unblocked else None

        # Update database
        db_game.state_blob = serialize_game(game)
        if game.result == GameResult.BLACK_WIN:
            db_game.result = DBGameResult.BLACK_WIN
        elif game.result == GameResult.WHITE_WIN:
            db_game.result = DBGameResult.WHITE_WIN
        db.commit()

        return MoveResponse(
            success=True,
            game_state=game_to_response(game_id, game, db_game),
            unblocked_stones=unblocked_list,
        )
    except GameOverError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OccupiedPointError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SuicideError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IllegalMoveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ForcedUnblockingImpossibleError as e:
        # Update database with game result
        db_game.state_blob = serialize_game(game)
        if game.result == GameResult.BLACK_WIN:
            db_game.result = DBGameResult.BLACK_WIN
        elif game.result == GameResult.WHITE_WIN:
            db_game.result = DBGameResult.WHITE_WIN
        db.commit()

        return MoveResponse(
            success=False,
            game_state=game_to_response(game_id, game, db_game),
            message=str(e),
        )


@router.get("/games/{game_id}/debt-resolution")
def get_debt_resolution_info(
    game_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get information about pending debt resolution."""
    db_game = db.query(Game).filter(Game.id == game_id).first()
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    game = deserialize_game(
        db_game.state_blob, db_game.board_size, db_game.p1, db_game.p2
    )
    player = game.to_move

    debt_p = game.state.get_debt(player)
    debt_q = game.state.get_debt(player.opponent())
    net = debt_p - debt_q

    player_stones = game._get_player_stones(player)

    return {
        "player_debt": debt_p,
        "opponent_debt": debt_q,
        "net_debt": net,
        "stones_to_remove": max(0, net),
        "player_stones": [[r, c] for r, c in player_stones],
        "can_pay": len(player_stones) >= max(0, net),
    }


@router.get("/games/{game_id}/unblocking-options")
def get_unblocking_options(
    game_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get available forced unblocking options."""
    db_game = db.query(Game).filter(Game.id == game_id).first()
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    game = deserialize_game(
        db_game.state_blob, db_game.board_size, db_game.p1, db_game.p2
    )
    legal = game.legal_moves()

    if legal:
        return {
            "needs_unblocking": False,
            "options": [],
            "debt_per_stone": game.state.p2,
        }

    options = game._find_all_minimal_unblocking_sets()

    if not options:
        return {
            "needs_unblocking": True,
            "options": [],
            "debt_per_stone": game.state.p2,
            "impossible": True,
        }

    return {
        "needs_unblocking": True,
        "options": [[[r, c] for r, c in opt] for opt in options],
        "debt_per_stone": game.state.p2,
        "total_debt": len(options[0]) * game.state.p2,
    }


@router.post("/games/{game_id}/check-move")
def check_move(
    game_id: str, request: CheckMoveRequest, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Check if a move would trigger debt resolution."""
    db_game = db.query(Game).filter(Game.id == game_id).first()
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    game = deserialize_game(
        db_game.state_blob, db_game.board_size, db_game.p1, db_game.p2
    )

    stones_needed = game.check_completion_debt_resolution(request.row, request.col)

    if stones_needed is None:
        return {
            "requires_debt_resolution": False,
            "stones_to_remove": 0,
            "player_stones": [],
            "would_be_bankrupt": False,
        }

    player = game.to_move
    player_stones = game._get_player_stones(player)
    player_stones_with_new = player_stones + [(request.row, request.col)]
    would_be_bankrupt = len(player_stones_with_new) < stones_needed

    return {
        "requires_debt_resolution": True,
        "stones_to_remove": stones_needed,
        "player_stones": [[r, c] for r, c in player_stones_with_new],
        "would_be_bankrupt": would_be_bankrupt,
    }


@router.delete("/games/{game_id}")
def delete_game(
    game_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Delete a game (only if you're a player)."""
    db_game = db.query(Game).filter(Game.id == game_id).first()
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    if (
        db_game.player_black_id != current_user.id
        and db_game.player_white_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Not your game")

    db.delete(db_game)
    db.commit()
    return {"message": "Game deleted"}
