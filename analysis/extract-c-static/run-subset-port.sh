#!/usr/bin/env bash
# Run ligature extract-c-static over the subset-port fixture (chainlink #108)
# and keep the report next to it.
#
# The fixture is copied into a scratch rsync of this pilot because
# extract-c-static requires the descriptor's crate root to exist and
# rust/swisstable-verus-core does not exist in this pilot yet.  Nothing inside
# the pilot is written by this script except subset-port-result.json and
# subset-port-run.txt.
#
# Usage:  ./run-subset-port.sh [target-triple]
set -u

here="$(cd "$(dirname "$0")" && pwd)"
pilot="$(cd "$here/../.." && pwd)"
pyz="$pilot/tools/ligature/ligature.pyz"
target="${1:-x86_64-unknown-linux-gnu}"
scratch="/tmp/opencode/ecs-subset-port"

rm -rf "$scratch"
rsync -a --exclude 'analysis' --exclude 'ci/results' \
      --exclude 'upstream' --exclude 'tools/codesight-mcp' \
      "$pilot/" "$scratch/"
rm -rf "$scratch/rust/swisstable-verus-core"
mkdir -p "$scratch/rust/swisstable-verus-core"
cp -r "$here/subset-port/src" "$scratch/rust/swisstable-verus-core/src"

( cd "$scratch" && "$pyz" extract-c-static --target "$target" ) \
  > "$here/subset-port-run.txt" 2>&1
echo "exit=$?" >> "$here/subset-port-run.txt"
cp "$scratch/ci/results/c_static/rust_swisstable-verus-core.json" \
   "$here/subset-port-result.json"

cat "$here/subset-port-run.txt"
rm -rf "$scratch"
