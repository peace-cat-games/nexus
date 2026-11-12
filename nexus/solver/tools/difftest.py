"""Differential test: Rust move generator vs nexus/game.py.

For each test position, game.py (via pyref.canonical) and `nexus-solver movegen`
each list every turn of the side to move together with its outcome (mover wins /
mover loses / continuing board + both debts).  The two lists must be identical.

Positions come from (a) random playouts from the empty board (realistic
histories, so superko is exercised), mostly under p1=2, p2=4, and (b) random
boards with random debts, random side to move and histories seeded with keys
that one placement from the position would recreate (forcing ko hits), with a
bias towards nearly full boards (forced unblocking).

usage: python3 difftest.py [--games G] [--random R] [--seed S]
"""

import argparse
import random
import subprocess
import sys
import os

from pyref import (
    NexusGame, Player, BLACK, WHITE, EMPTY, NOMOVE, ILLDEF,
    canonical, enumerate_turns, apply_turn, clone, position_line,
)

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "..", "target", "release", "nexus-solver")


def pick_params(rng):
    if rng.random() < 0.6:
        return 2, 4
    return rng.randint(0, 6), rng.randint(0, 6)


def playouts(rng, games, max_turns=80):
    for _ in range(games):
        p1, p2 = pick_params(rng)
        g = NexusGame(size=3, p1=p1, p2=p2)
        for _ in range(max_turns):
            yield g
            turns = enumerate_turns(g)
            if turns in (NOMOVE, ILLDEF):
                break
            apply_turn(g, rng.choice(turns))
            if g.result.name != "ONGOING":
                break


def one_step_keys(g):
    """Post-capture (board, diff) keys reachable by one placement (ko bait)."""
    keys = []
    player = g.state.to_move
    stone = BLACK if player == Player.BLACK else WHITE
    for r in range(3):
        for c in range(3):
            if g.board[r][c] != EMPTY:
                continue
            h = clone(g)
            h.board[r][c] = stone
            cap = h._capture_groups_if_needed(player, (r, c))
            h.state.add_debt(player, cap * h.state.p1)
            keys.append(h.state.get_position_key())
    return keys


def random_positions(rng, count):
    for _ in range(count):
        p1, p2 = pick_params(rng)
        g = NexusGame(size=3, p1=p1, p2=p2)
        empties = rng.choice([0, 0, 1, 1, 2, 3, 4, 5, 9])
        cells = list(range(9))
        rng.shuffle(cells)
        board = [[EMPTY] * 3 for _ in range(3)]
        pb = rng.random()
        for i in cells[empties:]:
            board[i // 3][i % 3] = BLACK if rng.random() < pb else WHITE
        to_move = rng.choice([Player.BLACK, Player.WHITE])
        g.set_position(board, to_move=to_move, debt_black=rng.choice([0, 0, 2, 4, 6, 8, 12, rng.randint(0, 20)]),
                       debt_white=rng.choice([0, 0, 2, 4, 6, 8, 12, rng.randint(0, 20)]))
        hist = set()
        for k in one_step_keys(g):
            if rng.random() < 0.4:
                hist.add(k)
        # keys of positions one removal away (relevant to unblocking sets)
        for _ in range(rng.randint(0, 4)):
            h = clone(g)
            occ = [(r, c) for r in range(3) for c in range(3) if h.board[r][c] != EMPTY]
            if occ:
                r, c = rng.choice(occ)
                h.board[r][c] = EMPTY
                for k in one_step_keys(h):
                    if rng.random() < 0.3:
                        hist.add(k)
        g.state.position_history = hist
        yield g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=300)
    ap.add_argument("--random", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    lines, expected = [], []
    stats = {"positions": 0, "nomove": 0, "illdef": 0, "unblock": 0, "audit_choice": 0, "ko_limited": 0}
    gens = [playouts(rng, a.games), random_positions(rng, a.random)]
    for gen in gens:
        for g in gen:
            exp = canonical(g)
            lines.append(position_line(g))
            expected.append(exp)
            stats["positions"] += 1
            if exp == NOMOVE:
                stats["nomove"] += 1
            elif exp == ILLDEF:
                stats["illdef"] += 1
            else:
                if any(not t.startswith("-/") for t in exp.split()):
                    stats["unblock"] += 1
                if any(t.split("=")[0].split("/")[2] != "-" for t in exp.split()):
                    stats["audit_choice"] += 1
            if g.state.position_history:
                # did superko remove a placement that is otherwise Go-legal?
                h = clone(g)
                h.state.position_history = set()
                if len(h.legal_moves()) != len(g.legal_moves()):
                    stats["ko_limited"] += 1
    out = subprocess.run([BIN, "movegen"], input="\n".join(lines) + "\n", capture_output=True, text=True, check=True)
    got = out.stdout.splitlines()
    assert len(got) == len(expected), (len(got), len(expected))
    bad = 0
    for ln, e, r in zip(lines, expected, got):
        if e != r:
            bad += 1
            if bad <= 5:
                print("MISMATCH\n  pos:  ", ln, "\n  py:   ", e, "\n  rust: ", r)
    print(stats)
    print(f"{len(expected)} positions compared, {bad} mismatches")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
