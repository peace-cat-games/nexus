"""Summarise the price sweep (results/params/runs.jsonl).

Prints, for each first move (corner, edge, centre) and for the empty board, a
grid over (p1, p2): `B9` = Black forces a win within 9 turns, `W14` = White
does within 14, `?` = neither proved within the limits.  The empty board's
value follows from the first moves: Black wins iff some first move wins for
Black, within the smallest of those depths; White wins iff every first move
loses, within the largest of White's depths.  Writes results/params/summary.csv.

usage: python3 tools/summarize_params.py [results/params]
"""

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def cell(v, d):
    return {"black": f"B{d}", "white": f"W{d}"}.get(v, "?")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "results", "params")
    rs = [json.loads(l) for l in open(os.path.join(out, "runs.jsonl"))]
    by = {(r["p1"], r["p2"], r["start"]): r for r in rs}
    vals = sorted({r["p1"] for r in rs} | {r["p2"] for r in rs})
    starts = ["corner", "edge", "centre"]
    root = {}
    for p1 in vals:
        for p2 in vals:
            rr = [by.get((p1, p2, s)) for s in starts]
            if any(r is None for r in rr):
                continue
            bw = [r["within"] for r in rr if r["value"] == "black"]
            if bw:
                root[(p1, p2)] = ("black", min(bw))
            elif all(r["value"] == "white" for r in rr):
                root[(p1, p2)] = ("white", max(r["within"] for r in rr))
            else:
                root[(p1, p2)] = ("unknown", None)
    grids = [(s, lambda p1, p2, s=s: (by[(p1, p2, s)]["value"], by[(p1, p2, s)]["within"]) if (p1, p2, s) in by else None)
             for s in starts]
    grids.append(("empty board", lambda p1, p2: root.get((p1, p2))))
    for name, get in grids:
        print(f"\n{name}: rows p1, columns p2")
        print("p1\\p2 " + " ".join(f"{v:>4}" for v in vals))
        for p1 in vals:
            row = []
            for p2 in vals:
                x = get(p1, p2)
                row.append(f"{cell(*x) if x else '':>4}")
            print(f"{p1:>5} " + " ".join(row))
    with open(os.path.join(out, "summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["p1", "p2", "start", "value", "within", "black_no_win_within", "white_no_win_within",
                    "tree", "tree_turns", "longest", "illdef"])
        for r in sorted(rs, key=lambda r: (r["p1"], r["p2"], starts.index(r["start"]))):
            win = r.get(r["value"]) if r["value"] in ("black", "white") else None
            w.writerow([r["p1"], r["p2"], r["start"], r["value"], r["within"],
                        r["black"]["no_win_within"], r["white"]["no_win_within"],
                        win["tree"] if win else "", win["tree_turns"] if win else "", win["longest"] if win else "",
                        max(r["black"]["illdef"], r["white"]["illdef"])])
        for (p1, p2), (v, d) in sorted(root.items()):
            w.writerow([p1, p2, "empty", v, d, "", "", "", "", "", ""])
    illdef = sum(1 for r in rs if r["black"]["illdef"] or r["white"]["illdef"])
    failed = sum(1 for r in rs if r["black"]["extract_failed"] or r["white"]["extract_failed"])
    print(f"\n{len(rs)} runs; {illdef} with the undefined case (I6); {failed} extraction failures")


if __name__ == "__main__":
    main()
