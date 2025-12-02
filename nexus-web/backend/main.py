"""
Nexus Web API - FastAPI backend for the Nexus game.
"""

import json
from typing import Dict, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routes import auth_router, games_router, nexus_router


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        # game_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = set()
        self.active_connections[game_id].add(websocket)

    def disconnect(self, websocket: WebSocket, game_id: str):
        if game_id in self.active_connections:
            self.active_connections[game_id].discard(websocket)
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def broadcast_to_game(self, game_id: str, message: dict):
        if game_id in self.active_connections:
            message_json = json.dumps(message)
            for connection in self.active_connections[game_id].copy():
                try:
                    await connection.send_text(message_json)
                except Exception:
                    self.disconnect(connection, game_id)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


app = FastAPI(
    title="Nexus Game API",
    description="REST API for playing the Nexus board game",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(games_router)
app.include_router(nexus_router)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws/game/{game_id}")
async def websocket_game(websocket: WebSocket, game_id: str):
    """WebSocket endpoint for real-time game updates."""
    await manager.connect(websocket, game_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Parse and broadcast move updates
            try:
                message = json.loads(data)
                if message.get("type") == "move":
                    # Broadcast to all connected clients
                    await manager.broadcast_to_game(game_id, message)
                elif message.get("type") == "game_update":
                    await manager.broadcast_to_game(game_id, message)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)


# Expose manager for routes to use
def get_connection_manager():
    return manager


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
