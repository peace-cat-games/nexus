"""Sweep the debt prices (p1, p2) on 3x3 Nexus.

For every pair (p1, p2) in the grid and each of the three distinct first
moves of Black (corner -/0/-, edge -/1/-, centre -/4/-; the rules are
symmetric under the 8 symmetries of the square, so these cover all nine
first moves), two provers race: one asks whether Black forces a win, the
other whether White does.  When one proves a win, the other is stopped (both
cannot win).  Each proved win is extracted as a strategy tree.  The value of
the empty board follows: Black wins iff some first move wins for Black, and
White wins iff every first move loses.

Writes one JSON object per (p1, p2, first move) to results/params/runs.jsonl
and the trees to results/params/trees/.  The trees are checked separately, by
tools/check_strategy.py (game.py) and tools/check_strategy_ts.mjs (the Peace
Cat Games TypeScript engine); see tools/check_params.sh.

usage: python3 tools/sweep_params.py [--values 0-16,20,32,100,1000 | --pairs P1:P2,...]
           [--starts corner,edge,centre] [--resume]
           [--jobs 8] [--time 120] [--max-depth 60] [--out results/params]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "..", "target", "release", "nexus-solver")
STARTS = {"corner": "-/0/-", "edge": "-/1/-", "centre": "-/4/-"}


def parse_values(spec):
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def command(p1, p2, start, side, args, tree):
    cmd = [BIN, "prove", "--n", "3", "--p1", str(p1), "--p2", str(p2), "--side", side,
           "--max-depth", str(args.max_depth), "--time", str(args.time), "--max-tt", "2000000",
           "--out", tree]
    if STARTS[start]:
        cmd += ["--line", STARTS[start]]
    return cmd


def parse(text, start, side, tree, out_dir, stopped):
    res = {"side": side, "stopped": stopped, "win_within": None, "no_win_within": None,
           "timeout": "TIMEOUT" in text, "extract_failed": "extraction FAILED" in text,
           "tree": None, "tree_turns": None, "tree_leaves": None, "longest": None,
           "illdef": max([int(m) for m in re.findall(r"illdef (\d+)", text)] or [0]),
           "nodes": max([int(m) for m in re.findall(r"\(total (\d+)\)", text)] or [0])}
    # Depths completed so far (also for a run that was stopped part-way).
    done = [int(m) for m in re.findall(r"depth +(\d+): no forced win", text)]
    if done:
        res["no_win_within"] = max(done) + (1 if STARTS[start] else 0)
    m = re.search(r"forces a win within (\d+) further turns", text)
    if m:
        # Counted from the start of the game, like the no-win bound.
        res["win_within"] = int(m.group(1)) + (1 if STARTS[start] else 0)
    m = re.search(r"strategy: (\d+) turns \((\d+) leaves\), max game length (\d+) turns", text)
    if m:
        res["tree"] = os.path.relpath(tree, out_dir)
        res["tree_turns"], res["tree_leaves"], res["longest"] = map(int, m.groups())
    return res


def job(p1, p2, start, args):
    rec = {"p1": p1, "p2": p2, "start": start}
    tdir = os.path.join(args.out, "trees")
    procs = {}
    for side in ("black", "white"):
        tree = os.path.join(tdir, f"{start}_p1-{p1}_p2-{p2}_{side}.txt")
        f = tempfile.TemporaryFile("w+")
        procs[side] = (subprocess.Popen(command(p1, p2, start, side, args, tree), stdout=f, text=True), f, tree)
    stopped = set()
    while any(p.poll() is None for p, _, _ in procs.values()):
        for side, (p, f, _) in procs.items():
            if p.poll() is not None and p.returncode == 0:
                f.seek(0)
                if "extracted" in f.read():
                    for other, (q, _, _) in procs.items():
                        if other != side and q.poll() is None:
                            q.kill()
                            stopped.add(other)
        time.sleep(0.02)
    for side, (p, f, tree) in procs.items():
        f.seek(0)
        rec[side] = parse(f.read(), start, side, tree, args.out, side in stopped)
        f.close()
    winners = [s for s in ("black", "white") if rec[s]["win_within"] is not None]
    if len(winners) > 1:
        raise SystemExit(f"both sides proved a win at {rec}")
    rec["value"] = winners[0] if winners else "unknown"
    rec["within"] = rec[winners[0]]["win_within"] if winners else None
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--values", default="0-16,20,32,100,1000")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--time", type=int, default=120)
    ap.add_argument("--max-depth", type=int, default=60)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "results", "params"))
    ap.add_argument("--pairs", default="", help="explicit p1:p2 pairs (comma-separated) instead of the grid")
    ap.add_argument("--starts", default=",".join(STARTS), help="first moves to run (corner,edge,centre)")
    ap.add_argument("--resume", action="store_true", help="append to runs.jsonl, skipping runs already in it")
    args = ap.parse_args()
    args.out = os.path.abspath(args.out)
    os.makedirs(os.path.join(args.out, "trees"), exist_ok=True)
    starts = args.starts.split(",")
    if args.pairs:
        pairs = [tuple(int(x) for x in pr.split(":")) for pr in args.pairs.split(",")]
    else:
        vals = parse_values(args.values)
        pairs = [(p1, p2) for p1 in vals for p2 in vals]
    tasks = [(p1, p2, s) for p1, p2 in pairs for s in starts]
    path = os.path.join(args.out, "runs.jsonl")
    if args.resume and os.path.exists(path):
        seen = {(r["p1"], r["p2"], r["start"]) for r in map(json.loads, open(path))}
        tasks = [t for t in tasks if t not in seen]
    done = 0
    with open(path, "a" if args.resume else "w") as f, ThreadPoolExecutor(args.jobs) as ex:
        for rec in ex.map(lambda t: job(*t, args), tasks):
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            f.flush()
            done += 1
            if done % 100 == 0:
                print(f"{done}/{len(tasks)}", file=sys.stderr, flush=True)
    print(f"wrote {done} runs to {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
