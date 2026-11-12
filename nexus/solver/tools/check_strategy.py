"""Independent checker for a Nexus strategy tree, using only nexus/game.py.

The tree file (written by `nexus-solver solve`) lists nodes in preorder, one per
line: `<turn> <number of children>`; the first node is `root`.  A turn is
`S/m/R` (unblocking set / placed cell / audit-removal set, cells r*n+c; n from the header, default 3, '-' =
none).  The checker replays every turn through game.py's make_move, starting
from a fresh NexusGame (so the superko history is exactly the one game.py
builds along that line of play), and verifies:

  * at every node where the claimed winner is to move: exactly one child, and
    that turn is among the turns game.py allows (enumerated from game.py's
    legal_moves / _find_all_minimal_unblocking_sets / audit removal choices);
  * at every node where the loser is to move: the children are exactly ALL the
    turns game.py allows (no missing, no extra, no duplicates), or, with zero
    children, that game.py declares the loser unable to move
    (ForcedUnblockingImpossibleError, result = winner);
  * every leaf reached by a turn is a finished game won by the claimed winner,
    and no internal node is a finished game.

Because the tree is finite, this proves the claimed winner wins from the
initial position against every opponent strategy, and that every such game
ends within the tree's depth.

usage: python3 check_strategy.py STRATEGY_FILE
"""

import sys
import pyref
from pyref import (
    NexusGame, Player, GameResult, NOMOVE, ILLDEF, ForcedUnblockingImpossibleError,
    enumerate_turns, apply_turn, clone, turn_str, parse_turn, board_str,
)


class CheckError(Exception):
    pass


def main(path):
    header = {}
    nodes = []
    with open(path) as f:
        for line in f:
            if line.startswith("#"):
                for tok in line[1:].split():
                    if "=" in tok:
                        k, v = tok.split("=", 1)
                        header[k] = v
                continue
            t, c = line.split()
            nodes.append((t, int(c)))
    p1, p2 = int(header["p1"]), int(header["p2"])
    n = int(header.get("n", "3"))
    pyref.set_size(n)
    winner = Player.BLACK if header["winner"] == "BLACK" else Player.WHITE
    win_res = GameResult.BLACK_WIN if winner == Player.BLACK else GameResult.WHITE_WIN
    stats = {"nodes": len(nodes), "winner_nodes": 0, "loser_nodes": 0, "leaves": 0,
             "loser_cannot_move": 0, "max_len": 0, "illdef": 0}
    pos = [0]

    def nxt():
        if pos[0] >= len(nodes):
            raise CheckError("tree file truncated")
        n = nodes[pos[0]]
        pos[0] += 1
        return n

    def verify(game, nchild, depth):
        """game: ongoing, the position after the edge just read; nchild its child count."""
        if game.result != GameResult.ONGOING:
            raise CheckError("internal node is a finished game")
        turns = enumerate_turns(game)
        mover = game.state.to_move
        if mover == winner:
            stats["winner_nodes"] += 1
            if nchild != 1:
                raise CheckError(f"winner node with {nchild} children")
            if turns in (NOMOVE, ILLDEF):
                raise CheckError("winner cannot move")
            t, c = nxt()
            turn = parse_turn(t)
            if turn not in turns:
                raise CheckError(f"winner turn {t} not legal in game.py")
            child(game, turn, c, depth)
        else:
            stats["loser_nodes"] += 1
            if turns in (NOMOVE, ILLDEF):
                if nchild != 0:
                    raise CheckError("loser cannot move but node has children")
                if turns == ILLDEF:
                    stats["illdef"] += 1
                    raise CheckError("ILLDEF position (undefined in game.py) inside the tree")
                g = clone(game)
                try:
                    g.make_move(0, 0)
                    raise CheckError("expected ForcedUnblockingImpossibleError")
                except ForcedUnblockingImpossibleError:
                    pass
                if g.result != win_res:
                    raise CheckError("loser-cannot-move did not give the win")
                stats["loser_cannot_move"] += 1
                stats["leaves"] += 1
                stats["max_len"] = max(stats["max_len"], depth)
                return
            if nchild != len(turns):
                raise CheckError(f"loser node: tree has {nchild} replies, game.py allows {len(turns)} "
                                 f"at {board_str(game)} debts {game.state.debt_black}/{game.state.debt_white}")
            want = set(turns)
            for _ in range(nchild):
                t, c = nxt()
                turn = parse_turn(t)
                if turn not in want:
                    raise CheckError(f"loser reply {t} missing from game.py's list or duplicated")
                want.remove(turn)
                child(game, turn, c, depth)

    def child(game, turn, c, depth):
        g = clone(game)
        apply_turn(g, turn)
        if g.result == GameResult.ONGOING:
            verify(g, c, depth + 1)
        else:
            if g.result != win_res:
                raise CheckError(f"line ends in a loss for the claimed winner after {turn_str(turn)}")
            if c != 0:
                raise CheckError("finished game has children")
            stats["leaves"] += 1
            stats["max_len"] = max(stats["max_len"], depth + 1)

    root, rc_ = nxt()
    if root != "root":
        raise CheckError("first node must be root")
    game = NexusGame(size=n, p1=p1, p2=p2)
    verify(game, rc_, 0)
    if pos[0] != len(nodes):
        raise CheckError("trailing nodes in tree file")
    print(f"VERIFIED: {winner.name} wins {n}x{n} Nexus (p1={p1}, p2={p2}) from the empty board, Black to move.")
    print(stats)


if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except CheckError as e:
        print("CHECK FAILED:", e)
        sys.exit(1)
