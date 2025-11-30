## 1. High-level spec for playnexus.com

### Core features

1. **Accounts**

   * Register (username, email, password)
   * Login / logout
   * “My games” list
   * Optional: simple profile (joined date, rating placeholder, etc.)

2. **PvP Nexus Games**

   * **Real-time mode**

     * Live lobby of players “seeking game”
     * Create “Real-time 5×5” or “Real-time 7×7” challenge
     * Matchmaking: random opponent or direct challenge
     * Moves via WebSocket (ideal) or short-polling
     * Move clocks (e.g. 10+5 or just a “soft” inactivity timeout)
   * **Correspondence mode**

     * Games stored in DB with last-move timestamp
     * No tight clock; maybe “X days per move”
     * Email / notification hook later
     * Turn-based UI: you open an ongoing game, see the board, make a move, it’s saved

3. **Rules / Learn Nexus**

   * `/rules` page with:

     * Overview
     * Board / groups / liberties
     * Debt (p₁=2, p₂=4)
     * Completion & audit examples
     * Bankruptcy
     * Forced unblocking
   * `/puzzles` page (optional at first) with a small set of diagrams (“Is this capture safe?”, “What happens if White completes this line?”)

### Pages / routes

* `/` – landing page

  * “Play Nexus now”
  * “Learn the rules”
  * “Play as guest” (optional)
* `/register`
* `/login`
* `/logout`
* `/play` – main lobby:

  * Tabs: `Real-time` / `Correspondence`
  * Show:

    * “Create game” buttons
    * “Join random game”
    * List of open challenges
    * List of your active games
* `/game/:id`

  * Board UI
  * Move list (simple)
  * Debts display: “Black debt: 6, White debt: 2”
  * Status: “Black to move”, “White wins by bankruptcy”, etc.
* `/rules`
* `/about` (optional)

### Integration with your Nexus engine

Assume your engine provides something like this (you can adjust in the Claude prompt):

* `POST /api/games` → create new game (size, mode, players)
* `GET /api/games/:id` → return full game state
* `POST /api/games/:id/move` → apply a move for current player

  * Request: `{ row, col }` (and maybe forced-unblock flag if you want)
  * Response: updated state, including:

    * board
    * whose turn
    * debts
    * captures made
    * whether Completion happened
    * whether someone won (and how)

Real-time:

* WebSocket channel like `/ws/game/:id` that:

  * pushes opponent moves
  * pushes game end events
  * (fallback: poll `/api/games/:id` every 2–3 seconds for now)

Correspondence:

* No WS needed; just load state on page load and after you play.

### Basic data model (server-side DB)

* `users`

  * id
  * username
  * email
  * password_hash
  * created_at

* `games`

  * id
  * player_black_id
  * player_white_id
  * mode (`realtime` / `correspondence`)
  * board_size
  * state_blob (JSON from your engine)
  * result (`ongoing` / `black_win` / `white_win`)
  * created_at
  * updated_at

* `seeks` (for lobby)

  * id
  * owner_user_id
  * mode
  * board_size
  * created_at

That’s enough for a **minimal** Lichess-like site.