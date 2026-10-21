#!/usr/bin/env bash
# Determine the real order constraints between approvals, by running deliberately
# wrong orders on throwaway scratch copies and recording what each refuses.
# $1 = experiment id, $2 = order spec, $3 = transcript path
set -u
ROOT=$1; ORDER=$2; TRANSCRIPT=$3
REVIEWER="scratch-probe-not-a-human-approval"
PYZ="python3 tools/ligature/ligature.pyz"
C="$ROOT/rust/swisstable-verus-core/specs"

: > "$TRANSCRIPT"
say() { printf '%s\n' "$*" | tee -a "$TRANSCRIPT"; }

for step in $ORDER; do
  case $step in
    no-evidence)
      say "  (no evidence promoted)" ;;
    evidence)
      n=0; f=0
      for d in $(ls "$ROOT"/evidence/*.json.draft 2>/dev/null); do
        out=$($PYZ promote-evidence "${d%.draft}" 2>&1); r=$?
        n=$((n+1)); [ $r -ne 0 ] && { f=$((f+1)); say "  [exit $r] ${d%.draft}"; printf '%s\n' "$out" | sed 's/^/      /'; }
      done
      say "  evidence: promoted $n, failed $f" ;;
    boundaries|interactions|bridges|conflicts)
      case $step in
        boundaries) dir="$C/_boundaries" ;;
        interactions) dir="$C/_interactions" ;;
        bridges) dir="$C/_bridges" ;;
        conflicts) dir="$ROOT/specs/_conflicts" ;;
      esac
      n=0; f=0
      for d in $(ls "$dir"/*.json.draft 2>/dev/null); do
        out=$($PYZ approve --reviewer "$REVIEWER" "${d%.draft}" 2>&1); r=$?
        n=$((n+1)); [ $r -ne 0 ] && { f=$((f+1)); say "  [exit $r] $(basename "${d%.draft}")"; printf '%s\n' "$out" | sed 's/^/      /'; }
      done
      say "  $step: attempted $n, failed $f" ;;
    validate-interaction)
      out=$($PYZ validate-interaction 2>&1); r=$?
      say "  validate-interaction -> exit $r"; printf '%s\n' "$out" | sed 's/^/      /' | head -12 ;;
    validate-bridge)
      out=$($PYZ validate-bridge 2>&1); r=$?
      say "  validate-bridge -> exit $r"; printf '%s\n' "$out" | sed 's/^/      /' | head -12 ;;
    check)
      out=$($PYZ check --json 2>&1); r=$?
      say "  check --json -> exit $r"
      printf '%s' "$out" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('      conditions:', d['result']['conditions'])
for f in d['findings']:
    if f['severity'] in ('medium','high','blocker'): print('      ', f['severity'], f['gate_id'], f['subject'], '--', f['reason'])
" ;;
  esac
done