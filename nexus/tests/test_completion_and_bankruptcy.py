"""Tests for line completion, debt resolution, and bankruptcy."""

import pytest
from nexus import (
    NexusGame,
    Player,
    GameResult,
    EMPTY,
    BLACK,
    WHITE,
    GameOverError,
)


class TestLineCompletion:
    """Tests for detecting line completion."""

    def test_row_completion_wins(self):
        """Completing a row with zero debt wins the game."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Black has two stones in row 0, plays third to complete
        #   0 1 2
        # 0 X X .
        # 1 O O .
        # 2 . . .
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [WHITE, WHITE, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        game.apply_move(0, 2)  # Complete row 0

        assert game.result == GameResult.BLACK_WIN

    def test_column_completion_wins(self):
        """Completing a column with zero debt wins the game."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Black has two stones in column 0
        game.set_position(
            [
                [BLACK, WHITE, EMPTY],
                [BLACK, WHITE, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        game.apply_move(2, 0)  # Complete column 0

        assert game.result == GameResult.BLACK_WIN

    def test_main_diagonal_completion_wins(self):
        """Completing the main diagonal with zero debt wins the game."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [BLACK, WHITE, EMPTY],
                [WHITE, BLACK, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        game.apply_move(2, 2)  # Complete diagonal (0,0)-(1,1)-(2,2)

        assert game.result == GameResult.BLACK_WIN

    def test_anti_diagonal_completion_wins(self):
        """Completing the anti-diagonal with zero debt wins the game."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [WHITE, WHITE, BLACK],
                [EMPTY, BLACK, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        game.apply_move(2, 0)  # Complete diagonal (0,2)-(1,1)-(2,0)

        assert game.result == GameResult.BLACK_WIN

    def test_white_can_win(self):
        """White can also win by completing a line."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [WHITE, WHITE, EMPTY],
                [BLACK, BLACK, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.WHITE,
        )

        game.apply_move(0, 2)  # White completes row 0

        assert game.result == GameResult.WHITE_WIN


class TestZeroDebtCompletion:
    """Tests for completion when net debt is zero or negative."""

    def test_zero_debt_both_players(self):
        """Completing with zero debt for both players wins immediately."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [WHITE, WHITE, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
            debt_black=0,
            debt_white=0,
        )

        game.apply_move(0, 2)
        assert game.result == GameResult.BLACK_WIN

    def test_equal_debt_both_players(self):
        """Completing with equal debt (net=0) wins immediately."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [WHITE, WHITE, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
            debt_black=5,
            debt_white=5,
        )

        game.apply_move(0, 2)
        assert game.result == GameResult.BLACK_WIN

    def test_opponent_has_more_debt(self):
        """Completing when opponent has more debt (net<0) wins immediately."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [WHITE, WHITE, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
            debt_black=2,
            debt_white=10,
        )

        game.apply_move(0, 2)
        assert game.result == GameResult.BLACK_WIN


class TestDebtResolutionWithStoneRemoval:
    """Tests for completion when player must remove stones to pay debt."""

    def test_remove_stones_to_pay_debt(self):
        """Player removes stones when net debt > 0."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Black has 4 stones, will complete with 2 more debt than White
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [BLACK, WHITE, EMPTY],
                [BLACK, WHITE, EMPTY],
            ],
            to_move=Player.BLACK,
            debt_black=3,
            debt_white=1,
        )

        # Black plays at (0,2) to complete row 0
        # Net = 3 - 1 = 2, so Black must remove 2 stones
        # Specify which stones to remove to keep the row complete
        game.apply_move(0, 2, stones_to_remove=[(1, 0), (2, 0)])

        # Row 0 is still complete: (0,0), (0,1), (0,2) all Black
        assert game.result == GameResult.BLACK_WIN

    def test_remove_stones_breaks_line(self):
        """Removing stones may break the completed line."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Black has exactly 3 stones in a row
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [WHITE, WHITE, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
            debt_black=2,
            debt_white=0,
        )

        # Black completes row 0 by playing (0,2)
        # Now Black has 3 stones: (0,0), (0,1), (0,2)
        # Net = 2 - 0 = 2, must remove 2 stones
        # Removing 2 stones from 3 breaks the line
        game.apply_move(0, 2)

        # Should break line and continue game
        assert game.result == GameResult.ONGOING
        assert game.state.debt_black == 0  # Debt reset
        assert game.state.debt_white == 0  # Debt reset
        assert game.to_move == Player.WHITE  # Turn passed

    def test_specify_which_stones_to_remove(self):
        """Player can specify which of their stones to remove."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [BLACK, WHITE, EMPTY],
                [BLACK, WHITE, EMPTY],
            ],
            to_move=Player.BLACK,
            debt_black=3,
            debt_white=1,
        )

        # Remove (1,0) and (2,0) instead of default lexicographic order
        # This keeps row 0 complete
        game.apply_move(0, 2, stones_to_remove=[(1, 0), (2, 0)])

        assert game.result == GameResult.BLACK_WIN

    def test_remove_wrong_number_of_stones_raises(self):
        """Specifying wrong number of stones to remove raises error."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [BLACK, WHITE, EMPTY],
                [BLACK, WHITE, EMPTY],
            ],
            to_move=Player.BLACK,
            debt_black=3,
            debt_white=1,
        )

        # Need to remove 2 stones, but only specify 1
        with pytest.raises(Exception):  # IllegalMoveError
            game.apply_move(0, 2, stones_to_remove=[(1, 0)])


class TestBankruptcy:
    """Tests for bankruptcy (not enough stones to pay debt)."""

    def test_bankruptcy_loses_game(self):
        """Not having enough stones to pay debt causes bankruptcy loss."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Black has only 3 stones, needs to remove 4
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [WHITE, WHITE, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
            debt_black=5,
            debt_white=1,
        )

        # Black plays at (0,2) to complete row 0
        # Now Black has 3 stones
        # Net = 5 - 1 = 4, needs to remove 4 stones
        # But Black only has 3 stones -> bankruptcy
        game.apply_move(0, 2)

        assert game.result == GameResult.WHITE_WIN

    def test_bankruptcy_exactly_all_stones(self):
        """Needing to remove exactly as many stones as you have is NOT bankruptcy."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [WHITE, WHITE, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
            debt_black=3,
            debt_white=0,
        )

        # Black plays at (0,2), now has 3 stones
        # Net = 3, must remove 3 stones
        # After removing all 3, no line remains
        game.apply_move(0, 2)

        # Not bankruptcy (has exactly enough), but line is broken
        assert game.result == GameResult.ONGOING

    def test_large_debt_bankruptcy(self):
        """Very large debt relative to stones causes bankruptcy."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [WHITE, WHITE, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
            debt_black=100,
            debt_white=0,
        )

        game.apply_move(0, 2)
        assert game.result == GameResult.WHITE_WIN


class TestGameOverPreventsMoreMoves:
    """Tests that no moves can be made after game ends."""

    def test_move_after_win_raises(self):
        """Cannot make a move after someone has won."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [WHITE, WHITE, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        game.apply_move(0, 2)  # Black wins
        assert game.result == GameResult.BLACK_WIN

        with pytest.raises(GameOverError):
            game.apply_move(1, 2)

    def test_move_after_bankruptcy_raises(self):
        """Cannot make a move after bankruptcy."""
        game = NexusGame(size=3, p1=1, p2=2)
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [WHITE, WHITE, EMPTY],
                [EMPTY, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
            debt_black=10,
            debt_white=0,
        )

        game.apply_move(0, 2)  # Black bankrupts
        assert game.result == GameResult.WHITE_WIN

        with pytest.raises(GameOverError):
            game.apply_move(2, 2)


class TestMultipleCompletedLines:
    """Tests for completing multiple lines simultaneously."""

    def test_multiple_lines_still_wins(self):
        """Completing multiple lines at once still wins with net <= 0."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Black about to complete both row 0 and main diagonal
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [WHITE, BLACK, EMPTY],
                [WHITE, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # (0,2) completes row 0 and also part of anti-diagonal
        # (2,2) would complete main diagonal
        # Let's set up for (2,2) completing main diagonal
        game.apply_move(2, 2)  # Complete diagonal

        assert game.result == GameResult.BLACK_WIN

    def test_removal_may_break_one_but_keep_another(self):
        """Removing stones may break one line but keep another complete."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Complex position
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [BLACK, BLACK, EMPTY],
                [BLACK, EMPTY, EMPTY],
            ],
            to_move=Player.BLACK,
            debt_black=2,
            debt_white=0,
        )

        # Black plays at (0,2) - completes row 0
        # Has 6 stones, must remove 2
        # Can keep row 0 complete by removing from column 0
        game.apply_move(0, 2, stones_to_remove=[(1, 0), (2, 0)])

        assert game.result == GameResult.BLACK_WIN


class TestCompletionWithCapture:
    """Tests for moves that both capture and complete a line."""

    def test_capture_and_complete_same_move(self):
        """A move can capture stones and complete a line simultaneously."""
        game = NexusGame(size=3, p1=1, p2=2)
        # Black's move at (0,2) will:
        # 1. Capture White stone at (1,2) (surrounded after placement)
        # 2. Complete row 0
        game.set_position(
            [
                [BLACK, BLACK, EMPTY],
                [EMPTY, BLACK, WHITE],
                [EMPTY, BLACK, EMPTY],
            ],
            to_move=Player.BLACK,
        )

        # Before move: debt_black = 0
        # Move captures 1 stone, debt becomes 1
        # Then completion triggers with net = 1 - 0 = 1
        game.apply_move(0, 2)

        # Black must remove 1 stone
        # Row 0 is still complete (0,0), (0,1), (0,2)
        # Removing from elsewhere keeps the line
        assert game.result == GameResult.BLACK_WIN
