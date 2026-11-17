#!/usr/bin/env bash
# Reusable per-root smoke check for the four P4 mixed-verifier roots (#177).
#
# Usage: p4-root-smoke-check.sh [--probe] [--allow-protected] <root>
#
#   --probe             also run one synthetic obligation per declared verifier
#                       in a disposable /tmp fixture
#   --allow-protected   report but do not fail on present protected paths
#                       (use only after an operator has created them)
#
# Without --probe the check is read-only. Probe runs use a task-specific /tmp
# root and leave this repository untouched. This is a setup check, not a
# production port or proof claim.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PROBE=0
ALLOW_PROTECTED=0
ROOT_ARG=""

for arg in "$@"; do
  case "$arg" in
    --probe) PROBE=1 ;;
    --allow-protected) ALLOW_PROTECTED=1 ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) ROOT_ARG="$arg" ;;
  esac
done

if [[ -z "$ROOT_ARG" ]]; then
  echo "usage: p4-root-smoke-check.sh [--probe] [--allow-protected] <root>" >&2
  exit 2
fi

ROOT="$(cd "$ROOT_ARG" && pwd)"
ROOT_NAME="$(basename "$ROOT")"
KNOWN_ROOTS="icl-creusot-verus tinyxml2-creusot-kani snappy-verus-kani leveldb-three-verifiers"
if [[ " $KNOWN_ROOTS " != *" $ROOT_NAME "* ]]; then
  echo "FAIL: $ROOT_NAME is not one of the four P4 setup roots" >&2
  exit 1
fi

FAILURES=0
pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*"; FAILURES=$((FAILURES + 1)); }

echo "== P4 root smoke check: $ROOT_NAME =="
echo "root: $ROOT"

# 1. Independent Git root on main.
TOPLEVEL="$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null || true)"
if [[ "$TOPLEVEL" == "$ROOT" ]]; then
  pass "independent Git root"
else
  fail "not an independent Git root (toplevel=${TOPLEVEL:-none})"
fi
BRANCH="$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
if [[ "$BRANCH" == "main" ]]; then
  pass "branch is main"
else
  fail "branch is '${BRANCH:-none}', expected main"
fi
COMMITS="$(git -C "$ROOT" rev-list --count HEAD 2>/dev/null || echo 0)"
echo "INFO: commits=$COMMITS (setup roots are uncommitted until the operator's baseline commit)"

# 2. Required setup files.
REQUIRED=(
  README.md
  SOURCE-PIN.json
  PORT-GAPS.md
  .gitignore
  findings/limitations.jsonl
  analysis/setup/SETUP.md
  analysis/setup/root-setup.json
  oracle/README.md
  oracle/oracle-PROTOCOL.md
)
for rel in "${REQUIRED[@]}"; do
  if [[ -f "$ROOT/$rel" ]]; then
    pass "present: $rel"
  else
    fail "missing: $rel"
  fi
done

# 3. Machine-readable setup consistency.
if ! python3 - "$WS" "$ROOT" "$ROOT_NAME" <<'PY'
import json
import sys
from pathlib import Path

ws, root, name = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
errors = []
setup = json.loads((root / "analysis/setup/root-setup.json").read_text())
if setup.get("root") != name:
    errors.append(f"root-setup.json root={setup.get('root')!r}, expected {name!r}")
if setup.get("issue") != 177:
    errors.append("root-setup.json issue is not 177")
if setup.get("ligature", {}).get("initialized") is not False:
    errors.append("root-setup.json must record ligature.initialized=false at setup")
verifiers = setup.get("verifiers", [])
if not verifiers:
    errors.append("root-setup.json has no verifiers")
def repo_key(url):
    return url.rstrip("/").removeprefix("https://github.com/").removeprefix("git@github.com:")

pins = {
    repo_key(p["repository"]): p
    for p in json.loads((ws / "planning/p4-mixed-2026-10-26/upstream-pins.json").read_text())
}
pin = json.loads((root / "SOURCE-PIN.json").read_text())
if pin.get("commit") != pins.get(repo_key(pin.get("repository", "")), {}).get("commit"):
    errors.append("SOURCE-PIN.json commit does not match planning upstream-pins.json")
if pin.get("checkout", {}).get("status") != "absent":
    errors.append("SOURCE-PIN.json must record checkout.status=absent at setup")

allowed_tools = {"ligature", "creusot", "verus", "kani", "nextest", "rdb", "mcp", "oracle"}
severities = {"blocker", "scope-cut", "friction"}
keys = {
    "id", "pilot", "stage", "command", "tool", "chain", "symptom", "repro_cmd",
    "exit_code", "expected", "actual", "workaround", "severity", "revisit_trigger",
    "pyz_sha256", "tool_path", "tool_version",
}
lines = [l for l in (root / "findings/limitations.jsonl").read_text().splitlines() if l.strip()]
seen_ids = set()
for line in lines:
    rec = json.loads(line)
    missing = keys - set(rec)
    if missing:
        errors.append(f"finding {rec.get('id')} missing fields {sorted(missing)}")
    if rec.get("pilot") != name:
        errors.append(f"finding {rec.get('id')} pilot={rec.get('pilot')!r}")
    if rec.get("tool") not in allowed_tools:
        errors.append(f"finding {rec.get('id')} has invalid tool {rec.get('tool')!r}")
    if rec.get("severity") not in severities:
        errors.append(f"finding {rec.get('id')} has invalid severity {rec.get('severity')!r}")
    if rec.get("id") in seen_ids:
        errors.append(f"duplicate finding id {rec.get('id')!r}")
    seen_ids.add(rec.get("id"))

for error in errors:
    print(f"FAIL: {error}")
print(f"PASS: {len(lines)} finding record(s) valid" if not errors else f"INFO: {len(lines)} finding record(s) checked")
sys.exit(1 if errors else 0)
PY
then
  FAILURES=$((FAILURES + 1))
fi

# 4. Oracle protocol copy must match the workspace protocol.
if cmp -s "$ROOT/oracle/oracle-PROTOCOL.md" "$WS/oracle-PROTOCOL.md"; then
  pass "oracle/oracle-PROTOCOL.md matches workspace protocol"
else
  fail "oracle/oracle-PROTOCOL.md differs from workspace protocol"
fi

# 5. Protected paths must be absent at setup time.
PROTECTED_PRESENT="$(python3 - "$ROOT" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
setup = json.loads((root / "analysis/setup/root-setup.json").read_text())
found = []
for entry in setup.get("protected_paths", []):
    rel = entry["path"]
    for p in root.glob(rel):
        found.append(str(p.relative_to(root)))
print("\n".join(sorted(found)))
PY
)"
if [[ -z "$PROTECTED_PRESENT" ]]; then
  pass "no protected paths created"
else
  if [[ "$ALLOW_PROTECTED" -eq 1 ]]; then
    echo "INFO: protected paths present (allowed by flag):"
    echo "$PROTECTED_PRESENT" | sed 's/^/  /'
  else
    fail "protected paths present: $(echo "$PROTECTED_PRESENT" | tr '\n' ' ')"
  fi
fi

# 6. Tool availability for the declared verifiers.
VERIFIERS="$(python3 -c "import json,sys;print(' '.join(json.load(open(sys.argv[1]))['verifiers']))" "$ROOT/analysis/setup/root-setup.json")"
echo "INFO: verifiers=$VERIFIERS"
CARGO_HOME_DIR="${CARGO_HOME:-$HOME/.cargo}"
CREUSOT_WRAPPER="${P4_CREUSOT_WRAPPER:-/nix/store/9y9g4kpsppxn6zqmyfkvfcc2234qkdwv-creusot-wrapped}"
VERUS_BIN_DIR="${P4_VERUS_BIN_DIR:-/nix/store/57l94534x07sysi7gjf4zkkpai6cw6vc-verus-tools/bin}"

if [[ " $VERIFIERS " == *" creusot "* ]]; then
  if [[ -x "$CREUSOT_WRAPPER/bin/cargo-creusot" ]]; then
    pass "Creusot wrapper present: $CREUSOT_WRAPPER"
  else
    fail "Creusot wrapper missing: $CREUSOT_WRAPPER"
  fi
  if "$CARGO_HOME_DIR/bin/rustup" run nightly-2026-04-21 rustc --version >/dev/null 2>&1; then
    pass "rustc nightly-2026-04-21 present"
  else
    fail "rustc nightly-2026-04-21 missing"
  fi
fi
if [[ " $VERIFIERS " == *" verus "* ]]; then
  if [[ -x "$VERUS_BIN_DIR/verus" ]]; then
    pass "Verus present: $("$VERUS_BIN_DIR/verus" --version 2>&1 | awk '/Version:/ {print $2; exit}')"
  else
    fail "Verus missing: $VERUS_BIN_DIR/verus"
  fi
fi
if [[ " $VERIFIERS " == *" kani "* ]]; then
  if "$CARGO_HOME_DIR/bin/cargo" kani --version >/dev/null 2>&1; then
    pass "Kani present: $("$CARGO_HOME_DIR/bin/cargo" kani --version 2>&1 | head -1)"
  else
    fail "cargo kani not available"
  fi
fi

# 7. Optional disposable verifier probes.
if [[ "$PROBE" -eq 1 ]]; then
  WORK="/tmp/p4-smoke-${ROOT_NAME}-$$"
  rm -rf "$WORK"
  mkdir -p "$WORK"
  for tool in $VERIFIERS; do
    case "$tool" in
      creusot) probe="$SCRIPT_DIR/probes/creusot-0.12-probe.sh" ;;
      verus) probe="$SCRIPT_DIR/probes/verus-1.95-probe.sh" ;;
      kani) probe="$SCRIPT_DIR/probes/kani-0.67-probe.sh" ;;
      *) continue ;;
    esac
    if "$probe" "$WORK/$tool" 2>&1 | tee "$WORK/$tool.log"; then
      pass "$tool probe"
    else
      fail "$tool probe (log: $WORK/$tool.log)"
    fi
  done
  echo "INFO: probe workdir: $WORK"
fi

echo "== result: $ROOT_NAME: $FAILURES failure(s) =="
if [[ "$FAILURES" -ne 0 ]]; then
  exit 1
fi
