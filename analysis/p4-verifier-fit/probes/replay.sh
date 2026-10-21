#!/usr/bin/env bash
# Replays the chainlink #157 verifier-fit probes and checks each expected result.
# Verus and Kani run in this pilot's swisstable-verus shell; Creusot runs in the
# date-creusot shell. The Creusot probes borrow date-creusot's crate skeleton
# (its Cargo files, .cargo/config.toml and the pinned creusot-std link), read
# only. Every probe builds in a temporary directory; nothing in either pilot is
# written. Logs go to logs/ next to this script.
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

nix develop "$FLAKE#swisstable-verus" --command bash -c "
  cd '$HERE/verus'
  { command -v verus; verus --version; } > '$LOGS/verus-version.txt' 2>&1
  for f in set_ext set_ext_manual bits; do
    verus \$f.rs > '$LOGS/verus-'\$f'.log' 2>&1
    echo \"exit=\$?\" >> '$LOGS/verus-'\$f'.log'
  done
" > /dev/null 2>&1

for f in set_ext set_ext_mutant bits_plain bits; do
  dir="$TMP/creusot-$f"
  rsync -a --exclude target --exclude verif --exclude src --exclude tests \
    --exclude specs --exclude .why3find "$P1_CRATE/" "$dir/"
  chmod -R u+w "$dir"
  sed -i "s/^name = \"date-creusot-core\"/name = \"probe-${f//_/-}\"/" "$dir/Cargo.toml"
  mkdir -p "$dir/src" && cp "$HERE/creusot/$f.rs" "$dir/src/lib.rs"
done
nix develop "$FLAKE#date-creusot" --command bash -c "
  cargo creusot version > '$LOGS/creusot-version.txt' 2>&1
  for f in set_ext set_ext_mutant bits_plain bits; do
    cd '$TMP/creusot-'\$f
    CARGO_TARGET_DIR='$TMP/creusot-target' cargo creusot > '$LOGS/creusot-'\$f'.log' 2>&1
    echo \"exit=\$?\" >> '$LOGS/creusot-'\$f'.log'
  done
" > /dev/null 2>&1

rsync -a --exclude target "$PILOT/rust/swisstable-verus-core/" "$TMP/p2/"
cp "$HERE/kani/p2_probe.rs" "$TMP/p2/src/kani_probe.rs"
printf '\n#[cfg(kani)]\nmod kani_probe;\n' >> "$TMP/p2/src/lib.rs"
rsync -a "$HERE/kani/upstream_shapes/" "$TMP/shapes/"
nix develop "$FLAKE#swisstable-verus" --command bash -c "
  { command -v cargo-kani; cargo kani --version; } > '$LOGS/kani-version.txt' 2>&1
  cd '$TMP/p2'
  # --harness matches substrings; --exact keeps insert_contains_erase from also
  # running insert_contains_erase_mutant.
  for h in insert_contains_erase insert_contains_erase_mutant; do
    CARGO_TARGET_DIR='$TMP/p2-target' cargo kani --exact --harness kani_probe::\$h > '$LOGS/kani-p2-'\$h'.log' 2>&1
    echo \"exit=\$?\" >> '$LOGS/kani-p2-'\$h'.log'
  done
  cd '$TMP/shapes'
  for h in sse2_match_equals_scalar sse2_empty_or_deleted_equals_scalar raw_slots_insert_get_erase raw_slots_uninit_read_mutant; do
    CARGO_TARGET_DIR='$TMP/shapes-target' cargo kani --harness \$h > '$LOGS/kani-shapes-'\$h'.log' 2>&1
    echo \"exit=\$?\" >> '$LOGS/kani-shapes-'\$h'.log'
  done
  CARGO_TARGET_DIR='$TMP/shapes-target' cargo kani -Z uninit-checks --harness raw_slots_uninit_read_mutant > '$LOGS/kani-shapes-uninit-checks.log' 2>&1
  echo \"exit=\$?\" >> '$LOGS/kani-shapes-uninit-checks.log'
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
expect verus-set_ext          1 "2 verified, 2 errors"
expect verus-set_ext_manual   0 "2 verified, 0 errors"
expect verus-bits             0 "8 verified, 0 errors"
expect creusot-set_ext        0 "Proved (2 files)"
expect creusot-set_ext_mutant 1 "vc_erase_ext_mutant"
expect creusot-bits_plain     1 "3 unproved files"
expect creusot-bits           1 "vc_h1"
expect kani-p2-insert_contains_erase        0 "VERIFICATION:- SUCCESSFUL"
expect kani-p2-insert_contains_erase_mutant 1 "VERIFICATION:- FAILED"
expect kani-shapes-sse2_match_equals_scalar            0 "VERIFICATION:- SUCCESSFUL"
expect kani-shapes-sse2_empty_or_deleted_equals_scalar 0 "VERIFICATION:- SUCCESSFUL"
expect kani-shapes-raw_slots_insert_get_erase          0 "VERIFICATION:- SUCCESSFUL"
expect kani-shapes-raw_slots_uninit_read_mutant        0 "VERIFICATION:- SUCCESSFUL"
expect kani-shapes-uninit-checks                       1 "is not supported"
[ $fail -eq 0 ] && echo "replay ok" || { echo "replay FAILED"; exit 1; }
