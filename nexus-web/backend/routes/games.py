"""
Game management routes for Nexus Web (lobby, seeks, user games).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
from auth import get_current_user_required
from models import User, Game, Seek, GameMode, GameResult

router = APIRouter(prefix="/api", tags=["games"])


class SeekCreate(BaseModel):
    mode: str  # "realtime" or "correspondence"
    board_size: int = 5
    p1: int = 2
    p2: int = 4


class SeekResponse(BaseModel):
    id: int
    owner_id: int
    owner_username: str
    mode: str
    board_size: int
    p1: int
    p2: int

    class Config:
        from_attributes = True


class GameListResponse(BaseModel):
    id: str
    player_black_id: Optional[int]
    player_black_username: Optional[str]
    player_white_id: Optional[int]
    player_white_username: Optional[str]
    mode: str
    board_size: int
    result: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("/me/games", response_model=List[GameListResponse])
def get_my_games(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Get all games for the current user."""
    games = (
        db.query(Game)
        .filter(
            or_(
                Game.player_black_id == current_user.id,
                Game.player_white_id == current_user.id,
            )
        )
        .order_by(Game.updated_at.desc())
        .all()
    )

    result = []
    for game in games:
        result.append(
            GameListResponse(
                id=game.id,
                player_black_id=game.player_black_id,
                player_black_username=(
                    game.player_black.username if game.player_black else None
                ),
                player_white_id=game.player_white_id,
                player_white_username=(
                    game.player_white.username if game.player_white else None
                ),
                mode=game.mode.value,
                board_size=game.board_size,
                result=game.result.value,
                created_at=game.created_at.isoformat(),
                updated_at=game.updated_at.isoformat(),
            )
        )
    return result


@router.post("/nexus/seeks", response_model=SeekResponse)
def create_seek(
    seek_data: SeekCreate,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Create a new game seek."""
    # Validate mode
    try:
        mode = GameMode(seek_data.mode)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mode. Must be 'realtime' or 'correspondence'",
        )

    # Check if user already has an open seek
    existing_seek = db.query(Seek).filter(Seek.owner_id == current_user.id).first()
    if existing_seek:
        # Delete the existing seek and create a new one
        db.delete(existing_seek)

    # Create the seek
    seek = Seek(
        owner_id=current_user.id,
        mode=mode,
        board_size=seek_data.board_size,
        p1=seek_data.p1,
        p2=seek_data.p2,
    )
    db.add(seek)
    db.commit()
    db.refresh(seek)

    return SeekResponse(
        id=seek.id,
        owner_id=seek.owner_id,
        owner_username=current_user.username,
        mode=seek.mode.value,
        board_size=seek.board_size,
        p1=seek.p1,
        p2=seek.p2,
    )


@router.get("/nexus/seeks", response_model=List[SeekResponse])
def list_seeks(
    current_user: Optional[User] = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """List all open seeks (excluding current user's)."""
    seeks = db.query(Seek).filter(Seek.owner_id != current_user.id).all()

    result = []
    for seek in seeks:
        result.append(
            SeekResponse(
                id=seek.id,
                owner_id=seek.owner_id,
                owner_username=seek.owner.username,
                mode=seek.mode.value,
                board_size=seek.board_size,
                p1=seek.p1,
                p2=seek.p2,
            )
        )
    return result


@router.delete("/nexus/seeks/{seek_id}")
def cancel_seek(
    seek_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Cancel a seek."""
    seek = db.query(Seek).filter(Seek.id == seek_id).first()
    if not seek:
        raise HTTPException(status_code=404, detail="Seek not found")
    if seek.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your seek")

    db.delete(seek)
    db.commit()
    return {"message": "Seek cancelled"}


@router.get("/nexus/seeks/mine", response_model=Optional[SeekResponse])
def get_my_seek(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Get the current user's open seek, if any."""
    seek = db.query(Seek).filter(Seek.owner_id == current_user.id).first()
    if not seek:
        return None

    return SeekResponse(
        id=seek.id,
        owner_id=seek.owner_id,
        owner_username=current_user.username,
        mode=seek.mode.value,
        board_size=seek.board_size,
        p1=seek.p1,
        p2=seek.p2,
    )
