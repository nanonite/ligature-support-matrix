#!/usr/bin/env bash
# Reusable Creusot 0.12.0-dev setup probe (Chainlink #177).
#
# Usage: creusot-0.12-probe.sh <workdir>
#
# Creates a disposable Cargo crate under <workdir>, proves one synthetic
# obligation with the operator-selected Creusot/creusot-std 0.12.0-dev pair and
# rustc nightly-2026-04-21, then reports where companion artifacts landed.
#
# This is a setup probe, not a production port or proof claim.
set -euo pipefail

WORK="${1:?usage: creusot-0.12-probe.sh <workdir>}"
mkdir -p "$WORK" "$WORK/tmp" "$WORK/runtime" "$WORK/config"

CREUSOT_WRAPPER="${P4_CREUSOT_WRAPPER:-/nix/store/9y9g4kpsppxn6zqmyfkvfcc2234qkdwv-creusot-wrapped}"
CREUSOT_STD_SRC="${P4_CREUSOT_STD_SRC:-/nix/store/22j5g9088m140fgx2l6vbskkmg5ra5pp-creusot-source/creusot-std}"
RUSTUP_HOME_DIR="${RUSTUP_HOME:-$HOME/.rustup}"
CARGO_HOME_DIR="${CARGO_HOME:-$HOME/.cargo}"

if [[ ! -x "$CREUSOT_WRAPPER/bin/cargo-creusot" ]]; then
  echo "FAIL: Creusot 0.12 wrapper not found at $CREUSOT_WRAPPER" >&2
  exit 1
fi
if [[ ! -d "$CREUSOT_STD_SRC" ]]; then
  echo "FAIL: creusot-std 0.12 source not found at $CREUSOT_STD_SRC" >&2
  exit 1
fi
if ! "$CARGO_HOME_DIR/bin/rustup" run nightly-2026-04-21 rustc --version >/dev/null 2>&1; then
  echo "FAIL: rustc nightly-2026-04-21 is not installed via rustup" >&2
  exit 1
fi

CRATE="$WORK/crate"
rm -rf "$CRATE"
mkdir -p "$CRATE/src" "$CRATE/.cargo"

cat > "$CRATE/Cargo.toml" <<'EOF'
[package]
name = "p4_setup_creusot_probe"
version = "0.1.0"
edition = "2021"
publish = false

[dependencies]
creusot-std = "0.12.0-dev"

[lints.rust]
unexpected_cfgs = { level = "warn", check-cfg = ['cfg(creusot)'] }
EOF

cat > "$CRATE/.cargo/config.toml" <<EOF
[patch.crates-io]
creusot-std = { path = "$CREUSOT_STD_SRC" }
EOF

cat > "$CRATE/src/lib.rs" <<'EOF'
//! P4 setup probe: one synthetic Creusot obligation. Not a production port claim.
use creusot_std::prelude::*;

#[requires(x@ < u32::MAX@)]
#[ensures(result@ == x@ + 1)]
pub fn increment(x: u32) -> u32 {
    x + 1
}
EOF

cp "$CREUSOT_WRAPPER/why3find.json" "$CRATE/why3find.json"

export CARGO_HOME="$CARGO_HOME_DIR"
export RUSTUP_HOME="$RUSTUP_HOME_DIR"
export CARGO_NET_OFFLINE=true
export XDG_CONFIG_HOME="$WORK/config"
export TMPDIR="$WORK/tmp"
export XDG_RUNTIME_DIR="$WORK/runtime"
unset CREUSOT_RUSTC CREUSOT_DATA_HOME || true

run_creusot() {
  local target="$1"
  shift
  (
    cd "$CRATE"
    CARGO_TARGET_DIR="$target" \
      PATH="$CARGO_HOME_DIR/bin:$CREUSOT_WRAPPER/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
      "$CARGO_HOME_DIR/bin/rustup" run nightly-2026-04-21 \
      "$CREUSOT_WRAPPER/bin/cargo-creusot" creusot "$@"
  )
}

VERSION_LOG="$WORK/creusot-version.txt"
(
  cd "$CRATE"
  CARGO_TARGET_DIR="$WORK/target-version" \
    PATH="$CARGO_HOME_DIR/bin:$CREUSOT_WRAPPER/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    "$CARGO_HOME_DIR/bin/rustup" run nightly-2026-04-21 \
    "$CREUSOT_WRAPPER/bin/cargo-creusot" creusot version
) > "$VERSION_LOG" 2>&1

if ! grep -q 'cargo-creusot 0.12.0-dev' "$VERSION_LOG"; then
  echo "FAIL: wrapper did not report cargo-creusot 0.12.0-dev" >&2
  cat "$VERSION_LOG" >&2
  exit 1
fi
if ! grep -q 'nightly-2026-04-21' "$VERSION_LOG"; then
  echo "FAIL: wrapper did not report nightly-2026-04-21" >&2
  cat "$VERSION_LOG" >&2
  exit 1
fi

# 1. Local compile: writes the .coma under the crate's verif/ tree.
run_creusot "$WORK/target-local" --only coma > "$WORK/compile-local.log" 2>&1
LOCAL_COMA="$CRATE/verif/p4_setup_creusot_probe_rlib/increment.coma"
if [[ ! -f "$LOCAL_COMA" ]]; then
  echo "FAIL: local compile did not create $LOCAL_COMA" >&2
  exit 1
fi

# 2. External compile with a fresh target: writes the .coma outside the crate.
run_creusot "$WORK/target-external" --only coma --output-dir "$WORK/external-out" \
  > "$WORK/compile-external.log" 2>&1
EXTERNAL_COMA="$WORK/external-out/verif/p4_setup_creusot_probe_rlib/increment.coma"
if [[ ! -f "$EXTERNAL_COMA" ]]; then
  echo "FAIL: external compile did not create $EXTERNAL_COMA" >&2
  exit 1
fi

# 3. Prove with an explicit crate-relative pattern and an external output root.
run_creusot "$WORK/target-local" --only prove --output-dir "$WORK/external-out" \
  "verif/p4_setup_creusot_probe_rlib/increment.coma" > "$WORK/prove.log" 2>&1
if ! grep -q 'Proved' "$WORK/prove.log"; then
  echo "FAIL: Creusot did not report Proved" >&2
  cat "$WORK/prove.log" >&2
  exit 1
fi

PROOF_JSON="$CRATE/verif/p4_setup_creusot_probe_rlib/increment/proof.json"
if [[ -f "$PROOF_JSON" ]]; then
  PROOF_JSON_PLACEMENT="crate-local:$PROOF_JSON"
else
  PROOF_JSON_PLACEMENT="missing"
  echo "FAIL: proof.json was not found in the crate" >&2
  exit 1
fi
if compgen -G "$CRATE/.why3find/*" >/dev/null; then
  WHY3FIND_CACHE="crate-local:$CRATE/.why3find"
else
  WHY3FIND_CACHE="missing"
fi
if [[ -f "$WORK/external-out/verif/p4_setup_creusot_probe_rlib/increment/proof.json" ]]; then
  EXTERNAL_PROOF_JSON="present"
else
  EXTERNAL_PROOF_JSON="absent"
fi
EXTERNAL_COMA_COUNT=$(find "$WORK/external-out" -name '*.coma' | wc -l | tr -d ' ')

# 4. Why3 local-solver configuration under a private XDG/TMP root.
(
  cd "$CRATE"
  PATH="$CARGO_HOME_DIR/bin:$CREUSOT_WRAPPER/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    "$CREUSOT_WRAPPER/bin/why3" config detect
) > "$WORK/why3-config-detect.log" 2>&1 || {
  echo "FAIL: why3 config detect failed" >&2
  cat "$WORK/why3-config-detect.log" >&2
  exit 1
}
PROVER_COUNT=$(grep -oE '[0-9]+ prover\(s\) added' "$WORK/why3-config-detect.log" | grep -oE '^[0-9]+' || true)
if [[ -z "$PROVER_COUNT" || "$PROVER_COUNT" -lt 1 ]]; then
  echo "FAIL: no Why3 provers were detected" >&2
  cat "$WORK/why3-config-detect.log" >&2
  exit 1
fi

cat > "$WORK/probe-result.json" <<EOF
{
  "probe": "creusot-0.12.0-dev",
  "workdir": "$WORK",
  "wrapper": "$CREUSOT_WRAPPER",
  "creusot_std_source": "$CREUSOT_STD_SRC",
  "rust": "nightly-2026-04-21",
  "result": "proved",
  "local_coma": "$LOCAL_COMA",
  "external_coma": "$EXTERNAL_COMA",
  "external_coma_count": $EXTERNAL_COMA_COUNT,
  "proof_json_placement": "$PROOF_JSON_PLACEMENT",
  "external_proof_json": "$EXTERNAL_PROOF_JSON",
  "why3find_cache_placement": "$WHY3FIND_CACHE",
  "why3_provers_detected": $PROVER_COUNT,
  "why3_local_socket_access": "proof completed under private TMPDIR/XDG_RUNTIME_DIR",
  "production_claim": false
}
EOF

echo "PASS creusot-0.12-probe"
echo "  version: $(grep -m1 'cargo-creusot' "$VERSION_LOG")"
echo "  proof: $(grep -m1 'Proved' "$WORK/prove.log")"
echo "  external coma: $EXTERNAL_COMA"
echo "  proof.json: $PROOF_JSON_PLACEMENT"
echo "  external proof.json: $EXTERNAL_PROOF_JSON"
echo "  why3find cache: $WHY3FIND_CACHE"
echo "  why3 provers: $PROVER_COUNT"
echo "  evidence: $WORK/probe-result.json"
