#!/usr/bin/env bash
# Replays the chainlink #158 verifier-fit probes and checks each expected result.
# Verus and Creusot both run in this pilot's crypto-mixed shell. The Creusot
# probes borrow date-creusot's crate skeleton (its Cargo files,
# .cargo/config.toml and the pinned creusot-std link), read only. Every probe
# builds in a temporary directory; nothing in either pilot is written.
# Logs go to logs/ next to this script.
set -uo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
PILOT=$(cd "$HERE/../../.." && pwd)
WS=$(cd "$PILOT/.." && pwd)
FLAKE="path:$WS"
P1_CRATE="$WS/date-creusot/rust/date-creusot-core"
LOGS="$HERE/logs"
TMP=$(mktemp -d)
trap 'chmod -R u+w "$TMP" 2>/dev/null; rm -rf "$TMP"' EXIT
mkdir -p "$LOGS"

for f in core stdcalls; do
  dir="$TMP/creusot-$f"
  rsync -a --exclude target --exclude verif --exclude src --exclude tests \
    --exclude specs --exclude .why3find "$P1_CRATE/" "$dir/"
  chmod -R u+w "$dir"
  sed -i "s/^name = \"date-creusot-core\"/name = \"probe-p3-$f\"/" "$dir/Cargo.toml"
  mkdir -p "$dir/src" && cp "$HERE/creusot/$f.rs" "$dir/src/lib.rs"
done

nix develop "$FLAKE#crypto-mixed" --command bash -c "
  cd '$HERE/verus'
  { command -v verus; verus --version; } > '$LOGS/verus-version.txt' 2>&1
  for f in add rot qr qr_mutant le poly poly_hinted stdcalls; do
    verus \$f.rs > '$LOGS/verus-'\$f'.log' 2>&1
    echo \"exit=\$?\" >> '$LOGS/verus-'\$f'.log'
  done
  cargo creusot version > '$LOGS/creusot-version.txt' 2>&1
  for f in core stdcalls; do
    cd '$TMP/creusot-'\$f
    CARGO_TARGET_DIR='$TMP/creusot-target' cargo creusot > '$LOGS/creusot-'\$f'.log' 2>&1
    echo \"exit=\$?\" >> '$LOGS/creusot-'\$f'.log'
  done
" > /dev/null 2>&1

fail=0
expect() { # expect <log> <exit> <pattern>
  local log="$LOGS/$1.log"
  if grep -q "^exit=$2\$" "$log" && grep -q -- "$3" "$log"; then
    echo "ok    $1: exit $2, $(grep -m1 -o -- "$3.*" "$log" | cut -c1-90)"
  else
    echo "FAIL  $1: wanted exit $2 and '$3'"; fail=1
  fi
}
absent() { # absent <log> <pattern>: a goal that must have proved
  if grep -q -- "$2" "$LOGS/$1.log"; then echo "FAIL  $1: found '$2'"; fail=1
  else echo "ok    $1: no '$2'"; fi
}
expect verus-add         0 "2 verified, 0 errors"
expect verus-rot         1 "rotate_left\` is not supported"
expect verus-qr          0 "3 verified, 0 errors"
expect verus-qr_mutant   1 "2 verified, 1 errors"
expect verus-le          1 "from_le_bytes\` is not supported"
expect verus-poly        1 "possible arithmetic underflow/overflow"
expect verus-poly_hinted 0 "7 verified, 0 errors"
expect verus-stdcalls    1 "aborting due to 6 previous errors"
expect creusot-core      1 "4 unproved files"
absent creusot-core "vc_add:"
absent creusot-core "vc_rotl_exec:"
absent creusot-core "vc_qr:"
absent creusot-core "vc_d0:"
expect creusot-core      1 "vc_qr_mutant: ✘"
expect creusot-core      1 "vc_d0_mutant: ✘"
expect creusot-stdcalls  1 "5 unproved files"
[ $fail -eq 0 ] && echo "replay ok" || { echo "replay FAILED"; exit 1; }
