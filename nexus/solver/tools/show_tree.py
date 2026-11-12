"""Print principal variations of a strategy tree and/or export it as JSON.

The principal variation follows the winner's moves and, at each loser node,
the reply with the deepest remaining subtree (longest resistance).  Boards and
debts are obtained by replaying through nexus/game.py.

usage: python3 show_tree.py STRATEGY_FILE [--json OUT.json] [--all-replies]
  --all-replies : also print, for the root's loser node, each reply and how many
                  turns the game then lasts at most.
"""

import argparse
import json
from pyref import NexusGame, GameResult, apply_turn, clone, parse_turn, board_str, rc


def load(path):
    header, nodes = {}, []
    for line in open(path):
        if line.startswith("#"):
            for tok in line[1:].split():
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    header[k] = v
            continue
        t, c = line.split()
        nodes.append((t, int(c)))
    it = iter(nodes)

    def build():
        t, c = next(it)
        return {"turn": t, "children": [build() for _ in range(c)]}

    return header, build()


def height(n):
    n["height"] = 0 if not n["children"] else 1 + max(height(ch) for ch in n["children"])
    return n["height"]


def annotate(n, game):
    """Attach board/debts/to_move (after n's turn) for JSON export."""
    n["board"] = board_str(game)
    n["debt_black"], n["debt_white"] = game.state.debt_black, game.state.debt_white
    n["to_move"] = game.state.to_move.name if game.result == GameResult.ONGOING else None
    n["result"] = game.result.name
    for ch in n["children"]:
        g = clone(game)
        apply_turn(g, parse_turn(ch["turn"]))
        annotate(ch, g)


def describe(turn_s, mover):
    S, m, R = parse_turn(turn_s)
    s = f"{mover} {rc(m)}"
    if S:
        s = f"{mover} unblocks {[rc(i) for i in S]} then plays {rc(m)}"
    if R:
        s += f", removes {[rc(i) for i in R]} in the audit"
    return s


def show_board(b):
    return "\n".join("    " + " ".join(b[3 * r:3 * r + 3]) for r in range(3))


def pv(root, game):
    n = root
    k = 0
    while n["children"]:
        ch = max(n["children"], key=lambda c: c["height"])
        mover = game.state.to_move.name
        apply_turn(game, parse_turn(ch["turn"]))
        k += 1
        print(f"{k:2d}. {describe(ch['turn'], mover)}   debts B={game.state.debt_black} W={game.state.debt_white}"
              f"   {'-> ' + game.result.name if game.result != GameResult.ONGOING else ''}")
        print(show_board(board_str(game)))
        n = ch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree")
    ap.add_argument("--json")
    ap.add_argument("--all-replies", action="store_true")
    a = ap.parse_args()
    header, root = load(a.tree)
    height(root)
    game = NexusGame(size=3, p1=int(header["p1"]), p2=int(header["p2"]))
    print(f"tree {a.tree}: winner {header['winner']}, max game length {root['height']} turns")
    if a.all_replies:
        first = root["children"][0]
        print(f"after {first['turn']}: replies and remaining length:")
        for ch in sorted(first["children"], key=lambda c: -c["height"]):
            print(f"   {ch['turn']}: game over within {1 + ch['height']} more turns")
    print("principal variation (longest resistance):")
    pv(root, NexusGame(size=3, p1=int(header["p1"]), p2=int(header["p2"])))
    if a.json:
        annotate(root, game)
        with open(a.json, "w") as f:
            json.dump({"header": header, "tree": root}, f)
        print("wrote", a.json)


if __name__ == "__main__":
    main()
