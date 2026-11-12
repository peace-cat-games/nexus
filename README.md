# Nexus

A strategic board game combining Go-style captures with Tic-Tac-Toe line completion and debt economics.

## Overview

Nexus is a perfect-information, deterministic, two-player game played on an n×n grid of intersections. It uniquely combines:

- **Go-style mechanics**: Stones are placed on intersections, groups share liberties, and surrounded groups are captured
- **Tic-Tac-Toe objectives**: Win by completing a full line (row, column, or main diagonal)
- **Debt economics**: Capturing opponent stones incurs debt that must be settled when completing a line
- **Bankruptcy rules**: Failing to pay debt in stones results in a loss

## Installation

```bash
# Clone the repository
git clone https://github.com/peace-cat-games/nexus.git
cd nexus

# Install in development mode
pip install -e ".[dev]"
```

## Quick Start

### Command-Line Interface

Play Nexus interactively in your terminal:

```bash
# Start a game with default settings (5x5 board)
nexus
# Or run as a Python module
python -m nexus

# Custom board size
nexus --size 7

# Custom debt parameters
nexus --size 5 --p1 3 --p2 5
```

In-game commands:
- `r,c` or `r c` - Place a stone at row r, column c (e.g., `2,3`)
- `legal` - Show all legal moves
- `rules` - Show game rules
- `help` - Show help
- `quit` - Exit the game

### Python API

```python
from nexus import NexusGame, Player

# Create a new 5x5 game
game = NexusGame(size=5)

# Make moves (row, col)
game.make_move(0, 0)  # Black plays
game.make_move(1, 1)  # White plays
game.make_move(0, 1)  # Black plays
# ...

# Check game state
print(game)
print(f"Current player: {game.to_move}")
print(f"Legal moves: {game.legal_moves()}")
```

## Rules Summary

### Basic Play
1. Black plays first, then players alternate
2. Stones are placed on empty intersections
3. Suicide moves (placing a stone that would have no liberties without capturing) are illegal

### Captures and Debt
- When a group loses all liberties, it is captured and removed
- Capturing stones adds debt to the capturing player: `captured_count × p1` (default p1=2)

### Winning Conditions
- Complete a full line (all n stones in a row, column, or main diagonal)
- When completing a line, debt is resolved:
  - If your debt ≤ opponent's debt: **You win**
  - If your debt > opponent's debt: Remove `(your_debt - opponent_debt)` of your own stones
    - If you can't afford it: **Bankruptcy - you lose**
    - If line remains complete after removal: **You win**
    - Otherwise: Game continues, debts reset to 0

### Forced Unblocking (Rule 6)
If a player has no legal moves:
1. Remove the minimum number of opponent stones to create a legal move
2. Add `removed_count × p2` debt (default p2=4)
3. Then make a normal move

## API Reference

### NexusGame

```python
# Initialize
game = NexusGame(size=5, p1=2, p2=4)

# Properties
game.size        # Board dimension
game.board       # 2D list (0=empty, 1=black, 2=white)
game.to_move     # Current player (Player.BLACK or Player.WHITE)
game.result      # GameResult.ONGOING, BLACK_WIN, or WHITE_WIN

# Methods
game.legal_moves()                    # List of legal (row, col) tuples
game.make_move(row, col)              # Make a move (handles forced unblocking)
game.apply_move(row, col)             # Apply move without forced unblocking
game.set_position(board, to_move, debt_black, debt_white)  # Set up position
```

### Exceptions

- `IllegalMoveError`: Move violates game rules
- `SuicideError`: Move would be suicide
- `OccupiedPointError`: Point is already occupied
- `GameOverError`: Game has already ended
- `ForcedUnblockingImpossibleError`: Cannot unblock and player loses

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest nexus/tests/test_basic_rules.py
```

### Code Formatting

```bash
# Check formatting
black --check .

# Apply formatting
black .
```

## Project Structure

```
nexus/
├── nexus/
│   ├── __init__.py       # Package exports
│   ├── __main__.py       # Module entry point
│   ├── cli.py            # Command-line interface
│   ├── game.py           # Core game engine
│   ├── exceptions.py     # Custom exceptions
│   └── tests/            # Unit tests
├── prompts/
│   └── nexus.txt         # Game specification
├── pyproject.toml        # Project configuration
└── README.md
```

## Research

3×3 Nexus with the default parameters (p1 = 2, p2 = 4) is a first-player win. The solver and the independent checker that prove it are at [haapavesi-institute/nexus-solver](https://github.com/haapavesi-institute/nexus-solver).

## License

Copyright 2025–2026 Ian Joiner. Licensed under the Apache License, Version 2.0 (see [LICENSE](LICENSE)).
