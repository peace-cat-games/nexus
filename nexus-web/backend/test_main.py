"""Tests for the Nexus Web API."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path to import nexus game engine
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthCheck:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestCreateGame:
    def test_create_default_game(self, client):
        response = client.post("/api/games", json={})
        assert response.status_code == 200
        data = response.json()

        assert "game_id" in data
        assert data["size"] == 5
        assert data["to_move"] == "BLACK"
        assert data["debt_black"] == 0
        assert data["debt_white"] == 0
        assert data["result"] == "ONGOING"
        assert data["p1"] == 2
        assert data["p2"] == 4
        assert len(data["board"]) == 5
        assert len(data["board"][0]) == 5

    def test_create_custom_game(self, client):
        response = client.post("/api/games", json={"size": 3, "p1": 1, "p2": 2})
        assert response.status_code == 200
        data = response.json()

        assert data["size"] == 3
        assert data["p1"] == 1
        assert data["p2"] == 2

    def test_create_game_invalid_size(self, client):
        response = client.post("/api/games", json={"size": 2})
        assert response.status_code == 422  # Validation error


class TestGetGame:
    def test_get_existing_game(self, client):
        # Create a game
        create_response = client.post("/api/games", json={})
        game_id = create_response.json()["game_id"]

        # Get the game
        response = client.get(f"/api/games/{game_id}")
        assert response.status_code == 200
        assert response.json()["game_id"] == game_id

    def test_get_nonexistent_game(self, client):
        response = client.get("/api/games/nonexistent-id")
        assert response.status_code == 404


class TestMakeMove:
    def test_make_valid_move(self, client):
        # Create a game
        create_response = client.post("/api/games", json={"size": 3})
        game_id = create_response.json()["game_id"]

        # Make a move
        response = client.post(f"/api/games/{game_id}/move", json={"row": 1, "col": 1})
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["game_state"]["board"][1][1] == 1  # BLACK stone
        assert data["game_state"]["to_move"] == "WHITE"

    def test_make_move_occupied_point(self, client):
        # Create a game
        create_response = client.post("/api/games", json={"size": 3})
        game_id = create_response.json()["game_id"]

        # Make first move
        client.post(f"/api/games/{game_id}/move", json={"row": 1, "col": 1})

        # Try to place on occupied point
        response = client.post(f"/api/games/{game_id}/move", json={"row": 1, "col": 1})
        assert response.status_code == 400

    def test_make_move_nonexistent_game(self, client):
        response = client.post(
            "/api/games/nonexistent-id/move", json={"row": 0, "col": 0}
        )
        assert response.status_code == 404


class TestDeleteGame:
    def test_delete_existing_game(self, client):
        # Create a game
        create_response = client.post("/api/games", json={})
        game_id = create_response.json()["game_id"]

        # Delete the game
        response = client.delete(f"/api/games/{game_id}")
        assert response.status_code == 200

        # Verify it's gone
        get_response = client.get(f"/api/games/{game_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_game(self, client):
        response = client.delete("/api/games/nonexistent-id")
        assert response.status_code == 404


class TestGameFlow:
    def test_complete_line_wins(self, client):
        """Test that completing a line with zero debt wins the game."""
        # Create a 3x3 game
        create_response = client.post("/api/games", json={"size": 3})
        game_id = create_response.json()["game_id"]

        # Play moves to complete a row for Black
        # Black plays: (0,0), (0,1), (0,2)
        # White plays: (1,0), (1,1)
        moves = [
            (0, 0),  # Black
            (1, 0),  # White
            (0, 1),  # Black
            (1, 1),  # White
            (0, 2),  # Black - completes row 0
        ]

        for row, col in moves:
            response = client.post(
                f"/api/games/{game_id}/move", json={"row": row, "col": col}
            )
            assert response.status_code == 200

        # Check final state
        final_state = response.json()["game_state"]
        assert final_state["result"] == "BLACK_WIN"
