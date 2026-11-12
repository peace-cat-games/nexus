"""Cross-check the history-aware transposition table of `nexus-solver prove`.

Random playouts (through game.py) give start lines that contain captures,
audits and unblocking, so the superko history matters.  From each start, for
both sides, `prove` is run with stored TT values (the sound reuse rule) and
with the table used for move ordering only (pure exact search).  The per-depth
answers must agree.

usage: python3 crosscheck_tt.py --n N [--lines L] [--depth D] [--seed S]
"""

import argparse
import random
import subprocess
import os

import pyref
from pyref import NexusGame, enumerate_turns, apply_turn, turn_str, NOMOVE, ILLDEF

BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "target", "release", "nexus-solver")


def random_line(rng, n, min_len, max_len):
    """A random game prefix; prefers lines in which a capture or removal happened."""
    g = NexusGame(size=n, p1=2, p2=4)
    line = []
    removals = 0
    for _ in range(rng.randint(min_len, max_len)):
        turns = enumerate_turns(g)
        if turns in (NOMOVE, ILLDEF):
            break
        before = sum(v != 0 for row in g.board for v in row)
        t = rng.choice(turns)
        h = NexusGame(size=n, p1=2, p2=4)
        h.state = g.state.copy()
        apply_turn(h, t)
        if h.result.name != "ONGOING":
            break
        g = h
        line.append(turn_str(t))
        after = sum(v != 0 for row in g.board for v in row)
        removals += after <= before
    return line, removals


def run(n, line, side, depth, tt_values):
    cmd = [BIN, "prove", "--n", str(n), "--side", side, "--max-depth", str(depth), "--time", "120",
           "--line", " ".join(line), "--out", os.devnull]
    if not tt_values:
        cmd.append("--no-tt-values")
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return [ln.split()[2] for ln in out.splitlines() if ln.startswith("depth")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--lines", type=int, default=40)
    ap.add_argument("--depth", type=int, default=7)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    pyref.set_size(a.n)
    rng = random.Random(a.seed)
    bad = done = with_removal = 0
    while done < a.lines:
        line, rem = random_line(rng, a.n, 4, 4 * a.n * a.n)
        if rem == 0 and rng.random() < 0.8:
            continue
        with_removal += rem > 0
        for side in ("black", "white"):
            r1 = run(a.n, line, side, a.depth, True)
            r2 = run(a.n, line, side, a.depth, False)
            if r1 != r2:
                bad += 1
                print("MISMATCH", side, " ".join(line), r1, r2)
        done += 1
    print(f"n={a.n}: {done} start lines ({with_removal} with captures/removals), both sides, depth <= {a.depth}: "
          f"{bad} mismatches")


if __name__ == "__main__":
    main()
