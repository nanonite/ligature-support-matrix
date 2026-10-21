#!/usr/bin/env bash
# Prove, on an rsync scratch copy, that approving the staged Stage 0-3 drafts in
# the documented order yields a clean validate / validate-interaction / check.
#
# The --reviewer name below is deliberately not a human's. This is a throwaway
# scratch tree; nothing here is an approval of anything in the live pilot root,
# and the reviewer string is written into ci/results/review_log.jsonl of a
# directory under /tmp that is deleted afterwards.
set -u
ROOT=${1:?scratch root}
TRANSCRIPT=${2:?transcript path}
REVIEWER="scratch-probe-not-a-human-approval"
PYZ="python3 tools/ligature/ligature.pyz"

: > "$TRANSCRIPT"
say() { printf '%s\n' "$*" | tee -a "$TRANSCRIPT"; }
run() { say "\$ $*"; "$@" 2>&1 | tee -a "$TRANSCRIPT" | sed 's/^/    /'; return "${PIPESTATUS[0]}"; }
rc_of() { printf '%s\n' "${PIPESTATUS[0]}"; }

say "=============================================================="
say "Stage 0-3 approval proof -- chainlink #28, pilot swisstable-verus"
say "root: $ROOT   reviewer: $REVIEWER (scratch only, not a human approval)"
say "=============================================================="
say ""
say "--- baseline before any approve ---"
run $PYZ status | tail -4
run $PYZ check --json > /dev/null; say "    check exit=$?"

say ""
say "--- STEP 0  promote every Stage 0 evidence draft (mechanical, no --reviewer) ---"
n=0; f=0
for d in $(ls "$ROOT"/evidence/*.json.draft 2>/dev/null); do
  t="${d%.draft}"
  out=$($PYZ promote-evidence "$t" 2>&1); r=$?
  n=$((n+1))
  if [ $r -ne 0 ]; then f=$((f+1)); say "  [exit $r] $t"; printf '%s\n' "$out" | sed 's/^/      /'; fi
done
say "  promoted $n evidence record(s), $f failure(s)"

# `approve` is given the TARGET path, not the `.draft`; the target is derived from
# the staged draft's own filename so the list can never drift from what is on disk.
approve_all() { # approve_all <label> <dir...>
  local label="$1"; shift
  say ""
  say "--- $label ---"
  local n=0 f=0 d t
  for d in $(ls "$@"/*.json.draft 2>/dev/null); do
    t="${d%.draft}"
    out=$($PYZ approve --reviewer "$REVIEWER" "$t" 2>&1); r=$?
    n=$((n+1))
    if [ $r -ne 0 ]; then f=$((f+1)); say "  [exit $r] $t"; printf '%s\n' "$out" | sed 's/^/      /'; fi
  done
  say "  approved $n target(s), $f failure(s)"
}

C="$ROOT/rust/swisstable-verus-core/specs"

# Order 1: boundaries -> interactions -> bridges -> conflict resolutions.
approve_all "STEP 1  approve every boundary contract" "$C/_boundaries"
approve_all "STEP 2  approve every interaction" "$C/_interactions"
approve_all "STEP 3  approve every bridge specification" "$C/_bridges"
approve_all "STEP 4  approve the evidence conflict resolution" "$ROOT/specs/_conflicts"

say ""
say "--- STEP 5  concept specs: approve has no branch for them (expected failure) ---"
for d in $(ls "$C"/*.json.draft 2>/dev/null); do
  t="${d%.draft}"
  out=$($PYZ approve --reviewer "$REVIEWER" "$t" 2>&1); r=$?
  say "  [exit $r] $t"
  printf '%s\n' "$out" | sed 's/^/      /'
done

say ""
say "--- STEP 6  witness specs: approve reaches G2 and needs a promoted concept spec ---"
for d in $(ls "$C"/_witnesses/*.json.draft 2>/dev/null); do
  t="${d%.draft}"
  out=$($PYZ approve --reviewer "$REVIEWER" "$t" 2>&1); r=$?
  say "  [exit $r] $t"
  printf '%s\n' "$out" | sed 's/^/      /'
done

say ""
say "--- STEP 7  validators ---"
for v in validate validate-interaction validate-bridge validate-evidence validate-exemption validate-protocol-debt validate-witness validate-conflict-resolution; do
  out=$($PYZ $v 2>&1); r=$?
  say "  $v -> exit $r"
  # The full validator output goes into the transcript too, not just the console:
  # check-runbook.py derives the README's expected finding counts from these lines,
  # so a validator that starts reporting a different number cannot leave the README
  # stale.
  printf '%s\n' "$out" | sed 's/^/      /' | tee -a "$TRANSCRIPT" > /dev/null
  printf '%s\n' "$out" | sed 's/^/      /'
done

say ""
say "--- STEP 8  check --json ---"
out=$($PYZ check --json 2>&1); r=$?
printf '%s\n' "$out" | tee -a "$TRANSCRIPT" >/dev/null
python3 -c "
import json,sys
d=json.loads(sys.stdin.read())
print('  exit', $r)
print('  findings:', d['findings'])
print('  conditions:', d['result']['conditions'])
print('  exit_code:', d['result']['exit_code'])
for g in d['gates']: print(f\"  gate {g['gate_id']}: {g['outcome']} -- {g['reason']}\")
print('  next_action:', d['next_action']['action_id'])
" <<<"$out"
say ""
say "--- STEP 9  status / write-set ---"
$PYZ status 2>&1 | tee -a "$TRANSCRIPT" | sed 's/^/    /'
$PYZ write-set-check --json 2>&1 | tee -a "$TRANSCRIPT" | sed 's/^/    /'
say ""
say "=============================================================="