#!/usr/bin/env bash
# Capture the two Verus transcripts that back findings/limitations.jsonl.
#
#   analysis/verus/run-verus.sh
#
# Writes, both overwritten on every run so nothing stale can survive:
#   analysis/verus/verus-transcript.txt        the crate
#   analysis/verus/reachability-probe.txt      the bitwise probe
#
# analysis/ligature/write-findings-30.py reads its counts out of these files; it
# has no hardcoded result strings, so a finding can never claim an output that is
# not on disk.
#
# The declared crate now has a Ligature-scaffolded Cargo.toml, but the generic
# scaffold does not yet provide Cargo-Verus's pinned `vstd` dependency or
# `[package.metadata.verus] verify = true`.  Until a sanctioned configuration
# path is available, drive Verus directly on the crate root.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pilot="$(cd "$here/../.." && pwd)"
workspace="$(cd "$pilot/.." && pwd)"
crate=rust/swisstable-verus-core
errors="${VERUS_ERROR_BUDGET:-200}"

mkdir -p "$here"

capture() { # <outfile> <label> <entrypoint>
  local out="$here/$1" label="$2" entry="$3"
  # `verus --crate-type=lib` drops a `<stem>.rlib` beside the entrypoint; keep the
  # tree clean by sending it to the crate's own target/ (an allowed write root).
  mkdir -p "$pilot/rust/swisstable-verus-core/target"
  local stem; stem="$(basename "$entry" .rs)"
  {
    echo "\$ nix develop $workspace#swisstable-verus -c 'verus --crate-type=lib --multiple-errors $errors $entry'"
    echo "# cwd: $pilot"
    echo
    nix develop "$workspace#swisstable-verus" -c bash -lc \
      "cd '$pilot' && verus --crate-type=lib --multiple-errors $errors $entry"
    echo "exit=$?"
  } >"$out" 2>&1
  rm -f "$pilot/lib$stem.rlib"
  echo "--- $label"
  grep -E "verification results" "$out" || echo "(no results line: the run did not reach one)"
  grep -cE "^error" "$out" | sed 's/^/    ^error lines: /'
  echo "    -> $out"
}

capture verus-transcript.txt "crate" "$crate/src/lib.rs"
capture reachability-probe.txt "bitwise probe" "$crate/verif/reachability_probe.rs"

echo "--- error distribution, crate"
python3 "$here/err-summary.py" "$here/verus-transcript.txt"
