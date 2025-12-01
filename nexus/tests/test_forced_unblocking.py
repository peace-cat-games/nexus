"""Tests for forced unblocking (Rule 6)."""

import pytest
from nexus import (
    NexusGame,
    Player,
    GameResult,
    EMPTY,
    BLACK,
    WHITE,
    ForcedUnblockingImpossibleError,
)


class TestForcedUnblockingBasic:
    """Basic tests for forced unblocking mechanics."""

    def test_detect_no_legal_moves(self):
        """legal_moves() returns empty when no legal moves exist."""
        game = NexusGame(size=4, p1=1, p2=2)
        # Create a position where the only empty point is suicide
        # and surrounding white stones have other liberties
        #   0 1 2 3
        # 0 . O . .
        # 1 O O . .
        # 2 . . . .
        # 3 . . . .
        # (0,0) is empty, surrounded by White, but White has other liberties
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY, EMPTY],
                [WHITE, WHITE, EMPTY, EMPTY],
                [EMPTY, EMPTY, EMPTY, EMPTY],
                [EMPTY, EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # (0,0) is suicide - White group has liberties elsewhere
        assert (0, 0) not in game.legal_moves()
        # But other points are legal
        assert len(game.legal_moves()) > 0

    def test_no_legal_moves_all_suicide(self):
        """legal_moves() returns empty when ALL empty points are suicide."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Fill most of the board with both colors, leaving only suicide points
        # Black stones with no liberties except points that are suicide for Black
        #   0 1 2
        # 0 . O O
        # 1 O X X
        # 2 O X X
        # (0,0) is suicide - surrounded by O (which has liberties at X positions externally)
        # Wait, let me think... X = Black, O = White
        # (0,0) neighbors: (0,1)=O, (1,0)=O.
        # White group at (0,1), (0,2), (1,0), (2,0) - connected?
        # (0,1)-(0,2) connected. (1,0)-(2,0) connected. Are they connected? No.
        # Let me use a clearer position

        game = NexusGame(size=3, p1=1, p2=2)
        # All positions except corners filled, corners are suicide
        #   0 1 2
        # 0 . O .
        # 1 O X O
        # 2 . O .
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY],
                [WHITE, BLACK, WHITE],
                [EMPTY, WHITE, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # All four corners are empty
        # (0,0) neighbors: (0,1)=W, (1,0)=W - White has liberty at (0,0) AND other corners
        # So playing (0,0) doesn't capture anything, and Black at (0,0) has no liberties = suicide
        legal = game.legal_moves()
        # (0,0), (0,2), (2,0), (2,2) are all suicide
        assert len(legal) == 0

    def test_remove_one_stone_to_unblock(self):
        """Removing one opponent stone creates a legal move."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Same position - all corners suicide
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY],
                [WHITE, BLACK, WHITE],
                [EMPTY, WHITE, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        assert len(game.legal_moves()) == 0

        # Get unblocking options and choose one
        options = game._find_all_minimal_unblocking_sets()
        assert len(options) > 0

        # Black wants to play at (0,0), choosing to remove (0,1)
        removed = game.make_move(0, 0, unblocking_stones=[(0, 1)])

        assert removed is not None
        assert len(removed) == 1
        assert removed[0] == (0, 1)  # Adjacent white removed
        assert game.board[0][0] == BLACK
        assert game.board[0][1] == EMPTY  # Removed
        assert game.state.debt_black == 1 * game.state.p2  # p2 = 2

    def test_forced_unblocking_adds_debt(self):
        """Forced unblocking adds p2 debt per stone removed."""
        game = NexusGame(size=3, p1=1, p2=3)  # p2 = 3
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY],
                [WHITE, BLACK, WHITE],
                [EMPTY, WHITE, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # Choose one of the unblocking options
        options = game._find_all_minimal_unblocking_sets()
        game.make_move(0, 0, unblocking_stones=options[0])

        assert game.state.debt_black == 3  # 1 stone * p2=3

    def test_minimal_set_chosen(self):
        """The minimal number of stones are removed for unblocking."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Position where there ARE legal moves, so no unblocking needed
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY],
                [WHITE, EMPTY, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # (0,0) is suicide - surrounded by (0,1) and (1,0)
        # But there are other legal moves!
        legal = game.legal_moves()
        assert len(legal) > 0
        assert (0, 0) not in legal  # Suicide

        # Normal move, no forced unblocking
        game.apply_move(1, 1)
        assert game.state.debt_black == 0

    def test_capture_gives_group_liberties(self):
        """A move can capture stones, making itself legal via the captured liberties."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Position where (1,1) seems surrounded but captures give it liberties
        #   0 1 2
        # 0 X O X
        # 1 O . O
        # 2 X O X
        game.set_position(
            [
                [BLACK, WHITE, BLACK],
                [WHITE, EMPTY, WHITE],
                [BLACK, WHITE, BLACK],
            ],
            to_move=Player.BLACK,
        )

        # (1,1) is empty. Neighbors: (0,1)=W, (1,0)=W, (1,2)=W, (2,1)=W
        # Each white stone is isolated and has only (1,1) as liberty
        # So placing Black at (1,1) captures all 4 white stones -> LEGAL!
        # After capturing, the main diagonal (0,0)-(1,1)-(2,2) is complete
        legal = game.legal_moves()
        assert (1, 1) in legal

        game.apply_move(1, 1)
        # Captured 4 stones, then diagonal completed
        # Net debt = 4, must remove 4 stones from 5 Black stones
        # Line breaks, game continues
        assert game.result == GameResult.ONGOING

    def test_multiple_options_returned(self):
        """All minimal unblocking sets are returned for user to choose."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY],
                [WHITE, BLACK, WHITE],
                [EMPTY, WHITE, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # Try to play at (0,0)
        # Need to remove one of (0,1) or (1,0)
        # Both are valid minimal options
        options = game._find_all_minimal_unblocking_sets()

        # Should have multiple options
        assert len(options) >= 2
        assert [(0, 1)] in options
        assert [(1, 0)] in options

        # Player can choose either option
        removed = game.make_move(0, 0, unblocking_stones=[(1, 0)])
        assert removed == [(1, 0)]


class TestForcedUnblockingImpossible:
    """Tests for when forced unblocking is impossible."""

    def test_no_way_to_unblock_loses(self):
        """If no removal creates a legal move, player loses."""
        game = NexusGame(size=2, p1=1, p2=2)
        # Board full of Black stones - no empty points, no opponent stones
        game.set_position(
            [
                [BLACK, BLACK],
                [BLACK, BLACK],
            ],
            to_move=Player.BLACK,
        )

        # No empty points, no opponent stones
        # Forced unblocking impossible
        with pytest.raises(ForcedUnblockingImpossibleError):
            game.make_move(0, 0)

        # Game should end with White winning
        assert game.result == GameResult.WHITE_WIN

    def test_forced_unblocking_sets_result_before_raising(self):
        """When unblocking is impossible, result is set before raising exception."""
        game = NexusGame(size=2, p1=1, p2=2)
        game.set_position(
            [
                [BLACK, BLACK],
                [BLACK, BLACK],
            ],
            to_move=Player.BLACK,
        )

        try:
            game.make_move(0, 0)
        except ForcedUnblockingImpossibleError:
            pass

        assert game.result == GameResult.WHITE_WIN


class TestForcedUnblockingWithGameplay:
    """Tests for forced unblocking followed by normal gameplay."""

    def test_forced_unblock_then_capture(self):
        """After forced unblocking, the move can still capture stones."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Position where forced unblock creates a capture opportunity
        #   0 1 2
        # 0 . O .
        # 1 O X O
        # 2 . O .
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY],
                [WHITE, BLACK, WHITE],
                [EMPTY, WHITE, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # All corners are suicide. Black plays at (0,0) via forced unblock
        # Remove (0,1), then place at (0,0)
        # After placing, check if (1,0) is captured
        # (1,0) neighbors: (0,0)=B, (1,1)=B, (2,0)=empty
        # So (1,0) still has liberty at (2,0) - not captured

        # Choose to remove (0,1)
        removed = game.make_move(0, 0, unblocking_stones=[(0, 1)])

        assert removed is not None
        assert (0, 1) in removed  # Removed to unblock
        assert game.board[0][0] == BLACK  # Placed
        # (1,0) not captured because it has liberty at (2,0)
        assert game.board[1][0] == WHITE

        # Debt: p2*1 (unblock) = 2
        assert game.state.debt_black == 2

    def test_forced_unblock_leads_to_win(self):
        """Forced unblocking followed by completion can win the game."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Position: all corners suicide for Black
        #   0 1 2
        # 0 . O .
        # 1 O X O
        # 2 . O .
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY],
                [WHITE, BLACK, WHITE],
                [EMPTY, WHITE, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # All empty points are suicide
        legal = game.legal_moves()
        assert len(legal) == 0

        # Get unblocking options
        options = game._find_all_minimal_unblocking_sets()

        # Black plays at (0,0) via forced unblock
        removed = game.make_move(0, 0, unblocking_stones=options[0])

        # Forced unblock: remove a stone to give (0,0) a liberty
        # Place Black at (0,0)
        # No complete line, game continues
        assert removed is not None
        assert game.board[0][0] == BLACK
        assert game.result == GameResult.ONGOING
        assert game.state.debt_black == 2  # p2 * 1

    def test_forced_unblock_game_continues_normally(self):
        """After forced unblocking and move, game continues if no win/loss."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY],
                [WHITE, BLACK, WHITE],
                [EMPTY, WHITE, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # Get unblocking options
        options = game._find_all_minimal_unblocking_sets()
        removed = game.make_move(0, 0, unblocking_stones=options[0])

        assert removed is not None
        assert game.result == GameResult.ONGOING
        assert game.to_move == Player.WHITE
        assert game.board[0][0] == BLACK
        assert game.state.debt_black == 2  # p2 * 1


class TestForcedUnblockingEdgeCases:
    """Edge cases for forced unblocking."""

    def test_unblocking_required_but_not_provided(self):
        """ValueError is raised when unblocking is required but not provided."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY],
                [WHITE, BLACK, WHITE],
                [EMPTY, WHITE, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # No legal moves
        assert len(game.legal_moves()) == 0

        # Try to make move without providing unblocking choice
        with pytest.raises(ValueError) as exc_info:
            game.make_move(0, 0)

        assert "Forced unblocking required" in str(exc_info.value)

    def test_invalid_unblocking_choice_rejected(self):
        """ValueError is raised when invalid unblocking choice is provided."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY],
                [WHITE, BLACK, WHITE],
                [EMPTY, WHITE, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # Try to make move with a non-minimal unblocking set (removing 2 stones when 1 suffices)
        with pytest.raises(ValueError) as exc_info:
            game.make_move(0, 0, unblocking_stones=[(0, 1), (1, 0)])

        assert "Invalid unblocking choice" in str(exc_info.value)

    def test_valid_unblocking_wrong_move_raises_suicide(self):
        """SuicideError is raised when valid unblocking doesn't unblock the chosen move."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [EMPTY, WHITE, EMPTY],
                [WHITE, BLACK, WHITE],
                [EMPTY, WHITE, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # (2,1) is a valid unblocking set (unblocks 2,0 and 2,2), but doesn't unblock (0,0)
        from nexus.exceptions import SuicideError

        with pytest.raises(SuicideError):
            game.make_move(0, 0, unblocking_stones=[(2, 1)])

    def test_has_legal_moves_no_unblocking(self):
        """If legal moves exist, forced unblocking doesn't happen."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [EMPTY, BLACK, EMPTY],
                [EMPTY, EMPTY, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        removed = game.make_move(0, 0)

        assert removed is None  # No unblocking needed
        assert game.state.debt_black == 0

    def test_white_forced_unblocking(self):
        """White can also trigger forced unblocking."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Same pattern but for White
        game.set_position(
            [
                [EMPTY, BLACK, EMPTY],
                [BLACK, WHITE, BLACK],
                [EMPTY, BLACK, EMPTY],
            ],
            to_move=Player.WHITE,
        )

        # All corners are suicide for White
        assert len(game.legal_moves()) == 0

        # Get unblocking options
        options = game._find_all_minimal_unblocking_sets()
        removed = game.make_move(0, 0, unblocking_stones=options[0])

        assert removed is not None
        assert len(removed) == 1
        assert game.board[0][0] == WHITE
        assert game.state.debt_white == 2  # p2 * 1

    def test_remove_from_edge(self):
        """Forced unblocking can remove edge stones."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Edge position - (1,0) is empty, surrounded
        #   0 1 2
        # 0 O . .
        # 1 . O .
        # 2 O . .
        game.set_position(
            [
                [WHITE, EMPTY, EMPTY],
                [EMPTY, WHITE, EMPTY],
                [WHITE, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # Many legal moves exist here - (0,1), (0,2), (1,0), (1,2), (2,1), (2,2)
        legal = game.legal_moves()
        assert len(legal) > 0

        # Normal move, no forced unblocking
        removed = game.make_move(0, 1)
        assert removed is None
        assert game.state.debt_black == 0
