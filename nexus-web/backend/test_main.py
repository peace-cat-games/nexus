"""Tests for the Nexus Web API."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path to import nexus game engine
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app
from database import Base, engine


@pytest.fixture(autouse=True)
def setup_database():
    """Set up a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_client():
    """Create a client with authentication."""
    with TestClient(app) as client:
        # Register a user
        register_response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpass123",
            },
        )
        token = register_response.json()["access_token"]

        # Set the auth header for all subsequent requests
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client


class TestHealthCheck:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestAuthentication:
    def test_register_success(self, client):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_username(self, client):
        # Register first user
        client.post(
            "/api/auth/register",
            json={
                "username": "sameuser",
                "email": "first@example.com",
                "password": "password123",
            },
        )

        # Try to register with same username
        response = client.post(
            "/api/auth/register",
            json={
                "username": "sameuser",
                "email": "second@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    def test_register_duplicate_email(self, client):
        # Register first user
        client.post(
            "/api/auth/register",
            json={
                "username": "user1",
                "email": "same@example.com",
                "password": "password123",
            },
        )

        # Try to register with same email
        response = client.post(
            "/api/auth/register",
            json={
                "username": "user2",
                "email": "same@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_short_password(self, client):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "123",
            },
        )
        assert response.status_code == 400
        assert "at least 6 characters" in response.json()["detail"]

    def test_login_success(self, client):
        # Register first
        client.post(
            "/api/auth/register",
            json={
                "username": "loginuser",
                "email": "login@example.com",
                "password": "password123",
            },
        )

        # Login
        response = client.post(
            "/api/auth/login", json={"username": "loginuser", "password": "password123"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client):
        # Register first
        client.post(
            "/api/auth/register",
            json={
                "username": "loginuser2",
                "email": "login2@example.com",
                "password": "password123",
            },
        )

        # Login with wrong password
        response = client.post(
            "/api/auth/login",
            json={"username": "loginuser2", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_get_me(self, auth_client):
        response = auth_client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_get_me_unauthenticated(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestCreateGame:
    def test_create_default_game(self, auth_client):
        response = auth_client.post("/api/nexus/games", json={})
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

    def test_create_custom_game(self, auth_client):
        response = auth_client.post(
            "/api/nexus/games", json={"size": 3, "p1": 1, "p2": 2}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["size"] == 3
        assert data["p1"] == 1
        assert data["p2"] == 2

    def test_create_game_invalid_size(self, auth_client):
        response = auth_client.post("/api/nexus/games", json={"size": 2})
        assert response.status_code == 422  # Validation error


class TestGetGame:
    def test_get_existing_game(self, auth_client):
        # Create a game
        create_response = auth_client.post("/api/nexus/games", json={})
        game_id = create_response.json()["game_id"]

        # Get the game
        response = auth_client.get(f"/api/nexus/games/{game_id}")
        assert response.status_code == 200
        assert response.json()["game_id"] == game_id

    def test_get_nonexistent_game(self, auth_client):
        response = auth_client.get("/api/nexus/games/nonexistent-id")
        assert response.status_code == 404


class TestMakeMove:
    def test_make_valid_move(self, auth_client):
        # Create a game
        create_response = auth_client.post("/api/nexus/games", json={"size": 3})
        game_id = create_response.json()["game_id"]

        # Make a move
        response = auth_client.post(
            f"/api/nexus/games/{game_id}/move", json={"row": 1, "col": 1}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["game_state"]["board"][1][1] == 1  # BLACK stone
        assert data["game_state"]["to_move"] == "WHITE"

    def test_make_move_occupied_point(self, auth_client):
        # Create a game
        create_response = auth_client.post("/api/nexus/games", json={"size": 3})
        game_id = create_response.json()["game_id"]

        # Make first move
        auth_client.post(f"/api/nexus/games/{game_id}/move", json={"row": 1, "col": 1})

        # Try to place on occupied point (White's turn, but still occupied)
        response = auth_client.post(
            f"/api/nexus/games/{game_id}/move", json={"row": 1, "col": 1}
        )
        assert response.status_code == 400

    def test_make_move_nonexistent_game(self, auth_client):
        response = auth_client.post(
            "/api/nexus/games/nonexistent-id/move", json={"row": 0, "col": 0}
        )
        assert response.status_code == 404


class TestSeeks:
    def test_create_seek(self, auth_client):
        response = auth_client.post(
            "/api/nexus/seeks", json={"mode": "realtime", "board_size": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "realtime"
        assert data["board_size"] == 5
        assert data["owner_username"] == "testuser"

    def test_get_seeks(self, auth_client):
        # Create a seek with auth_client (testuser)
        auth_client.post("/api/nexus/seeks", json={"mode": "realtime", "board_size": 5})

        # Create another client and register another user
        with TestClient(app) as other_client:
            other_client.post(
                "/api/auth/register",
                json={
                    "username": "otheruser",
                    "email": "other@example.com",
                    "password": "password123",
                },
            )
            login_response = other_client.post(
                "/api/auth/login",
                json={"username": "otheruser", "password": "password123"},
            )
            token = login_response.json()["access_token"]
            other_client.headers.update({"Authorization": f"Bearer {token}"})

            # Get seeks as other user (should see the seek)
            response = other_client.get("/api/nexus/seeks")
            assert response.status_code == 200
            seeks = response.json()
            assert len(seeks) == 1
            assert seeks[0]["owner_username"] == "testuser"

    def test_accept_seek(self, auth_client):
        # Create a seek with auth_client (testuser)
        seek_response = auth_client.post(
            "/api/nexus/seeks", json={"mode": "realtime", "board_size": 5}
        )
        seek_id = seek_response.json()["id"]

        # Create another client and register another user
        with TestClient(app) as other_client:
            other_client.post(
                "/api/auth/register",
                json={
                    "username": "joiner",
                    "email": "joiner@example.com",
                    "password": "password123",
                },
            )
            login_response = other_client.post(
                "/api/auth/login",
                json={"username": "joiner", "password": "password123"},
            )
            token = login_response.json()["access_token"]
            other_client.headers.update({"Authorization": f"Bearer {token}"})

            # Accept the seek
            response = other_client.post(f"/api/nexus/seeks/{seek_id}/accept")
            assert response.status_code == 200
            game = response.json()
            assert game["player_black_username"] == "testuser"
            assert game["player_white_username"] == "joiner"
            assert game["result"] == "ONGOING"

    def test_cannot_accept_own_seek(self, auth_client):
        # Create a seek
        seek_response = auth_client.post(
            "/api/nexus/seeks", json={"mode": "realtime", "board_size": 5}
        )
        seek_id = seek_response.json()["id"]

        # Try to accept own seek
        response = auth_client.post(f"/api/nexus/seeks/{seek_id}/accept")
        assert response.status_code == 400
        assert "own seek" in response.json()["detail"]


class TestMyGames:
    def test_get_my_games(self, auth_client):
        # Create a game
        auth_client.post("/api/nexus/games", json={})

        # Get my games
        response = auth_client.get("/api/me/games")
        assert response.status_code == 200
        games = response.json()
        assert len(games) == 1

    def test_get_my_games_unauthenticated(self, client):
        response = client.get("/api/me/games")
        assert response.status_code == 401


class TestGameFlow:
    def test_complete_line_wins(self, auth_client):
        """Test that completing a line with zero debt wins the game."""
        # Create a 3x3 game
        create_response = auth_client.post("/api/nexus/games", json={"size": 3})
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
            response = auth_client.post(
                f"/api/nexus/games/{game_id}/move", json={"row": row, "col": col}
            )
            assert response.status_code == 200

        # Check final state
        final_state = response.json()["game_state"]
        assert final_state["result"] == "BLACK_WIN"

    def test_realtime_vs_correspondence_mode(self, auth_client):
        """Test creating games with different modes."""
        # Create realtime game
        rt_response = auth_client.post("/api/nexus/games", json={"mode": "realtime"})
        assert rt_response.status_code == 200
        assert rt_response.json()["mode"] == "realtime"

        # Create correspondence game
        corr_response = auth_client.post(
            "/api/nexus/games", json={"mode": "correspondence"}
        )
        assert corr_response.status_code == 200
        assert corr_response.json()["mode"] == "correspondence"
