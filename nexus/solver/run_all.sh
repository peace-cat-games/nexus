#!/usr/bin/env bash
# Build, differential-test, solve (exact mode) and independently verify 3x3 Nexus, p1=2 p2=4.
set -euo pipefail
cd "$(dirname "$0")"
cargo build --release
python3 tools/difftest.py --games 3000 --random 30000 --seed 2
mkdir -p results
./target/release/nexus-solver solve --no-tt --time 600 --max-depth 30 --out results/strategy_p1-2_p2-4.txt
for m in 0 1 2 3 4 5 6 7 8; do
  ./target/release/nexus-solver solve --no-tt --first $m --time 600 --max-depth 30 --out results/opening_$m.txt
done
cd tools
for f in ../results/strategy_p1-2_p2-4.txt ../results/opening_*.txt; do
  echo "== $f"; python3 check_strategy.py "$f"
done
python3 show_tree.py ../results/strategy_p1-2_p2-4.txt --json ../results/strategy_p1-2_p2-4.json
