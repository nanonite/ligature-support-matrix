#!/usr/bin/env bash
# Capture the Cargo-side transcripts for rust/swisstable-verus-core.
#
#   analysis/verus/run-cargo.sh
#
# Writes, overwritten on every run so nothing stale can survive:
#   analysis/verus/cargo-transcript.txt   cargo build / cargo test / cargo verus verify
#
# `run-verus.sh` is the Verus-side runner and stays authoritative for the
# verified/error counts; this one exists because the crate has a Cargo package
# (chainlink #115 scaffold, completed under the 2026-10-03 operator authorisation)
# and it is worth having its three Cargo entry points on disk rather than only in
# a comment.  See `findings/limitations.jsonl` `swisstable-verus-010` for what each
# of the three actually proves about a Verus crate.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pilot="$(cd "$here/../.." && pwd)"
workspace="$(cd "$pilot/.." && pwd)"
crate="$pilot/rust/swisstable-verus-core"

mkdir -p "$here"

run() { # <label> <subcommand...>
  local label="$1"; shift
  {
    echo "\$ nix develop $workspace#swisstable-verus -c 'cargo $*'"
    echo "# cwd: $crate"
    echo
    nix develop "$workspace#swisstable-verus" -c bash -lc \
      "cd '$crate' && cargo $* 2>&1"
    echo "exit=$?"
  } 2>&1
}

{
  echo "=== cargo build"
  run build build
  echo
  echo "=== cargo test"
  run test test
  echo
  echo "=== cargo verus verify"
  # Cargo fingerprints the crate by mtime and a second `cargo verus verify` is a
  # no-op that prints no `verification results` line at all -- so the transcript
  # would record a green run that verified nothing.  Touching the crate root
  # forces the verification to re-run without rebuilding vstd.
  touch "$crate/src/lib.rs"
  run verify verus verify
} >"$here/cargo-transcript.txt"

echo "--- cargo"
grep -E "^=== |^exit=|^error|Finished .* profile|verification results|test result" \
  "$here/cargo-transcript.txt" || echo "(no summary lines)"
echo "    -> $here/cargo-transcript.txt"