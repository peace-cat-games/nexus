"""Negative tests for both checkers: corrupted trees must be rejected.

From the main 3x3 strategy (and the centre-opening tree) this writes six
corrupted trees, runs check_strategy.py (game.py) and check_strategy_ts.mjs
(the Peace Cat Games engine) on each, and fails unless both checkers reject
every one.  It also checks that the site checker turns the centre tree into
a draw when the quiet-turn limit is lowered to 5 (the tree reaches 9), and
accepts it with the draw rule off.

usage: python3 mutation_test.py ENGINE_DIR [WORK_DIR]
"""

import copy
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")


def read(path):
    lines = open(path).read().splitlines()
    hdr = [l for l in lines if l.startswith("#")]
    body = [l.split() for l in lines if l and not l.startswith("#")]
    pos = [0]

    def parse():
        t, c = body[pos[0]]
        pos[0] += 1
        return [t, [parse() for _ in range(int(c))]]

    return hdr, parse()


def write(path, hdr, root):
    out = []

    def dump(n):
        out.append(f"{n[0]} {len(n[1])}")
        for ch in n[1]:
            dump(ch)

    dump(root)
    with open(path, "w") as f:
        f.write("\n".join(hdr + out) + "\n")


def white_nodes(n, d, acc):
    """Nodes whose children are White turns (depth odd), with at least 2 children."""
    if d % 2 == 1 and len(n[1]) >= 2:
        acc.append(n)
    for ch in n[1]:
        white_nodes(ch, d + 1, acc)
    return acc


def first_black_leaf(n, d):
    for ch in n[1]:
        if d % 2 == 0 and not ch[1]:
            return ch
        x = first_black_leaf(ch, d + 1)
        if x:
            return x
    return None


def mutants(work):
    hdr, root = read(os.path.join(RES, "strategy_p1-2_p2-4.txt"))
    out = {}

    r = copy.deepcopy(root)
    r[1][0][0] = "-/9/-"  # Black's first move off the board
    out["illegal_winner_turn"] = (hdr, r)

    r = copy.deepcopy(root)
    n = white_nodes(r, 0, [])[0]
    n[1][1] = copy.deepcopy(n[1][0])  # a White reply listed twice
    out["duplicated_reply"] = (hdr, r)

    r = copy.deepcopy(root)
    n = white_nodes(r, 0, [])[0]
    del n[1][-1]  # a White reply missing
    out["missing_reply"] = (hdr, r)

    r = copy.deepcopy(root)
    leaf = first_black_leaf(r, 0)
    s, m, rem = leaf[0].split("/")
    leaf[0] = f"{s}/{(int(m) + 1) % 9}/{rem}"  # a winning Black turn replaced
    out["winning_turn_replaced"] = (hdr, r)

    out["wrong_winner"] = ([h.replace("winner=BLACK", "winner=WHITE") for h in hdr], copy.deepcopy(root))

    chdr, croot = read(os.path.join(RES, "opening_4.txt"))
    out["other_prices"] = ([h.replace("p2=4", "p2=0") for h in chdr], croot)  # White wins the centre at p2=0

    paths = {}
    for name, (h, r) in out.items():
        paths[name] = os.path.join(work, f"mutant_{name}.txt")
        write(paths[name], h, r)
    return paths


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    first = (r.stdout.strip().splitlines() or [""])[0]
    return r.returncode, first


def main():
    engine = sys.argv[1]
    work = sys.argv[2] if len(sys.argv) > 2 else tempfile.mkdtemp()
    os.makedirs(work, exist_ok=True)
    ok = True
    for name, path in mutants(work).items():
        py = run([sys.executable, "check_strategy.py", path], cwd=HERE)
        ts = run(["node", "--experimental-strip-types", "--no-warnings", "check_strategy_ts.mjs", engine, path], cwd=HERE)
        rejected = py[0] != 0 and ts[0] != 0
        ok &= rejected
        print(f"{'ok  ' if rejected else 'FAIL'} {name}\n      game.py: {py[1]}\n      site:    {ts[1]}")
    centre = os.path.join(RES, "opening_4.txt")
    low = run(["node", "--experimental-strip-types", "--no-warnings", "check_strategy_ts.mjs", engine, "--quiet-limit", "5", centre], cwd=HERE)
    off = run(["node", "--experimental-strip-types", "--no-warnings", "check_strategy_ts.mjs", engine, "--no-draw", centre], cwd=HERE)
    draw_ok = low[0] != 0 and "draw" in low[1] and off[0] == 0
    ok &= draw_ok
    print(f"{'ok  ' if draw_ok else 'FAIL'} draw rule\n      limit 5: {low[1]}\n      no draw: {off[1]}")
    print("ALL MUTANTS REJECTED" if ok else "SOME CHECK DID NOT BEHAVE AS EXPECTED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
