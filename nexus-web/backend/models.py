"""
SQLAlchemy models for Nexus Web.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
import enum

from database import Base


class GameMode(str, enum.Enum):
    REALTIME = "realtime"
    CORRESPONDENCE = "correspondence"


class GameResult(str, enum.Enum):
    ONGOING = "ongoing"
    BLACK_WIN = "black_win"
    WHITE_WIN = "white_win"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    games_as_black = relationship(
        "Game", foreign_keys="Game.player_black_id", back_populates="player_black"
    )
    games_as_white = relationship(
        "Game", foreign_keys="Game.player_white_id", back_populates="player_white"
    )
    seeks = relationship("Seek", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Game(Base):
    __tablename__ = "games"

    id = Column(String(36), primary_key=True, index=True)
    player_black_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    player_white_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    mode = Column(SQLEnum(GameMode), nullable=False)
    board_size = Column(Integer, nullable=False, default=5)
    p1 = Column(Integer, nullable=False, default=2)
    p2 = Column(Integer, nullable=False, default=4)
    state_blob = Column(Text, nullable=False)  # JSON serialized game state
    result = Column(SQLEnum(GameResult), nullable=False, default=GameResult.ONGOING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    player_black = relationship(
        "User", foreign_keys=[player_black_id], back_populates="games_as_black"
    )
    player_white = relationship(
        "User", foreign_keys=[player_white_id], back_populates="games_as_white"
    )

    def __repr__(self):
        return f"<Game(id='{self.id}', mode={self.mode}, result={self.result})>"


class Seek(Base):
    __tablename__ = "seeks"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mode = Column(SQLEnum(GameMode), nullable=False)
    board_size = Column(Integer, nullable=False, default=5)
    p1 = Column(Integer, nullable=False, default=2)
    p2 = Column(Integer, nullable=False, default=4)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="seeks")

    def __repr__(self):
        return f"<Seek(id={self.id}, owner_id={self.owner_id}, mode={self.mode}, board_size={self.board_size})>"
