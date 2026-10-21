#!/usr/bin/env bash
# Replay the rdb investigation of boundary-aead-output-length-encrypt-0003 in any checkout.
#
# Run inside the crypto-mixed flake shell:
#   nix develop path:/home/goya/storage/full-ligature-port-workspace#crypto-mixed -c \
#     oracle/divergences/boundary-aead-output-length-encrypt-0003/replay.sh
#
# The breakpoint address depends on the build path, so it is resolved with nm
# for this build rather than taken from rdb-commands.txt (which records the
# original session's 0x2111f0). rdb exits 0 even when its commands fail, so
# the transcript itself is checked.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
cd "$here/../../rust-check"
RUSTFLAGS="-C link-arg=-no-pie" CARGO_TARGET_DIR=target/repro cargo build --bin oracle_repro
bin=target/repro/debug/oracle_repro

symbol="crypto_mixed_core::aead::ChaCha20Poly1305::encryption_output_length"
hex="$(nm -C "$bin" | awk -v s="$symbol" '$2 == "T" && $3 == s { print $1 }')"
if [ -z "$hex" ]; then
  echo "symbol $symbol not found in $bin" >&2
  exit 1
fi
addr="$(printf '0x%x' "$((16#$hex))")"

transcript="$(printf 'break %s\ncontinue\nvariable list\nregister rdi\nregister rsi\nregister rdx\nnext\nvariable list\nnext\nnext\nbacktrace\ncontinue\nquit\n' "$addr" | rdb "$bin" 2>&1)"
printf '%s\n' "$transcript"

for expected in "breakpoint set at $addr" "rdx = 0x3fffffffc1" "aead.rs:21" "aead.rs:22" "result=Err(MessageTooLong)"; do
  if ! grep -qF "$expected" <<<"$transcript"; then
    echo "replay failed: transcript lacks '$expected'" >&2
    exit 1
  fi
done
echo "replay ok: breakpoint $addr; rdx = 0x3fffffffc1 (2^38-63) > MAX_MESSAGE_BYTES at aead.rs:21; returns Err at aead.rs:22"
