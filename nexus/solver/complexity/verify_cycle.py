"""Replay a Nexus debt-pumping cycle through nexus/game.py.

usage: python3 verify_cycle.py N LAPS "path turns" "lap turns"
Prints the debt difference after every lap; superko (game.py) must accept every turn.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import pyref
from pyref import NexusGame, apply_turn, parse_turn, board_str

n, laps, path, lap = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3].split(), sys.argv[4].split()
pyref.set_size(n)
g = NexusGame(size=n, p1=2, p2=4)
for t in path:
    apply_turn(g, parse_turn(t))
start = (board_str(g), g.state.to_move)
d0 = g.state.debt_black - g.state.debt_white
diffs = []
for _ in range(laps):
    for t in lap:
        apply_turn(g, parse_turn(t))
        assert g.result.name == "ONGOING"
    assert (board_str(g), g.state.to_move) == start
    diffs.append(g.state.debt_black - g.state.debt_white)
print(f"start {start[0]} {start[1].name} to move, diff {d0}; after laps 1..{laps}: diffs {diffs[:5]} ... {diffs[-3:]}")
print(f"debts after {laps} laps: Black {g.state.debt_black}, White {g.state.debt_white}; "
      f"history size {len(g.state.position_history)}; all {laps * len(lap) + len(path)} turns accepted by game.py")
