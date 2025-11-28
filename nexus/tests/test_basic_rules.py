"""Tests for basic game rules: initialization, placement, and Go legality."""

import pytest
from nexus import (
    NexusGame,
    Player,
    GameResult,
    EMPTY,
    BLACK,
    WHITE,
    SuicideError,
    OccupiedPointError,
)


class TestGameInitialization:
    """Tests for game initialization."""

    def test_new_game_empty_board(self):
        """A new game should have an empty board."""
        game = NexusGame(size=5)
        for r in range(5):
            for c in range(5):
                assert game.board[r][c] == EMPTY

    def test_new_game_black_to_move(self):
        """Black should move first in a new game."""
        game = NexusGame(size=5)
        assert game.to_move == Player.BLACK

    def test_new_game_ongoing(self):
        """A new game should have ONGOING result."""
        game = NexusGame(size=5)
        assert game.result == GameResult.ONGOING

    def test_new_game_zero_debt(self):
        """Both players should start with zero debt."""
        game = NexusGame(size=5)
        assert game.state.debt_black == 0
        assert game.state.debt_white == 0

    def test_custom_size(self):
        """Board should be created with custom size."""
        game = NexusGame(size=9)
        assert game.size == 9
        assert len(game.board) == 9
        assert len(game.board[0]) == 9


class TestBasicPlacement:
    """Tests for basic stone placement."""

    def test_place_on_empty(self):
        """Placing a stone on an empty intersection should be legal."""
        game = NexusGame(size=5)
        legal = game.legal_moves()
        assert (0, 0) in legal
        assert (2, 2) in legal
        assert len(legal) == 25  # All points are legal initially

    def test_place_stone_updates_board(self):
        """Placing a stone should update the board."""
        game = NexusGame(size=5)
        game.apply_move(2, 2)
        assert game.board[2][2] == BLACK

    def test_place_stone_changes_turn(self):
        """Placing a stone should pass turn to opponent."""
        game = NexusGame(size=5)
        game.apply_move(2, 2)
        assert game.to_move == Player.WHITE

    def test_place_stone_no_debt(self):
        """Placing a stone without capture should not add debt."""
        game = NexusGame(size=5)
        game.apply_move(2, 2)
        assert game.state.debt_black == 0
        assert game.state.debt_white == 0

    def test_cannot_place_on_occupied(self):
        """Cannot place a stone on an occupied intersection."""
        game = NexusGame(size=5)
        game.apply_move(2, 2)  # Black places
        with pytest.raises(OccupiedPointError):
            game.apply_move(2, 2)  # White tries same spot

    def test_multiple_moves(self):
        """Multiple moves should alternate between players."""
        game = NexusGame(size=5)
        game.apply_move(0, 0)  # Black
        assert game.board[0][0] == BLACK
        game.apply_move(1, 1)  # White
        assert game.board[1][1] == WHITE
        game.apply_move(2, 2)  # Black
        assert game.board[2][2] == BLACK


class TestSuicideRule:
    """Tests for the suicide rule (Go legality)."""

    def test_simple_suicide_rejected(self):
        """A move that creates a group with no liberties (without capture) is illegal."""
        game = NexusGame(size=3)
        # Create a corner suicide situation
        # White surrounds the corner
        #   0 1 2
        # 0 . O .
        # 1 O . .
        # 2 . . .
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY],
                [WHITE, EMPTY, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # Black cannot play at (0,0) - it would be suicide
        assert (0, 0) not in game.legal_moves()

        with pytest.raises(SuicideError):
            game.apply_move(0, 0)

    def test_edge_suicide_rejected(self):
        """Suicide on the edge is also rejected."""
        game = NexusGame(size=3)
        # Position where (0,1) is surrounded by White and edge
        #   0 1 2
        # 0 O . O
        # 1 . O .
        # 2 . . .
        game.set_position(
            [
                [WHITE, EMPTY, WHITE],
                [EMPTY, WHITE, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # Black at (0,1) has neighbors: edge (invalid), (0,0)=W, (0,2)=W, (1,1)=W
        # All occupied by White or edge, so no liberties -> suicide
        assert (0, 1) not in game.legal_moves()

    def test_suicide_with_capture_is_legal(self):
        """A move that would be suicide but captures opponent stones is legal."""
        game = NexusGame(size=3)
        # Black can play at (0,0) capturing the white stone at (0,1)
        # After capture, Black at (0,0) has liberties
        #   0 1 2
        # 0 . O X
        # 1 X X .
        # 2 . . .
        game.set_position(
            [
                [EMPTY, WHITE, BLACK],
                [BLACK, BLACK, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # Black at (0,0) captures White at (0,1)
        # After capture: Black at (0,0) has liberty at (0,1)
        assert (0, 0) in game.legal_moves()
        game.apply_move(0, 0)
        assert game.board[0][0] == BLACK
        assert game.board[0][1] == EMPTY  # White was captured

    def test_snapback_like_capture(self):
        """A move can capture even if it appears to be self-capture initially."""
        game = NexusGame(size=5)
        # Complex position where Black plays into apparent suicide but captures first
        #   0 1 2 3 4
        # 0 . X O . .
        # 1 X O . O .
        # 2 . X O . .
        # 3 . . . . .
        # 4 . . . . .
        game.set_position(
            [
                [EMPTY, BLACK, WHITE, EMPTY, EMPTY],
                [BLACK, WHITE, EMPTY, WHITE, EMPTY],
                [EMPTY, BLACK, WHITE, EMPTY, EMPTY],
                [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY],
                [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # Black at (1,2) captures White at (1,1)
        # White at (0,2), (1,3), (2,2) remain with liberties
        game.apply_move(1, 2)
        assert game.board[1][1] == EMPTY  # Captured
        assert game.board[1][2] == BLACK


class TestLegalMoves:
    """Tests for the legal_moves method."""

    def test_all_empty_points_legal_initially(self):
        """All empty points should be legal in an empty game."""
        game = NexusGame(size=3)
        legal = game.legal_moves()
        assert len(legal) == 9
        for r in range(3):
            for c in range(3):
                assert (r, c) in legal

    def test_occupied_points_excluded(self):
        """Occupied points should not be in legal moves."""
        game = NexusGame(size=3)
        game.apply_move(1, 1)
        legal = game.legal_moves()
        assert (1, 1) not in legal
        assert len(legal) == 8

    def test_suicide_points_excluded(self):
        """Suicide points should not be in legal moves."""
        game = NexusGame(size=3)
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY],
                [WHITE, EMPTY, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )
        legal = game.legal_moves()
        assert (0, 0) not in legal  # Would be suicide
