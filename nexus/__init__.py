"""
Nexus - A strategic board game combining Go and Tic-Tac-Toe mechanics with debt economics.
"""

from .game import (
    NexusGame,
    GameState,
    Player,
    GameResult,
    EMPTY,
    BLACK,
    WHITE,
    player_to_stone,
    stone_to_player,
)
from .exceptions import (
    NexusError,
    IllegalMoveError,
    GameOverError,
    SuicideError,
    OccupiedPointError,
    ForcedUnblockingImpossibleError,
)

__all__ = [
    "NexusGame",
    "GameState",
    "Player",
    "GameResult",
    "EMPTY",
    "BLACK",
    "WHITE",
    "player_to_stone",
    "stone_to_player",
    "NexusError",
    "IllegalMoveError",
    "GameOverError",
    "SuicideError",
    "OccupiedPointError",
    "ForcedUnblockingImpossibleError",
]
