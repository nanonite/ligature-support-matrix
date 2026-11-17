#!/usr/bin/env bash
# Reusable Kani 0.67.0 / Rust 1.95.0 setup probe (Chainlink #177).
#
# Usage: kani-0.67-probe.sh <workdir>
#
# Creates a disposable Cargo crate and checks one synthetic harness. Setup
# probe only; no production claim.
set -euo pipefail

WORK="${1:?usage: kani-0.67-probe.sh <workdir>}"
mkdir -p "$WORK"
CRATE="$WORK/crate"
rm -rf "$CRATE"
mkdir -p "$CRATE/src"

CARGO_HOME_DIR="${CARGO_HOME:-$HOME/.cargo}"
KANI_HOME_DIR="${KANI_HOME:-$HOME/.cache/kani}"

cat > "$CRATE/Cargo.toml" <<'EOF'
[package]
name = "p4_setup_kani_probe"
version = "0.1.0"
edition = "2021"

[lints.rust]
unexpected_cfgs = { level = "warn", check-cfg = ['cfg(kani)'] }
EOF

cat > "$CRATE/src/lib.rs" <<'EOF'
//! P4 setup probe: one synthetic Kani harness. Not a production port claim.
pub fn increment(x: u32) -> u32 {
    x + 1
}

#[cfg(kani)]
#[kani::proof]
fn increment_matches_postcondition_for_all_nonmax_inputs() {
    let x: u32 = kani::any();
    kani::assume(x < u32::MAX);
    assert!(increment(x) == x + 1);
}
EOF

export CARGO_HOME="$CARGO_HOME_DIR"
export RUSTUP_HOME="${RUSTUP_HOME:-$HOME/.rustup}"
export CARGO_NET_OFFLINE=true
export KANI_HOME="$KANI_HOME_DIR"

(
  cd "$CRATE"
  CARGO_TARGET_DIR="$WORK/target" \
    PATH="$CARGO_HOME_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    "$CARGO_HOME_DIR/bin/cargo" +1.95.0 kani \
      --harness increment_matches_postcondition_for_all_nonmax_inputs --exact \
      --target-dir "$WORK/target"
) > "$WORK/kani.log" 2>&1

if ! grep -q 'VERIFICATION:- SUCCESSFUL' "$WORK/kani.log"; then
  echo "FAIL: Kani did not report a successful verification" >&2
  tail -40 "$WORK/kani.log" >&2
  exit 1
fi
if ! grep -q '0 of 3 failed' "$WORK/kani.log"; then
  echo "FAIL: Kani checks did not report 0 failures" >&2
  tail -40 "$WORK/kani.log" >&2
  exit 1
fi
if ! grep -q '1 successfully verified harnesses' "$WORK/kani.log"; then
  echo "FAIL: Kani did not verify exactly one harness" >&2
  tail -40 "$WORK/kani.log" >&2
  exit 1
fi

KANI_VERSION=$("$CARGO_HOME_DIR/bin/cargo" kani --version 2>&1 | head -1)
RUST_VERSION=$("$CARGO_HOME_DIR/bin/rustup" run 1.95.0 rustc --version)

cat > "$WORK/probe-result.json" <<EOF
{
  "probe": "kani-0.67.0",
  "workdir": "$WORK",
  "kani": "$KANI_VERSION",
  "rust": "$RUST_VERSION",
  "result": "successful",
  "production_claim": false
}
EOF

echo "PASS kani-0.67-probe"
echo "  $KANI_VERSION"
echo "  $RUST_VERSION"
echo "  summary: $(grep -m1 '0 of 3 failed' "$WORK/kani.log" | tr -s ' ')"
echo "  evidence: $WORK/probe-result.json"
