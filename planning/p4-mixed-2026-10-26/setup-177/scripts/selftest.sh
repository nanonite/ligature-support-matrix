#!/usr/bin/env bash
# Self-test for the reusable P4 per-root smoke check (Chainlink #177).
#
# Builds a synthetic root under /tmp/opencode that satisfies the setup
# manifest, asserts the checker passes, then mutates a protected expectation
# and asserts the checker fails. Nothing is written to a real project root.
#
# Usage: selftest.sh [--keep]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK="$HERE/smoke_check.py"
BASE="${TMPDIR:-/tmp}/opencode/p177-selftest"
ROOT="$BASE/icl-creusot-verus"
KEEP=0
[[ "${1:-}" == "--keep" ]] && KEEP=1

rm -rf "$BASE"
mkdir -p "$ROOT/tools/ligature" "$ROOT/upstream" "$ROOT/oracle" \
  "$ROOT/findings" "$ROOT/analysis/stage/result-creusot" \
  "$ROOT/analysis/stage/results-creusot" "$ROOT/analysis/stage/results-verus"

cd "$ROOT"
git init -q
git config user.email selftest@example.invalid
git config user.name selftest

cat > project-descriptor.json <<'JSON'
{
  "schema_version": "1.0",
  "project": {"name": "icl-creusot-verus", "crate_naming_convention": "^icl-creusot-verus-[a-z]+"},
  "mode": "port",
  "closure_kind": "deductive",
  "crates": [
    {"crate_dir": "rust/icl-creusot-verus-creusot", "contracts_crate": "contracts"},
    {"crate_dir": "rust/icl-creusot-verus-verus", "contracts_crate": "specs"}
  ],
  "verifier_policy": {"default": "creusot"},
  "write_set": {
    "allowed_roots": ["rust/*/src/", "oracle/**", "analysis/**", "findings/limitations.jsonl", "PORT-GAPS.md"],
    "protected_roots": ["project-descriptor.json", "Cargo.toml", "rust/*/Cargo.toml", "rust/*/Cargo.lock", "tools/**", "upstream/**"]
  }
}
JSON

printf '#!/usr/bin/env bash\necho "ligature 1.4.3 selftest"\n' > tools/ligature/ligature.pyz
chmod +x tools/ligature/ligature.pyz
( cd tools/ligature && sha256sum ligature.pyz > SHA256SUMS )

cat > upstream/upstream-pin.json <<'JSON'
{"repository": "https://github.com/boostorg/icl", "tag": "boost-1.88.0", "commit": "2741c3a1b7b79f7326360c26c3e1588b385c9e53"}
JSON

for item in "creusot:nightly-2026-04-21" "verus:1.95.0"; do
  verifier="${item%%:*}"
  channel="${item##*:}"
  crate="rust/icl-creusot-verus-$verifier"
  mkdir -p "$crate/src" "$crate/.cargo"
  printf '[package]\nname = "icl-creusot-verus-%s"\nversion = "0.1.0"\nedition = "2021"\n' "$verifier" > "$crate/Cargo.toml"
  printf '# synthetic lock\n' > "$crate/Cargo.lock"
  printf '[toolchain]\nchannel = "%s"\n' "$channel" > "$crate/rust-toolchain.toml"
  printf '[patch.crates-io]\n' > "$crate/.cargo/config.toml"
  printf '// synthetic\n' > "$crate/src/lib.rs"
done

printf '' > findings/limitations.jsonl
printf '# PORT-GAPS (synthetic self-test)\n' > PORT-GAPS.md

echo "=== smoke check: seeded synthetic root (expect exit 0) ==="
set +e
python3 "$CHECK" --root "$ROOT"
pass_exit=$?
set -e
[[ $pass_exit -eq 0 ]] || { echo "SELFTEST FAILED: seeded root returned $pass_exit"; exit 1; }

echo
echo "=== mutation: repository-local target/ tree and wrong toolchain (expect exit 1) ==="
mkdir -p rust/icl-creusot-verus-verus/target
printf '[toolchain]\nchannel = "stable"\n' > rust/icl-creusot-verus-verus/rust-toolchain.toml
set +e
python3 "$CHECK" --root "$ROOT"
fail_exit=$?
set -e
[[ $fail_exit -ne 0 ]] || { echo "SELFTEST FAILED: mutated root unexpectedly passed"; exit 1; }
echo "SELFTEST OK: seeded=$pass_exit mutated=$fail_exit"

if [[ $KEEP -eq 0 ]]; then
  rm -rf "$BASE"
else
  echo "kept $BASE"
fi
