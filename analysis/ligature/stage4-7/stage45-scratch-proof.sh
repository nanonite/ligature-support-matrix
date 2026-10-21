#!/usr/bin/env bash
# Stage 4 / 4.5 proof on an rsync scratch copy of this pilot root.
#
# WHY THIS EXISTS.  The operator approves the whole 45-artifact set in ONE batch at
# the end of P2 (chainlink #29 operator direction), so `approve`, `record-ruling` and
# `accept-promotion` must NOT be run on the live root under any name.  This script
# runs them on a throwaway copy instead, so the README operator runbook carries a
# *measured* command list and a *measured* expected output rather than a guess.
#
# Nothing here touches the live root: SCRATCH is outside the workspace, and the
# reviewer name is obviously a scratch name (`scratch-approval-proof`), so a ruling
# logged here can never be confused with the operator's real ruling.
#
# Usage: bash analysis/ligature/stage4-7/stage45-scratch-proof.sh
set -u

REVIEWER="scratch-approval-proof"
SCRATCH="${SCRATCH:-/tmp/opencode/swisstable-stage45-scratch}"
HERE="$(cd "$(dirname "$0")/../../.." && pwd)"   # -> swisstable-verus/ (stage4-7 -> ligature -> analysis -> root)

echo "### rsync scratch copy: $SCRATCH"
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"
rsync -a --delete-excluded \
  --exclude '.git' \
  "$HERE/" "$SCRATCH/"
echo "rsync exit=$?"
echo

cd "$SCRATCH" || exit 1
L="python3 tools/ligature/ligature.pyz"

fails=0
step() { printf '\n--- %s\n' "$*"; }
run() { # run <label> -- <cmd...>
  local label="$1"; shift
  echo "\$ $*"
  local out; out="$("$@" 2>&1)"; local rc=$?
  printf '%s\n' "$out" | tail -25
  echo "EXIT=$rc"
  [ "$rc" -ne 0 ] && fails=$((fails+1))
  return 0
}

step "baseline on the scratch copy: nothing is approved yet"
run "validate-bridge"            python3 tools/ligature/ligature.pyz validate-bridge
run "check"                      python3 tools/ligature/ligature.pyz check

step "STEP 1 -- approve the 14 boundary contracts (README runbook step 1)"
approve_dir() { # approve_dir <dir> -- approve every staged <name>.json.draft as <name>.json
  local dir="$1" f target
  for f in "$dir"/*.json.draft; do
    [ -e "$f" ] || { echo "  (no staged draft in $dir)"; continue; }
    target="${f%.draft}"
    echo "\$ $L approve --reviewer \$R $target"
    local out; out="$($L approve --reviewer "$REVIEWER" "$target" 2>&1)"; local rc=$?
    printf '%s\n' "$out" | tail -6; echo "EXIT=$rc"
    [ "$rc" -ne 0 ] && fails=$((fails+1))
  done
}
approve_dir rust/swisstable-verus-core/specs/_boundaries
run "validate (step 1)"          python3 tools/ligature/ligature.pyz validate

step "STEP 2 -- approve the 15 interactions (README runbook step 2)"
approve_dir rust/swisstable-verus-core/specs/_interactions
run "validate-interaction (step 2)" python3 tools/ligature/ligature.pyz validate-interaction

step "STEP 3 -- approve the 6 bridges (README runbook step 3)"
approve_dir rust/swisstable-verus-core/specs/_bridges
run "validate-bridge (step 3)"   python3 tools/ligature/ligature.pyz validate-bridge

step "STEP 4 -- approve the conflict resolution (README runbook step 4)"
run "approve EC-1"               python3 tools/ligature/ligature.pyz approve --reviewer "$REVIEWER" specs/_conflicts/EC-1.json
run "validate-conflict-resolution" python3 tools/ligature/ligature.pyz validate-conflict-resolution

step "STEP 5 -- concept specs and witness specs: confirm they really cannot be approved (#111)"
run "approve concept raw_table"  python3 tools/ligature/ligature.pyz approve --reviewer "$REVIEWER" rust/swisstable-verus-core/specs/raw_table.json
run "approve witness"            python3 tools/ligature/ligature.pyz approve --reviewer "$REVIEWER" rust/swisstable-verus-core/specs/_witnesses/group_probe.match_full.json

step "the accepted artifact set -- what accept-promotion will be asked to accept"
ARTIFACTS=()
for f in \
  docs/reliance-policy.md \
  evidence/*.json \
  specs/_conflicts/EC-1.json \
  rust/swisstable-verus-core/specs/_boundaries/*.json \
  rust/swisstable-verus-core/specs/_interactions/*.json \
  rust/swisstable-verus-core/specs/_bridges/*.json
do
  ARTIFACTS+=("$f")
done
echo "count=${#ARTIFACTS[@]}"
printf '%s\n' "${ARTIFACTS[@]}"
args=(); for f in "${ARTIFACTS[@]}"; do args+=(--artifact "$f"); done

step "STAGE 4.5 BLOCKER -- accept-promotion against the policy doc AS IT SHIPS"
run "accept-promotion (unfilled policy template)" \
  python3 tools/ligature/ligature.pyz accept-promotion swisstable-verus-core \
    --reviewer "$REVIEWER" "${args[@]}"

step "STAGE 4.5 -- fill the policy placeholders ON THE SCRATCH COPY ONLY"
echo "On the live root docs/reliance-policy.md is a protected_roots path (WORKER-CONTRACT"
echo "§3) and still carries the template's literal placeholders, so this sed is scratch-only"
echo "and the live file is left byte-identical. Proving the rest of Stage 4.5 needs a real"
echo "marker line; filling it for real is a human authority step."
python3 - <<'PY'
p = 'docs/reliance-policy.md'
t = open(p).read()
subs = [
    ('Schema version this policy targets: `<boundary-contract-schema version>`.',
     'Schema version this policy targets: `1.0`.'),
    ('Owner: `<team or individual accountable for changes>`.',
     'Owner: `scratch-approval-proof` (scratch copy only; the live root is untouched).'),
    ('Policy version: `<policy-name>@<major>.<minor>`',
     'Policy version: swisstable-verus-reliance-policy@0.0'),
    ("| `0.1` | `<date>` | `<human>` | Initial adoption from the pipeline template |",
     "| `0.0` | `2026-10-02` | `scratch-approval-proof` | As shipped from the pipeline template |"),
]
for old, new in subs:
    if old not in t:
        raise SystemExit(f'NOT FOUND, refusing to guess: {old!r}')
    t = t.replace(old, new, 1)
open(p, 'w').write(t)
print('filled 4 placeholder lines')
PY
grep -n 'Policy version:\|Owner:\|Schema version this policy' docs/reliance-policy.md
run "accept-policy" \
  python3 tools/ligature/ligature.pyz accept-policy --reviewer "$REVIEWER"

step "STAGE 4.5 -- the human-ruling gate, with ZERO rulings recorded (fail-closed)"
run "accept-promotion (zero rulings)" \
  python3 tools/ligature/ligature.pyz accept-promotion swisstable-verus-core \
    --reviewer "$REVIEWER" "${args[@]}"

step "STAGE 4.5 -- record ONE ratified ruling covering the whole accepted set"
rargs=(); for f in "${ARTIFACTS[@]}"; do rargs+=(--artifact "$f"); done
run "record-ruling" \
  python3 tools/ligature/ligature.pyz record-ruling --reviewer "$REVIEWER" \
    --verdict ratified "${rargs[@]}"
echo "--- ci/results/human_rulings.jsonl (hashes elided)"
python3 - <<'PY'
import json
for line in open('ci/results/human_rulings.jsonl'):
    d = json.loads(line)
    print({k: (v if k != 'artifacts' else f"<{len(v)} artifacts>") for k, v in d.items()})
PY

step "STAGE 4.5 -- accept-promotion (the real call)"
run "accept-promotion" \
  python3 tools/ligature/ligature.pyz accept-promotion swisstable-verus-core \
    --reviewer "$REVIEWER" "${args[@]}"

step "STAGE 4.5 -- validate-promotion over the receipt ligature just wrote"
RECEIPT=$(ls specs/_promotions/*.json 2>/dev/null | head -1)
echo "receipt=$RECEIPT"
run "validate-promotion" python3 tools/ligature/ligature.pyz validate-promotion "$RECEIPT"
echo "--- receipt contents (artifact_manifest paths elided)"
python3 - "$RECEIPT" <<'PY' 2>/dev/null || cat "$RECEIPT"
import json, sys
d = json.load(open(sys.argv[1]))
for k, v in d.items():
    if k == 'artifact_manifest':
        print(f'{k}: [ {len(v)} entries ]')
        print('   first:', json.dumps(v[0]))
    else:
        print(f'{k}: {json.dumps(v)}')
PY
echo "--- sha256 of the receipt itself"
sha256sum "$RECEIPT" 2>/dev/null

step "post-approval gates on the scratch copy"
run "check-bridges (absolute --workspace: the #96 crash shape)" python3 tools/ligature/ligature.pyz --workspace "$SCRATCH" check-bridges
run "gate-g9 (absolute --workspace)"                            python3 tools/ligature/ligature.pyz --workspace "$SCRATCH" gate-g9
run "check-bridges (RELATIVE --workspace '.', the 1.1.1 crash shape)" python3 tools/ligature/ligature.pyz check-bridges
run "gate-g9 (RELATIVE --workspace '.')"                            python3 tools/ligature/ligature.pyz gate-g9
run "check"                      python3 tools/ligature/ligature.pyz check
run "status"                     python3 tools/ligature/ligature.pyz status
run "write-set-check"            python3 tools/ligature/ligature.pyz write-set-check
run "doctor"                     python3 tools/ligature/ligature.pyz doctor
run "gate-g14"                   python3 tools/ligature/ligature.pyz gate-g14
run "select-pilot-cluster"       python3 tools/ligature/ligature.pyz select-pilot-cluster
run "validate-promotion (re-run, idempotence)" \
  python3 tools/ligature/ligature.pyz validate-promotion specs/_promotions/swisstable-verus-core.json

printf '\n### non-zero exits recorded: %s\n' "$fails"
echo "### scratch copy left at $SCRATCH for inspection"
