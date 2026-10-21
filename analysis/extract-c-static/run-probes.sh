#!/usr/bin/env bash
# Controlled extract-c-static probe matrix (chainlink #108).
#
# Each probes/NN-name.rs becomes the whole src/lib.rs of a scratch copy of this
# pilot, so the report's counters (discovered / resolved / unresolved,
# unattributed_call_sites, out_of_scope_call_sites, macro_invocations) belong to
# exactly one shape and cannot be contaminated by a neighbour.  Nothing is
# written inside the pilot except this directory: every run happens on an
# rsync copy under /tmp/opencode/, because extract-c-static needs a crate
# directory to exist and this pilot's rust/swisstable-verus-core does not yet
# (that crate is a later issue, and its Cargo.toml is a protected_root).
#
# Usage:  ./run-probes.sh [target-triple]
set -u

here="$(cd "$(dirname "$0")" && pwd)"
pilot="$(cd "$here/../.." && pwd)"
pyz="$pilot/tools/ligature/ligature.pyz"
target="${1:-x86_64-unknown-linux-gnu}"
scratch="/tmp/opencode/ecs-probe"
out="$here/results"

mkdir -p "$out"
rm -rf "$scratch"

echo "== ligature version =="
( cd "$pilot/tools/ligature" && sha256sum -c SHA256SUMS )
"$pyz" version

for probe in "$here"/probes/[0-9][0-9]-*.rs; do
  name="$(basename "$probe" .rs)"
  rm -rf "$scratch"
  rsync -a --exclude 'analysis' --exclude 'ci/results' \
        --exclude 'upstream' --exclude 'tools/codesight-mcp' \
        "$pilot/" "$scratch/"
  mkdir -p "$scratch/rust/swisstable-verus-core/src"
  cp "$probe" "$scratch/rust/swisstable-verus-core/src/lib.rs"

  (
    cd "$scratch"
    "$pyz" extract-c-static --target "$target"
  ) > "$out/$name.txt" 2>&1
  echo "exit=$?" >> "$out/$name.txt"
  cp "$scratch/ci/results/c_static/rust_swisstable-verus-core.json" \
     "$out/$name.json" 2>/dev/null || echo "NO REPORT" >> "$out/$name.txt"
  printf '%-34s %s\n' "$name" "$(tail -n 2 "$out/$name.txt" | tr '\n' ' ')"
done

rm -rf "$scratch"
echo "== done: $(ls "$out"/*.json 2>/dev/null | wc -l) reports in $out =="
