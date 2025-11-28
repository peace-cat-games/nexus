"""
Nexus Game Engine

Nexus is a perfect-information, deterministic, two-player game played on an n×n grid
of intersections, similar to Go. It combines Go-style captures and liberties with
Tic-Tac-Toe-style line completion, an economic "debt" layer where capturing incurs
debt that must be resolved when a line is completed, and bankruptcy rules where
failing to pay debt in stones results in a loss.

Key Rules:
- Stones are placed on intersections (like Go)
- Groups with no liberties are captured; capturing adds debt to the capturing player
- A player wins by completing a full line (row, column, or main diagonal)
- When completing a line, debt is resolved: if debt exceeds opponent's debt,
  stones must be removed to pay; if unable to pay, the player goes bankrupt
- If no legal moves exist, forced unblocking removes opponent stones (adding debt)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Set, Tuple, Optional
from itertools import combinations

from .exceptions import (
    IllegalMoveError,
    GameOverError,
    SuicideError,
    OccupiedPointError,
    ForcedUnblockingImpossibleError,
)


class Player(Enum):
    """Represents the two players in the game."""

    BLACK = 1
    WHITE = 2

    def opponent(self) -> "Player":
        """Return the opponent of this player."""
        return Player.WHITE if self == Player.BLACK else Player.BLACK


class GameResult(Enum):
    """Represents the possible game outcomes."""

    ONGOING = 0
    BLACK_WIN = 1
    WHITE_WIN = 2


# Board cell values
EMPTY = 0
BLACK = 1
WHITE = 2


def player_to_stone(player: Player) -> int:
    """Convert a Player enum to the corresponding stone value."""
    return BLACK if player == Player.BLACK else WHITE


def stone_to_player(stone: int) -> Optional[Player]:
    """Convert a stone value to a Player enum, or None if empty."""
    if stone == BLACK:
        return Player.BLACK
    elif stone == WHITE:
        return Player.WHITE
    return None


@dataclass
class GameState:
    """
    Represents the complete state of a Nexus game.

    Attributes:
        size: The board dimension (n×n board).
        board: 2D list representing the board (0=empty, 1=black, 2=white).
        to_move: The player whose turn it is.
        debt_black: Black's current debt.
        debt_white: White's current debt.
        result: The current game result (ONGOING, BLACK_WIN, or WHITE_WIN).
        p1: Debt per stone captured (default 2).
        p2: Debt per stone removed during forced unblocking (default 4).
    """

    size: int
    board: List[List[int]] = field(default_factory=list)
    to_move: Player = Player.BLACK
    debt_black: int = 0
    debt_white: int = 0
    result: GameResult = GameResult.ONGOING
    p1: int = 2
    p2: int = 4

    def __post_init__(self):
        if not self.board:
            self.board = [[EMPTY for _ in range(self.size)] for _ in range(self.size)]

    def copy(self) -> "GameState":
        """Create a deep copy of this game state."""
        return GameState(
            size=self.size,
            board=[row[:] for row in self.board],
            to_move=self.to_move,
            debt_black=self.debt_black,
            debt_white=self.debt_white,
            result=self.result,
            p1=self.p1,
            p2=self.p2,
        )

    def get_debt(self, player: Player) -> int:
        """Get the current debt for a player."""
        return self.debt_black if player == Player.BLACK else self.debt_white

    def set_debt(self, player: Player, value: int) -> None:
        """Set the debt for a player."""
        if player == Player.BLACK:
            self.debt_black = value
        else:
            self.debt_white = value

    def add_debt(self, player: Player, amount: int) -> None:
        """Add to a player's debt."""
        if player == Player.BLACK:
            self.debt_black += amount
        else:
            self.debt_white += amount


class NexusGame:
    """
    Main game engine for Nexus.

    Provides methods to query legal moves, apply moves, handle captures,
    line completion, debt resolution, and forced unblocking.
    """

    def __init__(self, size: int = 5, p1: int = 1, p2: int = 2):
        """
        Initialize a new Nexus game.

        Args:
            size: Board dimension (default 5 for a 5×5 board).
            p1: Debt per stone captured (default 1).
            p2: Debt per stone removed during forced unblocking (default 2).
        """
        self.state = GameState(size=size, p1=p1, p2=p2)

    @property
    def size(self) -> int:
        return self.state.size

    @property
    def board(self) -> List[List[int]]:
        return self.state.board

    @property
    def to_move(self) -> Player:
        return self.state.to_move

    @property
    def result(self) -> GameResult:
        return self.state.result

    def _neighbors(self, r: int, c: int) -> List[Tuple[int, int]]:
        """Return the 4-connected neighbors of a point."""
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                neighbors.append((nr, nc))
        return neighbors

    def _find_group(self, r: int, c: int) -> Set[Tuple[int, int]]:
        """
        Find all stones in the same group as the stone at (r, c).

        A group is a maximal connected set (4-connected) of stones of the same color.

        Args:
            r: Row of the starting stone.
            c: Column of the starting stone.

        Returns:
            Set of (row, col) tuples for all stones in the group.
            Returns empty set if the point is empty.
        """
        stone = self.board[r][c]
        if stone == EMPTY:
            return set()

        group = set()
        stack = [(r, c)]
        while stack:
            pr, pc = stack.pop()
            if (pr, pc) in group:
                continue
            if self.board[pr][pc] != stone:
                continue
            group.add((pr, pc))
            for nr, nc in self._neighbors(pr, pc):
                if (nr, nc) not in group and self.board[nr][nc] == stone:
                    stack.append((nr, nc))
        return group

    def _group_liberties(self, group: Set[Tuple[int, int]]) -> Set[Tuple[int, int]]:
        """
        Find all liberties of a group.

        A liberty is an empty point adjacent (4-connected) to any stone in the group.

        Args:
            group: Set of (row, col) tuples representing the group.

        Returns:
            Set of (row, col) tuples representing the group's liberties.
        """
        liberties = set()
        for r, c in group:
            for nr, nc in self._neighbors(r, c):
                if self.board[nr][nc] == EMPTY:
                    liberties.add((nr, nc))
        return liberties

    def _capture_groups_if_needed(
        self, player: Player, placed_at: Tuple[int, int]
    ) -> int:
        """
        Capture any opponent groups with no liberties adjacent to the placed stone.

        Args:
            player: The player who placed the stone.
            placed_at: The (row, col) where the stone was placed.

        Returns:
            The number of opponent stones captured.
        """
        opponent_stone = player_to_stone(player.opponent())
        captured_count = 0
        captured_groups = []

        r, c = placed_at
        for nr, nc in self._neighbors(r, c):
            if self.board[nr][nc] == opponent_stone:
                group = self._find_group(nr, nc)
                liberties = self._group_liberties(group)
                if len(liberties) == 0:
                    captured_groups.append(group)

        # Remove captured stones
        for group in captured_groups:
            for gr, gc in group:
                if self.board[gr][gc] == opponent_stone:
                    self.board[gr][gc] = EMPTY
                    captured_count += 1

        return captured_count

    def _is_suicide(self, r: int, c: int, player: Player) -> bool:
        """
        Check if placing a stone at (r, c) would be suicide.

        A move is suicide if the placed stone's group would have no liberties
        AND the move does not capture any opponent stones.

        This method should be called with the stone already tentatively placed.

        Args:
            r: Row of the placed stone.
            c: Column of the placed stone.
            player: The player making the move.

        Returns:
            True if the move would be suicide.
        """
        group = self._find_group(r, c)
        liberties = self._group_liberties(group)
        return len(liberties) == 0

    def _would_capture(self, r: int, c: int, player: Player) -> bool:
        """
        Check if placing a stone at (r, c) would capture any opponent stones.

        This method should be called BEFORE placing the stone.

        Args:
            r: Row to place the stone.
            c: Column to place the stone.
            player: The player making the move.

        Returns:
            True if the move would capture at least one opponent stone.
        """
        # Temporarily place the stone
        original = self.board[r][c]
        self.board[r][c] = player_to_stone(player)

        opponent_stone = player_to_stone(player.opponent())
        would_capture = False

        for nr, nc in self._neighbors(r, c):
            if self.board[nr][nc] == opponent_stone:
                group = self._find_group(nr, nc)
                liberties = self._group_liberties(group)
                if len(liberties) == 0:
                    would_capture = True
                    break

        # Restore
        self.board[r][c] = original
        return would_capture

    def _is_legal_move(self, r: int, c: int, player: Optional[Player] = None) -> bool:
        """
        Check if a move at (r, c) is legal for the given player.

        A move is legal if:
        1. The point is empty.
        2. The move is not suicide (unless it captures opponent stones).

        Args:
            r: Row to place the stone.
            c: Column to place the stone.
            player: The player making the move (defaults to current player).

        Returns:
            True if the move is legal.
        """
        if player is None:
            player = self.state.to_move

        # Must be empty
        if self.board[r][c] != EMPTY:
            return False

        # Check if would capture
        would_capture = self._would_capture(r, c, player)

        # Temporarily place to check suicide
        self.board[r][c] = player_to_stone(player)
        is_suicide = self._is_suicide(r, c, player)
        self.board[r][c] = EMPTY

        # Suicide is only allowed if it captures
        if is_suicide and not would_capture:
            return False

        return True

    def legal_moves(self) -> List[Tuple[int, int]]:
        """
        Return all legal moves for the current player.

        Uses Go legality rules only (ignores Completion and Rule 6).

        Returns:
            List of (row, col) tuples representing legal moves.
        """
        moves = []
        for r in range(self.size):
            for c in range(self.size):
                if self._is_legal_move(r, c):
                    moves.append((r, c))
        return moves

    def _get_all_lines(self) -> List[List[Tuple[int, int]]]:
        """
        Get all lines that can be completed (rows, columns, main diagonals).

        Returns:
            List of lines, where each line is a list of (row, col) tuples.
        """
        lines = []

        # Rows
        for r in range(self.size):
            lines.append([(r, c) for c in range(self.size)])

        # Columns
        for c in range(self.size):
            lines.append([(r, c) for r in range(self.size)])

        # Main diagonal (top-left to bottom-right)
        lines.append([(i, i) for i in range(self.size)])

        # Anti-diagonal (top-right to bottom-left)
        lines.append([(i, self.size - 1 - i) for i in range(self.size)])

        return lines

    def _has_full_line(self, player: Player) -> bool:
        """
        Check if a player has at least one complete line.

        Args:
            player: The player to check.

        Returns:
            True if the player has at least one full line.
        """
        stone = player_to_stone(player)
        for line in self._get_all_lines():
            if all(self.board[r][c] == stone for r, c in line):
                return True
        return False

    def _count_stones(self, player: Player) -> int:
        """Count the number of stones a player has on the board."""
        stone = player_to_stone(player)
        count = 0
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == stone:
                    count += 1
        return count

    def _get_player_stones(self, player: Player) -> List[Tuple[int, int]]:
        """Get all positions of a player's stones."""
        stone = player_to_stone(player)
        positions = []
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == stone:
                    positions.append((r, c))
        return positions

    def _resolve_completion(
        self, player: Player, stones_to_remove: Optional[List[Tuple[int, int]]] = None
    ) -> bool:
        """
        Resolve the completion event for a player.

        Called when a player completes a line. Handles debt resolution,
        stone removal, and determining win/loss.

        Args:
            player: The player who triggered completion.
            stones_to_remove: Optional list of player's stones to remove if net debt > 0.
                            If not provided, stones are removed lexicographically.

        Returns:
            True if the game ended (win or loss), False if it continues.

        Raises:
            IllegalMoveError: If stones_to_remove doesn't match required count.
        """
        debt_p = self.state.get_debt(player)
        debt_q = self.state.get_debt(player.opponent())
        net = debt_p - debt_q

        # Case 1: net <= 0, player wins
        if net <= 0:
            self.state.result = (
                GameResult.BLACK_WIN if player == Player.BLACK else GameResult.WHITE_WIN
            )
            return True

        # Case 2: net > 0, player must remove stones
        k = net
        player_stones = self._get_player_stones(player)

        # Bankruptcy: not enough stones
        if len(player_stones) < k:
            self.state.result = (
                GameResult.WHITE_WIN if player == Player.BLACK else GameResult.BLACK_WIN
            )
            return True

        # Determine which stones to remove
        if stones_to_remove is None:
            # Default: remove lexicographically smallest stones
            player_stones.sort()
            stones_to_remove = player_stones[:k]
        else:
            if len(stones_to_remove) != k:
                raise IllegalMoveError(
                    f"Must remove exactly {k} stones, got {len(stones_to_remove)}"
                )
            # Validate that all stones belong to the player
            stone_value = player_to_stone(player)
            for r, c in stones_to_remove:
                if self.board[r][c] != stone_value:
                    raise IllegalMoveError(
                        f"Stone at ({r}, {c}) does not belong to {player.name}"
                    )

        # Remove the stones
        for r, c in stones_to_remove:
            self.board[r][c] = EMPTY

        # Check if player still has a full line
        if self._has_full_line(player):
            self.state.result = (
                GameResult.BLACK_WIN if player == Player.BLACK else GameResult.WHITE_WIN
            )
            return True

        # Game continues: reset debts, pass turn
        self.state.debt_black = 0
        self.state.debt_white = 0
        self.state.to_move = player.opponent()
        return False

    def apply_move(
        self,
        row: int,
        col: int,
        stones_to_remove: Optional[List[Tuple[int, int]]] = None,
    ) -> None:
        """
        Apply a move for the current player.

        Places a stone, resolves captures, updates debt, and checks for completion.
        Does NOT handle forced unblocking (use make_move for that).

        Args:
            row: Row to place the stone.
            col: Column to place the stone.
            stones_to_remove: If completion triggers and net debt > 0, which stones
                             to remove. If None, removes lexicographically smallest.

        Raises:
            GameOverError: If the game has already ended.
            IllegalMoveError: If the move is not legal.
        """
        if self.state.result != GameResult.ONGOING:
            raise GameOverError("Cannot make a move: game has already ended")

        player = self.state.to_move

        # Validate move
        if not self._is_legal_move(row, col, player):
            if self.board[row][col] != EMPTY:
                raise OccupiedPointError(f"Point ({row}, {col}) is already occupied")
            raise SuicideError(f"Move at ({row}, {col}) would be suicide")

        # Place the stone
        self.board[row][col] = player_to_stone(player)

        # Capture opponent groups
        captured = self._capture_groups_if_needed(player, (row, col))

        # Add debt for captures
        if captured > 0:
            self.state.add_debt(player, captured * self.state.p1)

        # Check for completion
        if self._has_full_line(player):
            game_ended = self._resolve_completion(player, stones_to_remove)
            if game_ended:
                return

        # Pass turn
        self.state.to_move = player.opponent()

    def _find_minimal_unblocking_set(self) -> Optional[List[Tuple[int, int]]]:
        """
        Find the minimal set of opponent stones to remove to create a legal move.

        Searches in order of increasing set size until a valid set is found.
        Within each size, prefers lexicographically smallest sets.

        Returns:
            List of (row, col) tuples to remove, or None if impossible.
        """
        player = self.state.to_move
        opponent_stones = self._get_player_stones(player.opponent())

        if not opponent_stones:
            return None

        # Sort for deterministic lexicographic ordering
        opponent_stones.sort()

        # Try increasing set sizes
        for size in range(1, len(opponent_stones) + 1):
            for subset in combinations(opponent_stones, size):
                # Temporarily remove these stones
                removed_values = []
                for r, c in subset:
                    removed_values.append(self.board[r][c])
                    self.board[r][c] = EMPTY

                # Check if any legal move now exists
                has_legal = len(self.legal_moves()) > 0

                # Restore
                for (r, c), val in zip(subset, removed_values):
                    self.board[r][c] = val

                if has_legal:
                    return list(subset)

        return None

    def make_move(
        self,
        row: int,
        col: int,
        stones_to_remove: Optional[List[Tuple[int, int]]] = None,
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Make a complete turn, handling forced unblocking if necessary.

        This is the main high-level API for making a move. It:
        1. Checks if legal moves exist
        2. If not, performs forced unblocking (Rule 6)
        3. Applies the specified move
        4. Returns any stones removed during forced unblocking

        Args:
            row: Row to place the stone.
            col: Column to place the stone.
            stones_to_remove: For completion debt resolution (see apply_move).

        Returns:
            List of opponent stones removed during forced unblocking, or None
            if no forced unblocking was needed.

        Raises:
            GameOverError: If the game has already ended.
            ForcedUnblockingImpossibleError: If forced unblocking is needed but impossible.
            IllegalMoveError: If the specified move is not legal after unblocking.
        """
        if self.state.result != GameResult.ONGOING:
            raise GameOverError("Cannot make a move: game has already ended")

        player = self.state.to_move
        unblocked_stones = None

        # Check if we need forced unblocking
        legal = self.legal_moves()
        if not legal:
            # Find minimal unblocking set
            unblock_set = self._find_minimal_unblocking_set()
            if unblock_set is None:
                # Cannot unblock: player loses
                self.state.result = (
                    GameResult.WHITE_WIN
                    if player == Player.BLACK
                    else GameResult.BLACK_WIN
                )
                raise ForcedUnblockingImpossibleError(
                    f"{player.name} has no legal moves and cannot unblock"
                )

            # Remove the stones
            for r, c in unblock_set:
                self.board[r][c] = EMPTY

            # Add debt for forced unblocking
            self.state.add_debt(player, len(unblock_set) * self.state.p2)
            unblocked_stones = unblock_set

        # Now apply the move
        self.apply_move(row, col, stones_to_remove)
        return unblocked_stones

    def set_position(
        self,
        board: List[List[int]],
        to_move: Player = Player.BLACK,
        debt_black: int = 0,
        debt_white: int = 0,
    ) -> None:
        """
        Set up a specific board position (for testing).

        Args:
            board: 2D list representing the board state.
            to_move: Player to move next.
            debt_black: Black's debt.
            debt_white: White's debt.
        """
        if len(board) != self.size or any(len(row) != self.size for row in board):
            raise ValueError(f"Board must be {self.size}x{self.size}")

        self.state.board = [row[:] for row in board]
        self.state.to_move = to_move
        self.state.debt_black = debt_black
        self.state.debt_white = debt_white

    def __str__(self) -> str:
        """Return a string representation of the current board state."""
        symbols = {EMPTY: ".", BLACK: "X", WHITE: "O"}
        lines = []
        lines.append(
            f"Nexus {self.size}x{self.size} - {self.state.to_move.name} to move"
        )
        lines.append(
            f"Debt: Black={self.state.debt_black}, White={self.state.debt_white}"
        )
        lines.append(f"Result: {self.state.result.name}")
        lines.append("")

        # Column headers
        lines.append("  " + " ".join(str(c) for c in range(self.size)))
        for r in range(self.size):
            row_str = " ".join(symbols[self.board[r][c]] for c in range(self.size))
            lines.append(f"{r} {row_str}")
        return "\n".join(lines)
