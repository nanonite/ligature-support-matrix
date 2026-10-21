#!/usr/bin/env bash
# PROBE ONLY -- measure what `validate` does in the state epic #1 #111 would unlock.
#
# #111 is the escalation that says a concept spec can be drafted but not promoted, so
# `crates[].specs_search_root` resolves nothing and every boundary's G2+ check degrades
# to `applies_to unverifiable` (info). This probe simulates the post-fix state on a
# THROWAWAY rsync scratch copy by copying each staged `specs/<snake>.json.draft` to
# `specs/<snake>.json`, then re-running the validators.
#
# It is a measurement harness, not a procedure. Copying a concept spec into
# `rust/*/specs/**` by hand is a protected_roots write the installed SKILL.md forbids,
# so this NEVER runs on the live root -- only inside this script, under /tmp, on a copy
# that is deleted immediately afterwards. Nothing it produces is an approval.
set -u
ROOT=${1:?scratch root}
OUT=${2:?transcript path}
REVIEWER="scratch-probe-not-a-human-approval"
PYZ="python3 tools/ligature/ligature.pyz"
C="$ROOT/rust/swisstable-verus-core/specs"

: > "$OUT"
say() { printf '%s\n' "$*" | tee -a "$OUT"; }

say "=============================================================="
say "PROOF 5 -- post-#111 G2+ outcome (PROBE ONLY, scratch copy)"
say "root: $ROOT   reviewer: $REVIEWER (scratch only)"
say "The concept specs are made resolvable by copying each staged"
say "specs/<snake>.json.draft to specs/<snake>.json. That is a"
say "protected_roots write SKILL.md forbids, which is exactly why #111 is filed;"
say "doing it here is how we measure what a fix would reveal, not a fix."
say "=============================================================="
say ""

say "--- run the documented approve order first ---"
n=0; f=0
for d in $(ls "$ROOT"/evidence/*.json.draft 2>/dev/null); do
  $PYZ promote-evidence "${d%.draft}" >/dev/null 2>&1; n=$((n+1))
done
say "  evidence promoted: $n"
for pair in "_boundaries:boundaries" "_interactions:interactions" "_bridges:bridges"; do
  dir="${pair%%:*}"; label="${pair##*:}"; n=0; f=0
  for d in $(ls "$C/$dir"/*.json.draft 2>/dev/null); do
    if $PYZ approve --reviewer "$REVIEWER" "${d%.draft}" >/dev/null 2>&1; then n=$((n+1)); else f=$((f+1)); fi
  done
  say "  $label approved: $n, failed: $f"
done
n=0; f=0
for d in $(ls "$ROOT"/specs/_conflicts/*.json.draft 2>/dev/null); do
  if $PYZ approve --reviewer "$REVIEWER" "${d%.draft}" >/dev/null 2>&1; then n=$((n+1)); else f=$((f+1)); fi
done
say "  conflict resolutions approved: $n, failed: $f"
say ""

say "--- make the concept specs resolvable (the #111 probe step) ---"
for d in $(ls "$C"/*.json.draft 2>/dev/null); do cp "$d" "${d%.draft}"; done
say "  concept specs now on disk: $(ls "$C"/*.json 2>/dev/null | wc -l)"
say ""

say "--- validators in the post-#111 state ---"
for v in validate validate-interaction validate-bridge validate-witness; do
  out=$($PYZ $v 2>&1); r=$?
  say "  $v -> exit $r"
  printf '%s\n' "$out" | sed 's|'"$ROOT"'/||' | sed 's/^/      /' | tee -a "$OUT" > /dev/null
  printf '%s\n' "$out" | sed 's|'"$ROOT"'/||' | sed 's/^/      /'
done

say ""
say "--- check --json in the post-#111 state ---"
out=$($PYZ check --json 2>&1); r=$?
printf '%s' "$out" | python3 -c "
import json,sys,collections
d=json.load(sys.stdin)
print('  exit_code', d['result']['exit_code'], 'conditions', d['result']['conditions'])
c=collections.Counter((f['severity'],f['gate_id']) for f in d['findings'])
if not c: print('  findings: none')
for k,v in sorted(c.items()): print('  findings', k, v)
for f in d['findings']:
    if f['severity'] in ('high','blocker'):
        print('  BLOCKING', f['gate_id'], f['subject'].split('/')[-1], '--', f['reason'])
" | tee -a "$OUT"
say "  check --json -> exit $r"
say ""
say "=============================================================="
rm -rf "$ROOT"