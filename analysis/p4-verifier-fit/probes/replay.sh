#!/usr/bin/env bash
# Replays the chainlink #156 verifier-fit probes and checks each expected result.
# Verus runs in the crypto-mixed shell (the date-creusot shell has no Verus).
# Kani runs one harness at a time on a temporary copy of the P1 crate, so the
# pilot's own crate and target directory are never touched.
# Logs are written to logs/ next to this script.
set -uo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
PILOT=$(cd "$HERE/../../.." && pwd)
WS=$(cd "$PILOT/.." && pwd)
FLAKE="path:$WS"
LOGS="$HERE/logs"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$LOGS"

nix develop "$FLAKE#crypto-mixed" --command bash -c "
  cd '$HERE/verus'
  { command -v verus; verus --version; } > '$LOGS/verus-version.txt' 2>&1
  for f in div yoe civil civil_rlimit mutant_spec mutant_rt; do
    verus \$f.rs > '$LOGS/verus-'\$f'.log' 2>&1
    echo \"exit=\$?\" >> '$LOGS/verus-'\$f'.log'
  done
" > /dev/null 2>&1

rsync -a --exclude target --exclude verif "$PILOT/rust/date-creusot-core/" "$TMP/crate/"
cp "$HERE/kani/kani_probe.rs" "$TMP/crate/src/kani_probe.rs"
printf '\n#[cfg(kani)]\nmod kani_probe;\n' >> "$TMP/crate/src/lib.rs"
nix develop "$FLAKE#date-creusot" --command bash -c "
  cd '$TMP/crate'
  { command -v cargo-kani; cargo kani --version; } > '$LOGS/kani-version.txt' 2>&1
  for h in round_trip_full_domain round_trip_reachable round_trip_mutant; do
    CARGO_TARGET_DIR='$TMP/target' cargo kani --harness \$h > '$LOGS/kani-'\$h'.log' 2>&1
    echo \"exit=\$?\" >> '$LOGS/kani-'\$h'.log'
  done
" > /dev/null 2>&1

fail=0
expect() { # expect <log> <exit> <pattern>
  local log="$LOGS/$1.log"
  if grep -q "^exit=$2\$" "$log" && grep -q -- "$3" "$log"; then
    echo "ok    $1: exit $2, $(grep -m1 -o -- "$3.*" "$log")"
  else
    echo "FAIL  $1: wanted exit $2 and '$3'"; fail=1
  fi
}
expect verus-div          0 "4 verified, 0 errors"
expect verus-yoe          0 "2 verified, 0 errors"
expect verus-civil        1 "2 verified, 2 errors"
expect verus-civil_rlimit 0 "4 verified, 0 errors"
expect verus-mutant_spec  1 "2 verified, 2 errors"
expect verus-mutant_rt    1 "3 verified, 1 errors"
expect kani-round_trip_full_domain 0 "VERIFICATION:- SUCCESSFUL"
expect kani-round_trip_reachable   0 "1 of 1 cover properties satisfied"
expect kani-round_trip_mutant      1 "VERIFICATION:- FAILED"
[ $fail -eq 0 ] && echo "replay ok" || { echo "replay FAILED"; exit 1; }
