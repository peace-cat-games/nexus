**PROMPT TO CLAUDE:**

You are an expert full-stack engineer and product designer.

I already have a working **Nexus game engine / API** that can:

* Create a Nexus game with a given board size
* Return current game state
* Apply a move and return the new state

Now I want you to design and code the **public-facing website** `playnexus.com` where people can:

1. Register and log in
2. Play **PvP Nexus** games:

   * Real-time (live)
   * Correspondence (turn-based)
3. Read the **Nexus rules** on a static page

Think “very minimal Lichess or Arimaa-like site, but for Nexus.”

### 1. Assume the engine API

Assume the backend already has these endpoints (or create stubs for them):

* `POST /api/nexus/games`

  * Body: `{ boardSize: number, mode: "realtime" | "correspondence" }`
  * Creates a new game with current user as one player.
* `GET /api/nexus/games/:id`

  * Returns:

    * `board`: 2D array
    * `toMove`: `"BLACK" | "WHITE"`
    * `debtBlack`, `debtWhite`
    * `result`: `"ongoing" | "black_win" | "white_win"`
    * `lastMove`
    * `availableMoves` (optional)
* `POST /api/nexus/games/:id/move`

  * Body: `{ row: number, col: number }`
  * Applies a move according to Nexus rules (captures, debt, completion, bankruptcy, forced unblocking handled engine-side)
  * Returns updated state as above.

If you need more fields, define them and assume the engine will be updated later.

### 2. Stack

Choose a simple stack like:

* Backend: Node + Express **or** Python + FastAPI/Flask
* Frontend: React + fetch/axios
* DB: SQLite or Postgres

You may assume a monorepo structure.

### 3. User system

Implement:

* `POST /auth/register`
* `POST /auth/login`
* `POST /auth/logout`
* Middleware for checking authenticated user
* User model:

  * id
  * username
  * email
  * password_hash
  * created_at

Use secure password hashing.

### 4. Game & lobby

Implement:

* `GET /api/me/games` – list of games involving current user
* `POST /api/nexus/seek` – create a game seek (mode, board size)
* `GET /api/nexus/seeks` – list open seeks
* `POST /api/nexus/seeks/:id/accept` – join someone’s seek → game created

Two modes:

* **Real-time**

  * Use WebSockets at `/ws/game/:id` to:

    * Broadcast moves to both players
    * Broadcast game end
  * Or implement simple polling (every 2s) if you prefer to avoid websockets but keep code structured for future WS upgrade.

* **Correspondence**

  * No need for WS; just load state when the page opens and after each move.
  * Store `lastMoveAt` in the DB for each game.

### 5. Pages / UI

Implement a simple React SPA or MPA with pages:

* `/` (Home)

  * “Play Nexus” button
  * “Learn Nexus” button
  * Quick explanation + link to `/rules`

* `/login` and `/register`

* `/play`

  * Show:

    * “Create Real-time Game” buttons (board size options: 3, 5, 7)
    * “Create Correspondence Game” buttons
    * List of open seeks (join buttons)
    * List of “Your games” (ongoing + finished)

* `/game/:id`

  * Show:

    * Board as clickable grid
    * Current player to move
    * Debts: `Black debt: X`, `White debt: Y`
    * Game result if finished (“White wins by bankruptcy”, etc.)
    * Move history (simple list: `B D4`, `W C3`, …)
  * On click:

    * POST to `/api/nexus/games/:id/move`
    * Show errors for illegal moves
    * Update board with new state
  * If using websockets, subscribe to `/ws/game/:id` and update when opponent moves.

* `/rules`

  * Render a **human-friendly version** of Nexus rules:

    * Overview
    * Board and groups
    * Captures and p₁=2 debt
    * Completion and the audit
    * Bankruptcy
    * Forced unblocking and p₂=4
  * Use headings, bullet points, and diagrams (ASCII or simple SVG).

Keep styling minimal but not ugly:
centered layout, simple navbar with links: Home / Play / Rules / Login / Register / Profile.

### 6. Code organization

Provide:

* Backend

  * `server.js` (or `main.py`)
  * `routes/auth.js`, `routes/games.js`, `routes/nexus.js`
  * `models/User`, `models/Game`, `models/Seek`
  * `services/nexusEngineClient.js` – wraps calls to the existing Nexus engine

* Frontend

  * React app with pages:

    * `HomePage`
    * `LoginPage`
    * `RegisterPage`
    * `PlayPage`
    * `GamePage`
    * `RulesPage`
  * Components:

    * `Board` (renders Nexus board)
    * `GameInfoPanel`
    * `GameList`
    * `SeekList`
    * `NavBar`

### 7. Tests

Write at least backend tests for:

* Authentication flow (register/login protections)
* Game creation
* Move application via `/api/nexus/games/:id/move` (mock the Nexus engine responses if needed)
* Real-time / correspondence distinction at the DB level

You do **not** need to re-test the Nexus rules engine itself; assume that’s already covered by its own tests.

### 8. Deliverable

* Provide all code in a structured way (file tree with code fences).

* At the end, include a short **“How to run locally”**:

  * `npm install` / `pip install`
  * `npm run dev` / gunicorn command, etc.
  * How to initialize DB

* Also describe:

  * How the lobby flow works
  * How real-time updates work (WS or polling)
  * How the game page talks to the existing Nexus engine.

---

Please now generate the complete codebase skeleton + representative implementations (not just pseudocode), and the instructions to run `playnexus.com` locally.
