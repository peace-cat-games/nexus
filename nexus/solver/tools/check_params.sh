#!/usr/bin/env bash
# Check every strategy tree of the price sweep (results/params/trees) with
# both independent checkers: check_strategy.py (game.py) and
# check_strategy_ts.mjs (the Peace Cat Games engine, draw rule on).
# usage: tools/check_params.sh ENGINE_DIR [JOBS]
set -euo pipefail
cd "$(dirname "$0")"
ENGINE=$1
JOBS=${2:-8}
P=../results/params
ls $P/trees/*.txt > $P/trees.list
echo "$(wc -l < $P/trees.list) trees"
# game.py checker: one process per tree.
xargs -P "$JOBS" -I{} sh -c 'python3 check_strategy.py {} | head -1 | sed "s|^|{}: |"' < $P/trees.list | sort > $P/check_gamepy.log
# Site checker: one Node process per chunk of trees, each with its own log
# (verdict line, then a JSON line of statistics, per tree).
split -n l/"$JOBS" -d $P/trees.list $P/trees.chunk.
ls $P/trees.chunk.* | xargs -P "$JOBS" -I{} sh -c "xargs node --experimental-strip-types --no-warnings check_strategy_ts.mjs '$ENGINE' < {} > {}.log || true"
cat $P/trees.chunk.*.log > $P/check_site_stats.log
grep -E '^(VERIFIED|CHECK FAILED)' $P/check_site_stats.log | sort > $P/check_site.log
rm -f $P/trees.chunk.*
echo "longest capture-free stretch in any line (site engine): $(grep -o '"maxQuiet":[0-9]*' $P/check_site_stats.log | cut -d: -f2 | sort -n | tail -1) turns"
for f in $P/check_gamepy.log $P/check_site.log; do
  echo "$f: $(grep -c VERIFIED $f) verified, $(grep -c 'CHECK FAILED' $f || true) failed"
done
