"""Custom exceptions for the Nexus game engine."""


class NexusError(Exception):
    """Base exception for all Nexus-related errors."""

    pass


class IllegalMoveError(NexusError):
    """Raised when an attempted move violates game rules."""

    pass


class GameOverError(NexusError):
    """Raised when attempting to make a move after the game has ended."""

    pass


class SuicideError(IllegalMoveError):
    """Raised when a move would result in self-capture without capturing any opponent stones."""

    pass


class OccupiedPointError(IllegalMoveError):
    """Raised when attempting to place a stone on an already-occupied point."""

    pass


class ForcedUnblockingImpossibleError(NexusError):
    """Raised when no set of opponent stones can be removed to create a legal move."""

    pass


class KoError(IllegalMoveError):
    """Raised when a move would violate the ko (superko) rule by repeating a previous position."""

    pass
