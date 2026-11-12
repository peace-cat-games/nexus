# 3×3 Nexus solver

Weak solution of 3×3 Nexus under the standard settings (p1 = 2 debt per
captured stone, p2 = 4 debt per stone removed in forced unblocking).

## Result

**Black, moving first, wins.** Every one of the 9 opening moves wins.

| Black's first move (cell) | forced win by turn (exact search) | verified tree: turns / leaves / max game length |
|---|---|---|
| (0,0) corner, cell 0 — **main strategy** | 9 | 198 / 79 / 9 |
| (0,1) edge, cell 1 | 9 | 202 / 76 / 9 |
| (0,2) corner, cell 2 | 9 | 206 / 82 / 9 |
| (1,0) edge, cell 3 | 9 | 196 / 74 / 9 |
| (1,1) centre, cell 4 | 18 | 2743 / 1139 / 18 |
| (1,2) edge, cell 5 | 9 | 229 / 85 / 9 |
| (2,0) corner, cell 6 | 9 | 240 / 94 / 9 |
| (2,1) edge, cell 7 | 9 | 247 / 82 / 9 |
| (2,2) corner, cell 8 | 9 | 240 / 95 / 9 |

* A "turn" is one complete action by the player to move: an optional forced
  unblocking, then a placement, then an optional audit removal. "Win by turn 9"
  means the game ends at or before the 9th turn of the game, counting both
  players (Black's 5th placement).
* **Main strategy** (`results/strategy_p1-2_p2-4.txt`): Black opens in the
  corner (0,0). The tree has 198 turns: 99 Black decision nodes, 21 White
  decision nodes and 79 terminal leaves. Every game played with it ends with a
  Black win by turn 9. White's longest resistance is (1,1), (1,2) or (2,1)
  (survives 8 turns). Every other White second move loses within 6 turns.
* **Minimality.** Exact search (no transposition table, full superko history)
  shows that Black can force a win within 9 turns but not within 8. Every
  corner and edge opening forces a win within 9 turns. The centre opening
  forces a win within 18 turns but not within 17. These lower bounds come from
  the solver's exact search only; the independent checker verifies the upper
  bounds, i.e. the trees.
* The ill-defined unblocking case (rule 6 below) never occurs, either in the
  trees or anywhere in the search: its counter is 0 at every iteration of
  every run in `results/solve.log`.

Principal variation of the main strategy, with White's longest resistance
(`results/pv_main.txt`; coordinates are (row, col)):

```
1. B (0,0)   2. W (1,1)   3. B (0,1)   4. W (0,2)   5. B (1,0)   6. W (2,1)
7. B (1,2)  captures W(0,2), Black debt 2
8. W (2,0)  (W cannot block at (0,2): that point is suicide for White)
9. B (0,2)  completes row 0; audit net = 2 - 0 = 2; Black removes (1,0),(1,2),
            which lie outside the row; the row survives -> BLACK WINS
```

The centre opening's principal variation (`results/pv_center_opening.txt`)
runs for 18 turns. It includes a White forced unblocking (turn 8), a Black
audit in which Black has to break its own line and the debts reset (turn 9),
and a final White bankruptcy.

## Rules as implemented (interpretation)

Sources: `RULES.md`, the original spec `prompts/nexus.txt`, and the reference
engine `nexus/game.py`. Where the documents are silent or disagree, the solver
follows `game.py`. Notes in *italics* mark the points that needed an
interpretation.

1. **Board and start.** 3×3 points, cell index `3*row + col`. The game starts
   on an empty board, Black to move, with both debts 0.
2. **Placement (Go rules).** The mover places on an empty point. After the
   stone is placed, every adjacent opponent group with no liberties is
   captured; all such groups are found first and then removed together. A
   placement that leaves its own group without liberties is illegal unless it
   captures. Capturing k stones adds k·p1 to the mover's debt.
3. **Positional superko, exactly as `game.py` implements it.** A history set
   holds keys `(board, debt_black − debt_white)`; side to move is not part of
   the key.
   * A key is recorded at the end of every completed turn that does not end the
     game. The recorded key is the final position of the turn: after captures
     and, if an audit took place, after the audit's stone removal and debt
     reset (key diff 0).
   * The initial empty position is not recorded. The intermediate position
     after a forced unblocking is not recorded either.
   * A placement is illegal if the position right after the placement and its
     captures, before any audit, is already in the history. That position's
     diff includes the new capture debt and any unblocking debt paid this
     turn. Audit removals are never ko-tested.
   * Superko counts as part of legality everywhere, so a player whose only
     Go-legal placements are superko-forbidden has "no legal placement" and
     must unblock.
   * *The spec (`prompts/nexus.txt`) says not to implement superko, while
     `RULES.md` and `game.py` do implement it. We follow `RULES.md`/`game.py`.*
4. **Completion audit.** After the placement and its captures, only the
   mover's lines are checked: 3 rows, 3 columns and 2 diagonals. If the mover
   owns a full line, net = D_mover − D_opponent.
   * net ≤ 0: the mover wins.
   * net > number of the mover's stones: the mover loses by bankruptcy.
   * Otherwise the mover removes exactly `net` stones of their own, chosen
     freely (`game.py` accepts `stones_to_remove`; its lexicographic default
     applies only when no choice is passed). If a full line survives, the
     mover wins. Hence the mover wins exactly when net ≤ stones − 3. Otherwise
     both debts reset to 0 and the turn passes.
5. **Forced unblocking.** It applies only when the mover has no legal
   placement under rule 2 plus superko. The mover removes a minimum-size set
   of opponent stones after which a legal placement exists, pays k·p2 debt,
   and then places as normal (rules 2–4). The mover loses if the opponent has
   no stones or if no set works.
   * *Which minimum set: the mover chooses.* RULES.md is silent and the spec
     suggests a lexicographic choice. `game.py` (`make_move`) requires the
     mover to pass one of the sets from `_find_all_minimal_unblocking_sets`,
     so the solver branches over all minimum sets.
   * *Exact `game.py` semantics.* Minimality is judged with the debts before
     the p2 charge, as `_find_all_minimal_unblocking_sets` does. The placement
     that follows is then judged with the debt after the charge, as
     `apply_move` does. The mover chooses the placement too.
6. **Ill-defined corner case.** Minimum sets can exist while no placement is
   legal once the p2 debt is added; this can only happen through superko,
   because the charge changes the diff. In that case `game.py` would raise in
   the middle of a turn. *The solver scores this as a loss for the mover and
   counts every occurrence.* The count is 0 in every search and tree reported
   here, and in all 58,856 differential-test positions. The checker would
   reject any such node, so the result does not depend on this choice.
7. **No passing.** `game.py` has no pass move: every turn ends with a
   placement.
8. **Infinite play.** The documents do not define a result for a game that
   never ends. Debts can grow without bound, so superko on (board, debt
   difference) does not by itself bound game length. *The convention would be
   that unending play is a draw, but it never matters here.* The winning
   strategy is a finite tree, so every game consistent with it terminates
   (within 9 turns for the main strategy).
9. **Turn branching.** A turn is the triple (unblocking set, placement, audit
   removal set). Each distinct triple available to the opponent is a separate
   branch that the strategy must answer.

Spec/engine discrepancies noticed along the way (none affect the result):
* The spec's example uses p1 = 1; we use the RULES.md defaults p1 = 2, p2 = 4.
* `game.py`'s `check_completion_debt_resolution` calls a method that does not
  exist, `_find_minimal_unblocking_set`. Neither the solver nor the checker
  uses it.

## Method

### Engine (`src/game.rs`)
Each colour is a 9-bit mask. Groups and liberties are computed with shift
masks. `gen()` returns every turn of the side to move together with its
outcome: mover wins, mover loses, or the next position plus the superko key to
record. The cases are the same as in rules 2–6. It also returns `NoMove`
(mover loses) and `IllDefined` (rule 6).

### Differential testing (`tools/difftest.py`)
For each test position, `game.py` and the Rust generator each list every turn
together with its outcome: a win, a loss, or the resulting board plus both
debts. The two lists must be identical. The `game.py` list is built only from
`legal_moves`, `_find_all_minimal_unblocking_sets` and `make_move`
(`tools/pyref.py`).

Test positions come from two sources:
* random playouts from the empty board, which give realistic superko
  histories;
* random boards with random debts and side to move. Their histories are seeded
  with keys that a single placement, or a single placement after one removal,
  would recreate. This is ko bait that also exercises unblocking.

Debt rates are mostly p1 = 2, p2 = 4, plus random pairs (p1, p2) ∈ [0,6]².

Result: **58,856 positions, 0 mismatches**. The positions included 2,183
no-move losses, 10,694 positions where unblocking was required, 5,444 audits
with a removal choice, and 15,499 positions where superko removed at least one
otherwise legal placement. Reproduce with
`python3 tools/difftest.py --games 3000 --random 30000 --seed 2`, which takes
about 2 minutes.

### Search (`src/main.rs`) and why it is sound
* **Superko and history.** The value of a position depends on the history set,
  which is the graph-history-interaction problem. Every ko test in the solver
  uses the **exact history of the actual path from the empty board**.
* **TT mode (default).** This is iterative-deepening negamax with three
  values (win / loss / unknown-within-depth). The transposition table is
  keyed on (board, debt_black, debt_white, side to move) **without** the
  history. That is not sound under superko, so this mode is treated purely as
  a heuristic for move ordering and as a guess at the value.
* **Exact mode (`--no-tt`).** This is the same search with no transposition
  table: plain depth-limited minimax over exact histories. It is sound. Every
  node is a real game prefix and the depth limit only produces "unknown",
  never a false win or loss. This mode gives the minimality statements above:
  `depth 8: Unk`, `depth 9: Win(9)` from the root, and `Loss(17)` after the
  centre opening, i.e. a Black win by turn 18 and not by turn 17.
* **Strategy extraction.** Extraction replays the game exactly, with full
  history and no table cut-offs. At each Black node it keeps one Black turn,
  and at each White node it keeps every White turn. A Black turn is accepted
  only if its subtree extracts successfully, and in exact mode only if exact
  search proves it. Black's candidates are ordered by the table or by exact
  search. Whatever the table contains, the extracted object is a finite tree
  in which each node's history is the exact history of its line.
* **Termination.** The tree is finite (depth ≤ 9 for the main strategy), so
  every game consistent with it ends. The open question about infinite play
  therefore never arises.

### Independent verification (`tools/check_strategy.py`)
The checker uses no solver code; legality and outcomes come from
`nexus/game.py`. It starts a fresh `NexusGame` and replays every turn through
`make_move`, so the superko history is the one `game.py` itself builds along
each line. At each node it checks the following.
* **Black to move:** exactly one child, and that turn is in `game.py`'s list
  of allowed turns. `make_move` also validates the unblocking set and the
  removal count and ownership.
* **White to move:** the children are exactly all turns `game.py` allows, with
  nothing missing, nothing extra and no duplicates. A node with zero children
  is accepted only if `game.py` raises `ForcedUnblockingImpossibleError` with
  a Black win.
* **Leaves and internal nodes:** every leaf is a finished game won by Black,
  and no internal node is a finished game.

All 11 tree files in `results/` pass (`results/verify.log`; the main tree
takes 0.07 s, the centre tree 0.9 s).

## Numbers

Hardware: Intel i7-12700H laptop CPU, single thread; the machine has 15 GB RAM.

| run | nodes searched | wall time | peak RSS |
|---|---|---|---|
| root, exact mode, iterative deepening to depth 9 | 224,253 | 0.02 s | 1.8 MB |
| root, TT mode | 36,001 (5,171 TT entries) | 0.01 s | — |
| centre opening, exact mode, iterative deepening to depth 17 | 35,293,441 | 2.1 s | — |
| other 7 openings, exact mode | 18,667 – 66,554 each | < 0.01 s | — |
| differential test (Python + Rust) | 58,856 positions | 2 min | — |

## Files

* `results/strategy_p1-2_p2-4.txt`: the main strategy tree (corner opening),
  in the format described below.
* `results/strategy_p1-2_p2-4.json`: the same tree as nested JSON. Each node
  has `turn`, `board` (9 characters, `X` = Black, `O` = White, `.` = empty,
  row-major), both debts, `to_move`, `result` and `height`. Intended for
  figures.
* `results/opening_<cell>.txt`: a verified depth-minimal strategy for each
  forced Black first move (cell = 3·row + col).
* `results/strategy_tt_p1-2_p2-4.txt`: the tree extracted in TT mode, which is
  identical to the main tree.
* `results/pv_main.txt`, `results/pv_center_opening.txt`: principal
  variations with boards.
* `results/solve.log`, `results/verify.log`: solver and checker output.

**Tree format.** Nodes are listed in preorder, one line per node:
`<turn> <number of children>`. The first line is `root 1`. A turn is written
`S/m/R`:
* `S` is the list of opponent stones removed by unblocking (`-` = none);
* `m` is the placed cell;
* `R` is the list of own stones removed in the audit (`-` = none).

Cells are digits 0–8. For example, `-/2/35` means "place at cell 2, then
remove own stones 3 and 5 in the audit".

## Reproduce

```
cd nexus/solver && ./run_all.sh     # build, difftest, solve, check (~3 min)
```

# Larger boards (4×4, 5×5) and complexity measurements

* `src/game.rs` now handles any n ≤ 5 (n²-bit masks, 128-bit superko keys);
  the 3×3 trees above regenerate byte for byte. `tools/` take the size
  (`difftest.py --n N`; the checker reads `n=` from the tree header).
* `nexus-solver prove --n N --side black|white` (`src/prove.rs`) decides
  "X forces a win within d turns" by iterative deepening: an AND/OR search
  over exact histories, with
  - a **sound, history-aware transposition table**: a stored result carries
    θ = fewest stones on any board whose superko key its search looked up,
    plus a 128-bit hash of the history keys with ≥ θ stones; it is reused only
    when the current history hashes the same above θ (proof in
    `prove.rs` and the paper's larger-boards section). `--no-tt-values`
    turns reuse off (ordering only = pure exact search);
  - two history-free horizon cut-offs (X needs a line it lacks ≤ 1 stone of to
    win on its last turn);
  - exact strategy extraction as before, for `check_strategy.py`.
* `tools/crosscheck_tt.py` compares reuse vs pure exact search per depth from
  random capture-rich start lines (`results/larger/crosscheck_tt_*.log`).
* `run_larger.sh` reruns the differential tests, cross-checks and the four
  45-minute searches; logs are in `results/larger/`.
* `complexity/` and `src/bin/complexity.rs`: board counts (exact for n ≤ 4,
  Monte Carlo for n = 5), Go reachability, the Nexus debt-pumping cycle
  (`verify_cycle.py` replays it through game.py), random playouts for Go,
  Enhanced Go and Nexus (`run_playouts.sh`), and the cross-check of the Rust
  Enhanced Go rules against the Peace Cat Games TypeScript engine
  (`ego_ts_count.mjs`, run with `node --experimental-strip-types`).
