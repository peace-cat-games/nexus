"""
Nexus CLI - Interactive command-line interface for playing Nexus.
"""

import sys
from typing import List, Tuple, Optional

from .game import NexusGame, Player, GameResult, player_to_stone, EMPTY


def print_board(game: NexusGame) -> None:
    """Display the game board with coordinates and game info."""
    symbols = {0: "·", 1: "X", 2: "O"}
    size = game.size

    # Header
    print()
    print(f"  {'─' * (size * 2 + 1)}")
    player_symbol = "X" if game.to_move == Player.BLACK else "O"
    print(f"  {game.to_move.name} ({player_symbol}) to move")
    print(f"  Debt: X={game.state.debt_black}  O={game.state.debt_white}")
    print(f"  {'─' * (size * 2 + 1)}")
    print()

    # Column headers
    col_header = "    " + " ".join(str(c) for c in range(size))
    print(col_header)
    print("    " + "─" * (size * 2 - 1))

    # Board rows
    for r in range(size):
        row_str = " ".join(symbols[game.board[r][c]] for c in range(size))
        print(f" {r} │ {row_str}")

    print()


def print_result(game: NexusGame) -> None:
    """Display the game result."""
    print()
    print("═" * 30)
    if game.result == GameResult.BLACK_WIN:
        print("  GAME OVER: BLACK (X) WINS!")
    elif game.result == GameResult.WHITE_WIN:
        print("  GAME OVER: WHITE (O) WINS!")
    print("═" * 30)
    print()


def print_help() -> None:
    """Display help information."""
    print(
        """
Commands:
  r,c       Place a stone at row r, column c (e.g., "2,3" or "2 3")
  legal     Show all legal moves
  help      Show this help message
  rules     Show game rules summary
  quit      Exit the game

During debt resolution:
  When you complete a line with positive net debt, you must choose
  which of your stones to remove. Enter coordinates separated by
  semicolons (e.g., "0,0;1,1;2,2").

During forced unblocking:
  When you have no legal moves, you must choose which opponent stones
  to remove. Enter the option number (e.g., "1" or "2").
"""
    )


def print_rules() -> None:
    """Display a summary of game rules."""
    print(
        """
Nexus Rules Summary:
────────────────────
• Place stones (X or O) on intersections, like Go
• Capture groups with no liberties (4-connected empty neighbors)
• Capturing adds DEBT to YOU: captured_stones × p1 (default: 2)
• Win by completing a full line (row, column, or diagonal)

Debt Resolution:
• When you complete a line, compute net_debt = your_debt - opponent_debt
• If net_debt ≤ 0: You WIN immediately
• If net_debt > 0: Remove that many of YOUR stones
  - If you can't remove enough: You go BANKRUPT and LOSE
  - If the line is broken: Game continues, debts reset to 0
  - If line remains complete: You WIN

Forced Unblocking:
• If you have no legal moves, you MUST remove opponent stones
• Removes minimum stones needed to create a legal move
• Adds debt: removed_stones × p2 (default: 4)
• If unblocking is impossible: You LOSE

Ko Rule:
• Prevents repeating any previous (board, debt_difference) state
• A move is illegal if it would recreate a past position with the same debt difference
"""
    )


def parse_move(input_str: str) -> Optional[Tuple[int, int]]:
    """Parse a move from user input."""
    input_str = input_str.strip()

    # Try comma-separated
    if "," in input_str:
        parts = input_str.split(",")
    else:
        parts = input_str.split()

    if len(parts) != 2:
        return None

    try:
        row = int(parts[0].strip())
        col = int(parts[1].strip())
        return (row, col)
    except ValueError:
        return None


def parse_stones_to_remove(input_str: str) -> Optional[List[Tuple[int, int]]]:
    """Parse multiple stone coordinates for debt resolution."""
    stones = []
    parts = input_str.strip().split(";")

    for part in parts:
        coord = parse_move(part)
        if coord is None:
            return None
        stones.append(coord)

    return stones


def get_unblocking_choice(
    game: NexusGame, options: List[List[Tuple[int, int]]]
) -> List[Tuple[int, int]]:
    """Prompt user to select which opponent stones to remove for forced unblocking."""
    print(f"\nNo legal moves! You must remove opponent stones to unblock.")
    print(f"This will add {len(options[0]) * game.state.p2} debt.")
    print(f"\nChoose which stones to remove:")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")

    while True:
        try:
            user_input = input("> ").strip()
            if user_input.lower() == "quit":
                sys.exit(0)

            choice = int(user_input)
            if 1 <= choice <= len(options):
                return options[choice - 1]
            print(f"Invalid choice. Enter a number from 1 to {len(options)}.")
        except ValueError:
            print(f"Invalid input. Enter a number from 1 to {len(options)}.")
        except EOFError:
            sys.exit(0)
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)


def get_stones_to_remove(game: NexusGame, required: int) -> List[Tuple[int, int]]:
    """Prompt user to select stones to remove for debt resolution."""
    player = game.to_move
    player_stones = []
    stone_value = player_to_stone(player)

    for r in range(game.size):
        for c in range(game.size):
            if game.board[r][c] == stone_value:
                player_stones.append((r, c))

    print(f"\nYou must remove {required} of your stones to resolve debt.")
    print(f"Your stones: {player_stones}")
    print(f"Enter {required} coordinates separated by semicolons (e.g., '0,0;1,1'):")

    while True:
        try:
            user_input = input("> ").strip()
            if user_input.lower() == "quit":
                sys.exit(0)

            stones = parse_stones_to_remove(user_input)
            if stones is None:
                print("Invalid format. Use 'r,c;r,c;...' format.")
                continue

            if len(stones) != required:
                print(f"Must select exactly {required} stones, got {len(stones)}.")
                continue

            # Validate stones belong to player
            valid = True
            for r, c in stones:
                if r < 0 or r >= game.size or c < 0 or c >= game.size:
                    print(f"Coordinate ({r},{c}) is out of bounds.")
                    valid = False
                    break
                if game.board[r][c] != stone_value:
                    print(f"Coordinate ({r},{c}) is not your stone.")
                    valid = False
                    break

            if valid:
                return stones

        except EOFError:
            sys.exit(0)
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)


def play_game(size: int = 5, p1: int = 2, p2: int = 4) -> None:
    """Main game loop."""
    game = NexusGame(size=size, p1=p1, p2=p2)

    print("\n" + "═" * 40)
    print(f"  NEXUS - {size}x{size} Board")
    print(f"  p1={p1} (debt per capture)")
    print(f"  p2={p2} (debt per forced unblock)")
    print("═" * 40)
    print("\nType 'help' for commands, 'rules' for game rules.\n")

    while game.result == GameResult.ONGOING:
        print_board(game)

        # Check for forced unblocking situation
        legal = game.legal_moves()
        unblocking_choice = None
        if not legal:
            unblock_options = game._find_all_minimal_unblocking_sets()
            if not unblock_options:
                print("No legal moves and no way to unblock - you lose!")
                break
            unblocking_choice = get_unblocking_choice(game, unblock_options)
            print_board(game)

        # Get user input
        try:
            prompt = f"{game.to_move.name}> "
            user_input = input(prompt).strip().lower()
        except EOFError:
            print("\nExiting...")
            break
        except KeyboardInterrupt:
            print("\nExiting...")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input == "quit" or user_input == "q":
            print("Thanks for playing!")
            break
        elif user_input == "help" or user_input == "h":
            print_help()
            continue
        elif user_input == "rules" or user_input == "r":
            print_rules()
            continue
        elif user_input == "legal" or user_input == "l":
            if unblocking_choice:
                # Show what moves will be legal after unblocking
                print(
                    f"After removing {unblocking_choice}, legal moves will be available."
                )
                print("Enter your move to proceed.")
            else:
                legal_now = game.legal_moves()
                if legal_now:
                    print(f"Legal moves ({len(legal_now)}): {legal_now}")
                else:
                    print("No legal moves!")
            continue

        # Parse as move
        move = parse_move(user_input)
        if move is None:
            print("Invalid input. Enter 'row,col' or type 'help'.")
            continue

        row, col = move

        # Validate bounds
        if row < 0 or row >= size or col < 0 or col >= size:
            print(f"Coordinates out of bounds. Valid range: 0-{size-1}")
            continue

        # Try to make the move
        try:
            # Check if this move will trigger completion with positive net debt
            stones_to_remove = None
            required = game.check_completion_debt_resolution(row, col)

            if required is not None and required > 0:
                # Count player's stones to check for bankruptcy
                # Add 1 because the move will place another stone
                player_stone_count = game._count_stones(game.to_move) + 1
                if player_stone_count < required:
                    # Player doesn't have enough stones - bankruptcy, loses immediately
                    print(
                        f"\nThis move completes a line but you have net debt of {required}."
                    )
                    print(
                        f"You only have {player_stone_count} stones - BANKRUPTCY! You lose."
                    )
                else:
                    # Player must manually select stones to remove
                    print(
                        f"\nThis move completes a line but you have net debt of {required}."
                    )
                    stones_to_remove = get_stones_to_remove(game, required)

            unblocked = game.make_move(row, col, stones_to_remove, unblocking_choice)

            if unblocked:
                print(f"Removed opponent stones: {unblocked}")

            if game.result != GameResult.ONGOING:
                print_board(game)
                print_result(game)
                break

        except Exception as e:
            print(f"Error: {e}")
            continue

    print("Game ended.")


def main() -> None:
    """Entry point for the CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Nexus - A strategic board game combining Go and Tic-Tac-Toe"
    )
    parser.add_argument(
        "-s", "--size", type=int, default=5, help="Board size (default: 5)"
    )
    parser.add_argument(
        "--p1", type=int, default=2, help="Debt per captured stone (default: 2)"
    )
    parser.add_argument(
        "--p2",
        type=int,
        default=4,
        help="Debt per stone removed in forced unblocking (default: 4)",
    )

    args = parser.parse_args()

    if args.size < 3:
        print("Error: Board size must be at least 3")
        sys.exit(1)

    play_game(size=args.size, p1=args.p1, p2=args.p2)


if __name__ == "__main__":
    main()
