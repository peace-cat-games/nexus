#!/usr/bin/env python3
"""
Nexus Bot - A simple engine that plays Nexus games.

This bot:
- Registers/logs in as "nexus-bot"
- Creates seeks for both realtime and correspondence games
- Monitors for games where it's the bot's turn
- Makes moves using a simple heuristic strategy
"""

import sys
import time
import random
import logging
import argparse
from typing import Optional, List, Tuple, Dict, Any

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("nexus-bot")

# Bot configuration
BOT_USERNAME = "nexus-bot"
BOT_EMAIL = "nexus-bot@example.com"
BOT_PASSWORD = "nexusbot123"
DEFAULT_SERVER = "http://localhost:8000"


class NexusBot:
    """A simple Nexus playing bot."""

    def __init__(self, server_url: str = DEFAULT_SERVER):
        self.server_url = server_url.rstrip("/")
        self.token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        """Get request headers with auth token."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get(self, endpoint: str) -> requests.Response:
        """Make a GET request."""
        url = f"{self.server_url}{endpoint}"
        return self.session.get(url, headers=self._headers())

    def _post(self, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        """Make a POST request."""
        url = f"{self.server_url}{endpoint}"
        return self.session.post(url, json=data or {}, headers=self._headers())

    def _delete(self, endpoint: str) -> requests.Response:
        """Make a DELETE request."""
        url = f"{self.server_url}{endpoint}"
        return self.session.delete(url, headers=self._headers())

    def register(self) -> bool:
        """Register the bot account."""
        logger.info(f"Attempting to register as {BOT_USERNAME}...")
        resp = self._post(
            "/api/auth/register",
            {
                "username": BOT_USERNAME,
                "email": BOT_EMAIL,
                "password": BOT_PASSWORD,
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = data["access_token"]
            logger.info("Registration successful!")
            return True
        elif resp.status_code == 400:
            detail = resp.json().get("detail", "")
            if "already registered" in detail.lower():
                logger.info("Account already exists, will try to login.")
                return False
            logger.error(f"Registration failed: {detail}")
            return False
        else:
            logger.error(f"Registration failed: {resp.status_code} - {resp.text}")
            return False

    def login(self) -> bool:
        """Login to the bot account."""
        logger.info(f"Logging in as {BOT_USERNAME}...")
        resp = self._post(
            "/api/auth/login",
            {"username": BOT_USERNAME, "password": BOT_PASSWORD},
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = data["access_token"]
            logger.info("Login successful!")
            return True
        else:
            logger.error(f"Login failed: {resp.status_code} - {resp.text}")
            return False

    def authenticate(self) -> bool:
        """Register or login to authenticate the bot."""
        # Try to register first
        if self.register():
            return True
        # If account exists, login
        return self.login()

    def get_user_info(self) -> bool:
        """Get current user info and store user_id."""
        resp = self._get("/api/auth/me")
        if resp.status_code == 200:
            data = resp.json()
            self.user_id = data["id"]
            logger.info(f"Bot user ID: {self.user_id}")
            return True
        logger.error(f"Failed to get user info: {resp.text}")
        return False

    def get_my_games(self) -> List[Dict]:
        """Get all games the bot is participating in."""
        resp = self._get("/api/me/games")
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"Failed to get games: {resp.text}")
        return []

    def get_game_state(self, game_id: str) -> Optional[Dict]:
        """Get the current state of a game."""
        resp = self._get(f"/api/nexus/games/{game_id}")
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"Failed to get game {game_id}: {resp.text}")
        return None

    def get_available_seeks(self) -> List[Dict]:
        """Get all available seeks from other players."""
        resp = self._get("/api/nexus/seeks")
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"Failed to get seeks: {resp.text}")
        return []

    def accept_seek(self, seek_id: int) -> Optional[Dict]:
        """Accept a seek and start a game."""
        resp = self._post(f"/api/nexus/seeks/{seek_id}/accept")
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"Failed to accept seek {seek_id}: {resp.text}")
        return None

    def create_seek(self, mode: str, board_size: int = 5) -> bool:
        """Create a seek for a new game."""
        resp = self._post(
            "/api/nexus/seeks",
            {"mode": mode, "board_size": board_size, "p1": 2, "p2": 4},
        )
        if resp.status_code == 200:
            logger.info(f"Created {mode} seek (size {board_size})")
            return True
        logger.error(f"Failed to create seek: {resp.text}")
        return False

    def get_my_seek(self) -> Optional[Dict]:
        """Get the bot's current open seek."""
        resp = self._get("/api/nexus/seeks/mine")
        if resp.status_code == 200:
            return resp.json()
        return None

    def get_unblocking_options(self, game_id: str) -> Dict:
        """Get forced unblocking options for a game."""
        resp = self._get(f"/api/nexus/games/{game_id}/unblocking-options")
        if resp.status_code == 200:
            return resp.json()
        return {"needs_unblocking": False, "options": []}

    def check_move(self, game_id: str, row: int, col: int) -> Dict:
        """Check if a move triggers debt resolution."""
        resp = self._post(
            f"/api/nexus/games/{game_id}/check-move", {"row": row, "col": col}
        )
        if resp.status_code == 200:
            return resp.json()
        return {"requires_debt_resolution": False}

    def make_move(
        self,
        game_id: str,
        row: int,
        col: int,
        stones_to_remove: Optional[List[List[int]]] = None,
        unblocking_stones: Optional[List[List[int]]] = None,
    ) -> Optional[Dict]:
        """Make a move in a game."""
        data: Dict[str, Any] = {"row": row, "col": col}
        if stones_to_remove:
            data["stones_to_remove"] = stones_to_remove
        if unblocking_stones:
            data["unblocking_stones"] = unblocking_stones

        resp = self._post(f"/api/nexus/games/{game_id}/move", data)
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"Failed to make move: {resp.text}")
        return None

    # --- Move Selection Strategy ---

    def evaluate_position(
        self, board: List[List[int]], size: int, player_stone: int
    ) -> float:
        """
        Evaluate the board position for a player.
        Higher score = better for player.
        """
        opponent_stone = 3 - player_stone  # 1->2, 2->1
        score = 0.0

        # Get all lines
        lines = self._get_all_lines(size)

        for line in lines:
            player_count = sum(1 for r, c in line if board[r][c] == player_stone)
            opponent_count = sum(1 for r, c in line if board[r][c] == opponent_stone)
            empty_count = sum(1 for r, c in line if board[r][c] == 0)

            # If line is blocked by both players, no value
            if player_count > 0 and opponent_count > 0:
                continue

            # Score based on how close to completion
            if player_count == size:
                score += 1000  # Complete line
            elif player_count == size - 1 and empty_count == 1:
                score += 50  # One away from completing
            elif player_count == size - 2 and empty_count == 2:
                score += 10  # Two away
            elif player_count > 0:
                score += player_count

            # Penalize opponent threats
            if opponent_count == size:
                score -= 1000
            elif opponent_count == size - 1 and empty_count == 1:
                score -= 100  # Must block!
            elif opponent_count == size - 2 and empty_count == 2:
                score -= 20

        # Slight preference for center
        center = size // 2
        for r in range(size):
            for c in range(size):
                if board[r][c] == player_stone:
                    dist = abs(r - center) + abs(c - center)
                    score += (size - dist) * 0.1

        return score

    def _get_all_lines(self, size: int) -> List[List[Tuple[int, int]]]:
        """Get all lines (rows, columns, diagonals)."""
        lines = []
        # Rows
        for r in range(size):
            lines.append([(r, c) for c in range(size)])
        # Columns
        for c in range(size):
            lines.append([(r, c) for r in range(size)])
        # Main diagonal
        lines.append([(i, i) for i in range(size)])
        # Anti-diagonal
        lines.append([(i, size - 1 - i) for i in range(size)])
        return lines

    def find_winning_move(
        self, board: List[List[int]], size: int, legal_moves: List[List[int]], player_stone: int
    ) -> Optional[Tuple[int, int]]:
        """Find a move that completes a line for the player."""
        lines = self._get_all_lines(size)
        for line in lines:
            player_count = sum(1 for r, c in line if board[r][c] == player_stone)
            if player_count == size - 1:
                # Find the empty cell
                for r, c in line:
                    if board[r][c] == 0 and [r, c] in legal_moves:
                        return (r, c)
        return None

    def find_blocking_move(
        self, board: List[List[int]], size: int, legal_moves: List[List[int]], player_stone: int
    ) -> Optional[Tuple[int, int]]:
        """Find a move that blocks opponent from completing a line."""
        opponent_stone = 3 - player_stone
        lines = self._get_all_lines(size)
        for line in lines:
            opponent_count = sum(1 for r, c in line if board[r][c] == opponent_stone)
            if opponent_count == size - 1:
                # Find the empty cell to block
                for r, c in line:
                    if board[r][c] == 0 and [r, c] in legal_moves:
                        return (r, c)
        return None

    def select_move(self, game_state: Dict) -> Tuple[int, int]:
        """
        Select the best move using a simple heuristic strategy.

        Priority:
        1. Win if possible
        2. Block opponent win
        3. Play strategically (maximize position evaluation)
        4. Random legal move
        """
        board = game_state["board"]
        size = game_state["size"]
        legal_moves = game_state["legal_moves"]
        to_move = game_state["to_move"]
        player_stone = 1 if to_move == "BLACK" else 2

        if not legal_moves:
            raise ValueError("No legal moves available")

        # 1. Check for winning move
        winning = self.find_winning_move(board, size, legal_moves, player_stone)
        if winning:
            logger.info(f"Found winning move: {winning}")
            return winning

        # 2. Check for blocking move
        blocking = self.find_blocking_move(board, size, legal_moves, player_stone)
        if blocking:
            logger.info(f"Found blocking move: {blocking}")
            return blocking

        # 3. Evaluate all moves and pick the best
        best_move = None
        best_score = float("-inf")

        for move in legal_moves:
            r, c = move
            # Simulate move
            test_board = [row[:] for row in board]
            test_board[r][c] = player_stone
            score = self.evaluate_position(test_board, size, player_stone)
            if score > best_score:
                best_score = score
                best_move = (r, c)

        if best_move:
            return best_move

        # 4. Fallback to random
        move = random.choice(legal_moves)
        return (move[0], move[1])

    def select_stones_to_remove(
        self, player_stones: List[List[int]], count: int, board: List[List[int]], size: int
    ) -> List[List[int]]:
        """
        Select which stones to remove for debt resolution.
        Try to keep stones that are part of potential winning lines.
        """
        if len(player_stones) <= count:
            return player_stones

        lines = self._get_all_lines(size)
        stone_scores = {}

        for stone in player_stones:
            r, c = stone
            score = 0
            for line in lines:
                if (r, c) in line:
                    # Count how many of our stones are on this line
                    our_count = sum(1 for lr, lc in line if [lr, lc] in player_stones)
                    score += our_count
            stone_scores[tuple(stone)] = score

        # Remove stones with lowest scores (least valuable)
        sorted_stones = sorted(player_stones, key=lambda s: stone_scores[tuple(s)])
        return sorted_stones[:count]

    def play_turn(self, game_id: str) -> bool:
        """
        Play a turn in the specified game.
        Returns True if move was made successfully.
        """
        game_state = self.get_game_state(game_id)
        if not game_state:
            return False

        # Check if game is over
        if game_state["result"] != "ONGOING":
            logger.info(f"Game {game_id} is over: {game_state['result']}")
            return False

        # Check if it's our turn
        to_move = game_state["to_move"]
        is_black = game_state.get("player_black_id") == self.user_id
        is_white = game_state.get("player_white_id") == self.user_id

        our_turn = (to_move == "BLACK" and is_black) or (to_move == "WHITE" and is_white)
        if not our_turn:
            return False

        player_stone = 1 if to_move == "BLACK" else 2
        logger.info(f"Playing as {'BLACK' if is_black else 'WHITE'} in game {game_id[:8]}...")

        # Check for forced unblocking
        unblocking = self.get_unblocking_options(game_id)
        unblocking_stones = None
        if unblocking.get("needs_unblocking"):
            options = unblocking.get("options", [])
            if options:
                # Pick the first option (all are minimal)
                unblocking_stones = options[0]
                logger.info(f"Forced unblocking: removing {unblocking_stones}")
            else:
                logger.warning("Forced unblocking impossible!")
                return False

        # Select move
        try:
            row, col = self.select_move(game_state)
        except ValueError as e:
            logger.error(f"Cannot select move: {e}")
            return False

        logger.info(f"Selected move: ({row}, {col})")

        # Check if debt resolution is needed
        check_result = self.check_move(game_id, row, col)
        stones_to_remove = None
        if check_result.get("requires_debt_resolution"):
            count = check_result["stones_to_remove"]
            player_stones = check_result["player_stones"]
            if check_result.get("would_be_bankrupt"):
                logger.warning("Move would cause bankruptcy, but playing anyway...")
            stones_to_remove = self.select_stones_to_remove(
                player_stones, count, game_state["board"], game_state["size"]
            )
            logger.info(f"Debt resolution: removing {count} stones: {stones_to_remove}")

        # Make the move
        result = self.make_move(game_id, row, col, stones_to_remove, unblocking_stones)
        if result:
            if result.get("success"):
                logger.info(f"Move successful! Game result: {result['game_state']['result']}")
                return True
            else:
                logger.warning(f"Move failed: {result.get('message')}")
        return False

    def run(self, poll_interval: float = 2.0):
        """
        Main bot loop.

        - Accepts any available seeks
        - Creates seeks if none exist
        - Plays moves in active games
        """
        logger.info("Starting Nexus Bot...")

        if not self.authenticate():
            logger.error("Failed to authenticate. Exiting.")
            sys.exit(1)

        if not self.get_user_info():
            logger.error("Failed to get user info. Exiting.")
            sys.exit(1)

        logger.info("Bot is ready! Waiting for games...")

        seek_modes = ["realtime", "correspondence"]
        current_seek_mode = 0

        while True:
            try:
                # Accept any available seeks
                seeks = self.get_available_seeks()
                for seek in seeks:
                    logger.info(
                        f"Accepting seek from {seek['owner_username']} "
                        f"({seek['mode']}, size {seek['board_size']})"
                    )
                    game = self.accept_seek(seek["id"])
                    if game:
                        logger.info(f"Game started: {game['game_id'][:8]}...")

                # Create a seek if we don't have one
                my_seek = self.get_my_seek()
                if not my_seek:
                    mode = seek_modes[current_seek_mode]
                    self.create_seek(mode)
                    current_seek_mode = (current_seek_mode + 1) % len(seek_modes)

                # Play in active games
                games = self.get_my_games()
                for game_info in games:
                    if game_info["result"] == "ongoing":
                        self.play_turn(game_info["id"])

                time.sleep(poll_interval)

            except KeyboardInterrupt:
                logger.info("Bot stopped by user.")
                break
            except Exception as e:
                logger.exception(f"Error in main loop: {e}")
                time.sleep(poll_interval * 2)


def main():
    parser = argparse.ArgumentParser(description="Nexus Bot - A simple Nexus playing engine")
    parser.add_argument(
        "--server",
        "-s",
        default=DEFAULT_SERVER,
        help=f"Server URL (default: {DEFAULT_SERVER})",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=float,
        default=2.0,
        help="Poll interval in seconds (default: 2.0)",
    )
    args = parser.parse_args()

    bot = NexusBot(server_url=args.server)
    bot.run(poll_interval=args.interval)


if __name__ == "__main__":
    main()
