"""Routes package for Nexus Web."""

from .auth import router as auth_router
from .games import router as games_router
from .nexus import router as nexus_router

__all__ = ["auth_router", "games_router", "nexus_router"]
