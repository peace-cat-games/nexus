"""Turn enumeration for n×n Nexus (n = 3, 4, 5) built only on the reference engine nexus/game.py.

A *turn* is (S, m, R): S = opponent stones removed by forced unblocking (or None),
m = the placed point, R = own stones removed in a completion audit (or None).
Cells are encoded i = n*row + col (set_size(n) selects n; default 3).  Everything that decides legality or outcome
is computed by game.py itself (legal_moves, _find_all_minimal_unblocking_sets,
make_move, _resolve_completion); this module only enumerates the choices that
game.py leaves to the mover (which minimal unblocking set, which placement,
which stones to remove) and applies each one through game.py.
"""

import os
import sys
from itertools import combinations

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from nexus.game import NexusGame, Player, GameResult, BLACK, WHITE, EMPTY  # noqa: E402
from nexus.exceptions import ForcedUnblockingImpossibleError  # noqa: E402

N = 3


def set_size(n):
    """Select the board size used by every function in this module."""
    global N
    N = n


NOMOVE = "NOMOVE"
ILLDEF = "ILLDEF"


_MEMO_ON = False


def enable_unblocking_memo():
    """Memoize game.py's _find_all_minimal_unblocking_sets on the complete
    game state (board, side to move, both debts, p1, p2, superko history).

    The method is a pure function of that state, so this changes speed only,
    not results.  make_move recomputes the sets for every turn it validates,
    which makes enumerating all turns of a 5x5 unblocking position very slow.
    """
    global _MEMO_ON
    if _MEMO_ON:
        return
    _MEMO_ON = True
    orig = NexusGame._find_all_minimal_unblocking_sets
    cache = {}

    def memo(self):
        st = self.state
        key = (tuple(tuple(r) for r in self.board), st.to_move, st.debt_black, st.debt_white, st.p1, st.p2,
               frozenset(st.position_history))
        if key not in cache:
            if len(cache) > 200000:
                cache.clear()
            cache[key] = [list(s) for s in orig(self)]
        return [list(s) for s in cache[key]]

    NexusGame._find_all_minimal_unblocking_sets = memo


def rc(i):
    return divmod(i, N)


def clone(game):
    g = NexusGame(size=game.size, p1=game.state.p1, p2=game.state.p2)
    g.state = game.state.copy()
    return g


def _remove_and_charge(game, S):
    """Mirror of make_move's unblocking step (stone removal + p2 debt)."""
    for r, c in S:
        game.board[r][c] = EMPTY
    game.state.add_debt(game.state.to_move, len(S) * game.state.p2)


def enumerate_turns(game):
    """All turns available to the side to move, as game.py defines them.

    Returns NOMOVE (mover cannot place and cannot unblock: mover loses),
    ILLDEF (minimal unblocking sets exist but no placement is legal after the
    p2 debt is added; game.py has no defined continuation), or a list of
    (S, m, R) tuples of cell-index tuples / None.
    """
    player = game.state.to_move
    legal = game.legal_moves()
    base = []
    if legal:
        base = [(None, m) for m in legal]
    else:
        sets = game._find_all_minimal_unblocking_sets()
        if not sets:
            return NOMOVE
        for S in sets:
            g = clone(game)
            _remove_and_charge(g, S)
            for m in g.legal_moves():
                base.append((tuple(sorted(S)), m))
        if not base:
            return ILLDEF
    turns = []
    stone = BLACK if player == Player.BLACK else WHITE
    for S, m in base:
        g = clone(game)
        if S:
            _remove_and_charge(g, S)
        r, c = m
        g.board[r][c] = stone
        cap = g._capture_groups_if_needed(player, m)
        if cap:
            g.state.add_debt(player, cap * g.state.p1)
        R_options = [None]
        if g._has_full_line(player):
            net = g.state.get_debt(player) - g.state.get_debt(player.opponent())
            own = sorted(g._get_player_stones(player))
            if 0 < net <= len(own):
                R_options = list(combinations(own, net))
        enc_S = None if S is None else tuple(r_ * N + c_ for r_, c_ in S)
        for R in R_options:
            enc_R = None if R is None else tuple(sorted(r_ * N + c_ for r_, c_ in R))
            turns.append((enc_S, r * N + c, enc_R))
    return turns


def apply_turn(game, turn):
    """Apply a turn through game.py's public make_move (which validates it)."""
    S, m, R = turn
    r, c = rc(m)
    game.make_move(
        r,
        c,
        stones_to_remove=None if R is None else [rc(i) for i in R],
        unblocking_stones=None if S is None else [rc(i) for i in S],
    )


def turn_str(turn):
    """Cells as digits for n = 3 (the 3x3 tree format), comma-separated otherwise."""
    S, m, R = turn
    sep = "" if N <= 3 else ","
    f = lambda x: "-" if not x else sep.join(str(i) for i in sorted(x))
    return f"{f(S)}/{m}/{f(R)}"


def parse_turn(s):
    a, m, b = s.split("/")
    if N <= 3:
        g = lambda x: None if x == "-" else tuple(int(ch) for ch in x)
    else:
        g = lambda x: None if x == "-" else tuple(int(t) for t in x.split(","))
    return (g(a), int(m), g(b))


def board_str(game):
    sym = {EMPTY: ".", BLACK: "X", WHITE: "O"}
    return "".join(sym[game.board[r][c]] for r in range(N) for c in range(N))


def outcome_str(game_after, mover):
    res = game_after.result
    if res == GameResult.ONGOING:
        assert game_after.state.to_move == mover.opponent()
        return f"C:{board_str(game_after)}:{game_after.state.debt_black}:{game_after.state.debt_white}"
    win = GameResult.BLACK_WIN if mover == Player.BLACK else GameResult.WHITE_WIN
    return "MW" if res == win else "ML"


def canonical(game):
    """Canonical string of all turns and their outcomes (comparable with the Rust movegen)."""
    turns = enumerate_turns(game)
    if turns in (NOMOVE, ILLDEF):
        return turns
    mover = game.state.to_move
    items = []
    for t in turns:
        g = clone(game)
        apply_turn(g, t)
        items.append(f"{turn_str(t)}={outcome_str(g, mover)}")
    return " ".join(sorted(items))


def position_line(game):
    """Input line for `nexus-solver movegen`."""
    st = game.state
    hist = " ".join(
        "".join({EMPTY: ".", BLACK: "X", WHITE: "O"}[v] for row in b for v in row) + f":{d}"
        for (b, d) in st.position_history
    )
    stm = 0 if st.to_move == Player.BLACK else 1
    return f"{st.p1} {st.p2} {stm} {board_str(game)} {st.debt_black} {st.debt_white} {hist}".rstrip()
