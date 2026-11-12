#!/usr/bin/env bash
# Random-playout measurements behind Table "game-tree complexity" (complexity.tex).
set -euo pipefail
cd "$(dirname "$0")/.."
C=./target/release/complexity
for n in 3 4 5; do $C playout go $n 20000 11; done
for n in 3 4 5; do $C playout nexus $n 20000 12; done
$C playout ego 3 5000 13 0.0
$C playout ego 4 2000 13 0.0
$C playout ego 5 240 13 0.0
$C playout ego 3 5000 14 0.1
$C playout ego 4 2000 14 0.1
$C playout ego 5 120 14 0.1
