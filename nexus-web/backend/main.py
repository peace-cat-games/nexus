"""
Nexus Web API - FastAPI backend for the Nexus game.
"""

import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add parent directory to path to import nexus game engine
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nexus.game import NexusGame, Player, GameResult, EMPTY, BLACK, WHITE
from nexus.exceptions import (
    IllegalMoveError,
    GameOverError,
    SuicideError,
    OccupiedPointError,
    ForcedUnblockingImpossibleError,
    KoError,
)


app = FastAPI(
    title="Nexus Game API",
    description="REST API for playing the Nexus board game",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory game storage
games: Dict[str, NexusGame] = {}


class NewGameRequest(BaseModel):
    size: int = Field(default=5, ge=3, le=19, description="Board size (3-19)")
    p1: int = Field(default=2, ge=1, description="Debt per captured stone")
    p2: int = Field(default=4, ge=1, description="Debt per forced unblock stone")


class MoveRequest(BaseModel):
    row: int = Field(ge=0, description="Row coordinate")
    col: int = Field(ge=0, description="Column coordinate")
    stones_to_remove: Optional[List[List[int]]] = Field(
        default=None, description="Stones to remove for debt resolution [[r,c], ...]"
    )


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


class MoveResponse(BaseModel):
    success: bool
    game_state: GameStateResponse
    unblocked_stones: Optional[List[List[int]]] = None
    message: Optional[str] = None


def game_to_response(game_id: str, game: NexusGame) -> GameStateResponse:
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
    )


@app.post("/api/games", response_model=GameStateResponse)
def create_game(request: NewGameRequest) -> GameStateResponse:
    """Create a new game."""
    game_id = str(uuid4())
    game = NexusGame(size=request.size, p1=request.p1, p2=request.p2)
    games[game_id] = game
    return game_to_response(game_id, game)


@app.get("/api/games/{game_id}", response_model=GameStateResponse)
def get_game(game_id: str) -> GameStateResponse:
    """Get the current state of a game."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    return game_to_response(game_id, games[game_id])


@app.post("/api/games/{game_id}/move", response_model=MoveResponse)
def make_move(game_id: str, request: MoveRequest) -> MoveResponse:
    """Make a move in the game."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[game_id]

    # Convert stones_to_remove to tuples
    stones_to_remove = None
    if request.stones_to_remove:
        stones_to_remove = [(s[0], s[1]) for s in request.stones_to_remove]

    try:
        unblocked = game.make_move(request.row, request.col, stones_to_remove)
        unblocked_list = [[r, c] for r, c in unblocked] if unblocked else None

        return MoveResponse(
            success=True,
            game_state=game_to_response(game_id, game),
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
    except ForcedUnblockingImpossibleError as e:
        # Game ends, update response
        return MoveResponse(
            success=False,
            game_state=game_to_response(game_id, game),
            message=str(e),
        )


@app.get("/api/games/{game_id}/debt-resolution")
def get_debt_resolution_info(game_id: str) -> Dict[str, Any]:
    """
    Get information about pending debt resolution.
    Returns the number of stones that need to be removed if completion is imminent.
    """
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[game_id]
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


class CheckMoveRequest(BaseModel):
    row: int = Field(ge=0, description="Row coordinate")
    col: int = Field(ge=0, description="Column coordinate")


@app.post("/api/games/{game_id}/check-move")
def check_move(game_id: str, request: CheckMoveRequest) -> Dict[str, Any]:
    """
    Check if a move would trigger debt resolution and calculate requirements.
    This allows the frontend to prompt for stone selection before making the move.
    """
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[game_id]

    # Use the game's check method
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

    # Include the stone being placed - it can also be removed during debt resolution
    player_stones_with_new = player_stones + [(request.row, request.col)]

    # Check if move would cause bankruptcy (including the new stone)
    would_be_bankrupt = len(player_stones_with_new) < stones_needed

    return {
        "requires_debt_resolution": True,
        "stones_to_remove": stones_needed,
        "player_stones": [[r, c] for r, c in player_stones_with_new],
        "would_be_bankrupt": would_be_bankrupt,
    }


@app.delete("/api/games/{game_id}")
def delete_game(game_id: str) -> Dict[str, str]:
    """Delete a game."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    del games[game_id]
    return {"message": "Game deleted"}


@app.get("/api/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
