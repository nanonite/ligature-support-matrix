#!/usr/bin/env bash
# Reusable Verus 0.2026.05.24.ecee80a / Rust 1.95.0 setup probe (Chainlink #177).
#
# Usage: verus-1.95-probe.sh <workdir>
#
# Creates a disposable Cargo crate, verifies one synthetic obligation and
# records the proof result. Setup probe only; no production claim.
set -euo pipefail

WORK="${1:?usage: verus-1.95-probe.sh <workdir>}"
mkdir -p "$WORK"
CRATE="$WORK/crate"
rm -rf "$CRATE"
mkdir -p "$CRATE/src" "$CRATE/out"

CARGO_HOME_DIR="${CARGO_HOME:-$HOME/.cargo}"
VERUS_BIN_DIR="${P4_VERUS_BIN_DIR:-/nix/store/57l94534x07sysi7gjf4zkkpai6cw6vc-verus-tools/bin}"
if [[ ! -x "$CARGO_HOME_DIR/bin/cargo" ]]; then
  echo "FAIL: cargo not found at $CARGO_HOME_DIR/bin/cargo" >&2
  exit 1
fi
if [[ ! -x "$VERUS_BIN_DIR/verus" ]]; then
  echo "FAIL: Verus not found at $VERUS_BIN_DIR/verus" >&2
  exit 1
fi

cat > "$CRATE/Cargo.toml" <<'EOF'
[package]
name = "p4_setup_verus_probe"
version = "0.1.0"
edition = "2021"

[dependencies]
vstd = "=0.0.0-2026-05-24-0157"

[package.metadata.verus]
verify = true

[lints.rust]
unexpected_cfgs = { level = "warn", check-cfg = ['cfg(verus_only)'] }
EOF

cat > "$CRATE/rust-toolchain.toml" <<'EOF'
[toolchain]
channel = "1.95.0"
profile = "minimal"
EOF

cat > "$CRATE/src/lib.rs" <<'EOF'
//! P4 setup probe: one synthetic Verus obligation. Not a production port claim.
use vstd::prelude::*;

verus! {
    pub fn increment(x: u32) -> (result: u32)
        requires x < u32::MAX,
        ensures result == x + 1,
    {
        x + 1
    }
}
EOF

export CARGO_HOME="$CARGO_HOME_DIR"
export RUSTUP_HOME="${RUSTUP_HOME:-$HOME/.rustup}"
export CARGO_NET_OFFLINE=true

(
  cd "$CRATE"
  CARGO_TARGET_DIR="$WORK/target" \
    PATH="$CARGO_HOME_DIR/bin:$VERUS_BIN_DIR:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    "$CARGO_HOME_DIR/bin/cargo" +1.95.0 verus build \
      --manifest-path "$CRATE/Cargo.toml" --offline --target-dir "$WORK/target" -- \
      --output-json
) > "$WORK/verus-build.log" 2>&1

if ! grep -q '"success": true' "$WORK/verus-build.log"; then
  echo "FAIL: Verus did not report success" >&2
  tail -40 "$WORK/verus-build.log" >&2
  exit 1
fi
if ! grep -q '"errors": 0' "$WORK/verus-build.log"; then
  echo "FAIL: Verus reported verification errors" >&2
  tail -40 "$WORK/verus-build.log" >&2
  exit 1
fi

VERUS_VERSION=$("$VERUS_BIN_DIR/verus" --version 2>&1 | awk '/Version:/ {print $2; exit}')
RUST_VERSION=$("$CARGO_HOME_DIR/bin/rustup" run 1.95.0 rustc --version)

cat > "$WORK/probe-result.json" <<EOF
{
  "probe": "verus-1.95.0",
  "workdir": "$WORK",
  "verus_bin": "$VERUS_BIN_DIR/verus",
  "verus_version": "$VERUS_VERSION",
  "rust": "$RUST_VERSION",
  "result": "verified",
  "production_claim": false
}
EOF

echo "PASS verus-1.95-probe"
echo "  verus: $VERUS_VERSION"
echo "  $RUST_VERSION"
echo "  proof: $(grep '"verified"' "$WORK/verus-build.log" | tail -1 | tr -d ' ')"
echo "  evidence: $WORK/probe-result.json"
