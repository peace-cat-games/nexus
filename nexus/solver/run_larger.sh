#!/usr/bin/env bash
# 4x4 and 5x5 Nexus (p1=2, p2=4): differential tests, TT cross-checks and the
# 45-minute "does X force a win within d turns" searches (results/larger/).
# The four searches run concurrently (about 3.5 GB in total).
set -euo pipefail
cd "$(dirname "$0")"
cargo build --release
L=results/larger
mkdir -p $L
(cd tools
 python3 difftest.py --n 3 --games 3000 --random 30000 --seed 2 > ../$L/difftest_n3.log
 python3 difftest.py --n 4 --games 2000 --random 15000 --seed 4 --max-turns 120 > ../$L/difftest_n4.log
 python3 difftest.py --n 5 --games 1000 --random 8000 --seed 5 --max-turns 150 > ../$L/difftest_n5.log
 python3 crosscheck_tt.py --n 3 --lines 60 --depth 10 --seed 3 > ../$L/crosscheck_tt_n3.log
 python3 crosscheck_tt.py --n 4 --lines 40 --depth 8 --seed 4 > ../$L/crosscheck_tt_n4.log
 python3 crosscheck_tt.py --n 5 --lines 20 --depth 6 --seed 5 > ../$L/crosscheck_tt_n5.log
 python3 crosscheck_tt.py --n 3 --lines 150 --depth 12 --seed 31 > ../$L/crosscheck_tt_n3_deep.log
 python3 crosscheck_tt.py --n 4 --lines 100 --depth 10 --seed 41 > ../$L/crosscheck_tt_n4_deep.log
 python3 crosscheck_tt.py --n 5 --lines 60 --depth 8 --seed 51 > ../$L/crosscheck_tt_n5_deep.log)
for n in 4 5; do
  mt=$([ $n = 4 ] && echo 6000000 || echo 4000000)
  for s in black white; do
    ./target/release/nexus-solver prove --n $n --side $s --time 2700 --max-tt $mt \
      --out $L/strategy_${n}x${n}_$s.txt > $L/prove_${n}x${n}_$s.log &
  done
done
wait
# Any extracted strategy would be checked with: (cd tools; python3 check_strategy.py ../$L/strategy_*.txt)
