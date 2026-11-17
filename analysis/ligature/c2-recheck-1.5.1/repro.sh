#!/usr/bin/env bash
# C.2 re-check: _-prefixed directory scan convention drift (chainlink #56)
#
# Black-box probe of the pilot-local Ligature bundle. Every mutation happens
# in a throwaway copy under /tmp/opencode; the live pilot is read-only here.
#
# Run from anywhere:
#   bash date-creusot/analysis/ligature/c2-recheck-1.5.1/repro.sh
set -u

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PILOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
LIG="tools/ligature/ligature.pyz"
SCRATCH=$(mktemp -d /tmp/opencode/c2-recheck.XXXXXX)
OUT="$SCRIPT_DIR/raw"
mkdir -p "$OUT"

say() { printf '\n=== %s ===\n' "$*"; }
run() {
  # run <label> <case-dir> <command...>; records stdout/stderr and exit code
  local label=$1 case_dir=$2; shift 2
  ( cd "$case_dir" && python3 "$LIG" "$@" ) >"$OUT/$label.out" 2>"$OUT/$label.err"
  local rc=$?
  printf '%-34s exit=%s\n' "$label" "$rc"
  sed -n '1,4p' "$OUT/$label.out" | sed 's/^/    /'
  if [ -s "$OUT/$label.err" ]; then sed -n '1,4p' "$OUT/$label.err" | sed 's/^/    ERR /'; fi
  return 0
}
fresh() {
  # fresh <name>: rsync a pristine copy of the pilot into $SCRATCH/<name>
  rm -rf "$SCRATCH/$1"
  rsync -a --exclude 'target/' --exclude '.git/' --exclude 'upstream/' \
    "$PILOT/" "$SCRATCH/$1/"
}

cd "$PILOT" || exit 1
say "binary"
python3 "$LIG" version
(cd tools/ligature && sha256sum -c SHA256SUMS)
printf 'pilot=%s\nscratch=%s\n' "$PILOT" "$SCRATCH"

# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------
fresh baseline
run baseline-status "$SCRATCH/baseline" status --json
run baseline-validate "$SCRATCH/baseline" validate
run baseline-check "$SCRATCH/baseline" check --json

# ---------------------------------------------------------------------------
# A. Concept spec in an unknown _-prefixed dir: it is reported as a
#    "candidate outside specs_search_root" even though it is inside that root.
# ---------------------------------------------------------------------------
fresh concept-in-underscore
SPEC="$SCRATCH/concept-in-underscore/rust/date-creusot-core/specs"
mkdir -p "$SPEC/_concepts"
mv "$SPEC/weekday.json" "$SPEC/_concepts/weekday.json"
run concept-in-underscore-validate "$SCRATCH/concept-in-underscore" validate
run concept-in-underscore-status "$SCRATCH/concept-in-underscore" status
run concept-in-underscore-g14 "$SCRATCH/concept-in-underscore" gate-g14

# ---------------------------------------------------------------------------
# B. The same concept spec in a plain (non-underscore) subdirectory: no
#    diagnostic at all. validate exits 0 and status is clean, while gate-g14
#    still blocks because the concept is gone.
# ---------------------------------------------------------------------------
fresh concept-in-plain-subdir
SPEC="$SCRATCH/concept-in-plain-subdir/rust/date-creusot-core/specs"
mkdir -p "$SPEC/nested"
mv "$SPEC/weekday.json" "$SPEC/nested/weekday.json"
run concept-in-plain-subdir-validate "$SCRATCH/concept-in-plain-subdir" validate
run concept-in-plain-subdir-status "$SCRATCH/concept-in-plain-subdir" status
run concept-in-plain-subdir-g14 "$SCRATCH/concept-in-plain-subdir" gate-g14

# ---------------------------------------------------------------------------
# C. Concept spec in a known artifact dir: the DIRECTORY decides the kind, so
#    it is validated as a boundary and the error names boundary fields.
# ---------------------------------------------------------------------------
fresh concept-in-boundaries
SPEC="$SCRATCH/concept-in-boundaries/rust/date-creusot-core/specs"
cp "$SPEC/weekday.json" "$SPEC/_boundaries/probe_concept.json"
python3 - "$SPEC/_boundaries/probe_concept.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d['concept']='ProbeConcept'; json.dump(d,open(p,'w'),indent=2)
PY
run concept-in-boundaries-status-json "$SCRATCH/concept-in-boundaries" status --json
run concept-in-boundaries-validate "$SCRATCH/concept-in-boundaries" validate

# ---------------------------------------------------------------------------
# D. Concept spec in specs/_closure: validate-closure rejects it, gate-g14
#    rejects it, but status prints a second cluster row with
#    closure_kind=unknown and state=closes for the same cluster.
# ---------------------------------------------------------------------------
fresh concept-in-closure
cp "$SCRATCH/concept-in-closure/rust/date-creusot-core/specs/weekday.json" \
   "$SCRATCH/concept-in-closure/specs/_closure/probe_concept.json"
python3 - "$SCRATCH/concept-in-closure/specs/_closure/probe_concept.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d['concept']='ProbeConcept'; json.dump(d,open(p,'w'),indent=2)
PY
run concept-in-closure-status "$SCRATCH/concept-in-closure" status
run concept-in-closure-status-json "$SCRATCH/concept-in-closure" status --json
run concept-in-closure-validate "$SCRATCH/concept-in-closure" validate-closure
run concept-in-closure-g14 "$SCRATCH/concept-in-closure" gate-g14

# ---------------------------------------------------------------------------
# E. draft target check: every known artifact directory accepts every template,
#    then the generated JSON is validated against the DESTINATION's schema.
# ---------------------------------------------------------------------------
fresh draft-targets
for spec in \
  "concept-to-code rust/date-creusot-core/specs/probe_concept.json" \
  "concept-to-code rust/date-creusot-core/specs/_boundaries/probe_concept.json" \
  "concept-to-code rust/date-creusot-core/specs/_concepts/probe_concept.json" \
  "boundary-drafting rust/date-creusot-core/specs/_boundaries/probe_boundary.json" \
  "boundary-drafting rust/date-creusot-core/specs/probe_boundary.json"
do
  set -- $spec
  label="draft-$1-$(echo "$2" | tr '/.' '__')"
  run "$label" "$SCRATCH/draft-targets" draft 3 "$1" "$2"
done

# Full renders (all template variables supplied) show the schema mismatch.
python3 - "$SCRATCH/draft-targets/rust/date-creusot-core/specs/weekday.json" \
  > "$SCRATCH/probe_concept_no_review.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); d['concept']='ProbeConcept'; d.pop('review',None)
print(json.dumps(d))
PY
python3 - "$SCRATCH/draft-targets/rust/date-creusot-core/specs/_boundaries/year_month_day_ok__to__year_ok.json" \
  > "$SCRATCH/probe_boundary_no_review.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); d.pop('review',None); print(json.dumps(d))
PY
( cd "$SCRATCH/draft-targets" && python3 "$LIG" draft 3 concept-to-code \
    rust/date-creusot-core/specs/_boundaries/probe_concept.json \
    --var concept=ProbeConcept --var cluster=date-creusot-core --var verifier=creusot \
    --var source_material=rust/date-creusot-core/src/weekday.rs \
    --var prior_artifact=none --var finding=none \
    < "$SCRATCH/probe_concept_no_review.json" ) \
    >"$OUT/draft-concept-into-boundaries.out" 2>"$OUT/draft-concept-into-boundaries.err"
printf '%-34s exit=%s\n' "draft-concept-into-_boundaries" "$?"
grep -E 'FAIL:|G1a/error' "$OUT/draft-concept-into-boundaries.out" | sed 's/^/    /'

( cd "$SCRATCH/draft-targets" && python3 "$LIG" draft 3 boundary-drafting \
    rust/date-creusot-core/specs/probe_boundary_flat.json \
    --var caller_concept=YearMonthDay --var caller_concept_snake=year_month_day \
    --var caller_method=ok --var callee_concept=Year --var callee_concept_snake=year \
    --var callee_method=ok \
    --var caller_spec=rust/date-creusot-core/specs/year_month_day.json \
    --var callee_spec=rust/date-creusot-core/specs/year.json \
    --var reliance_policy=docs/reliance-policy.md \
    --var prior_artifact=none --var finding=none \
    < "$SCRATCH/probe_boundary_no_review.json" ) \
    >"$OUT/draft-boundary-flat.out" 2>"$OUT/draft-boundary-flat.err"
printf '%-34s exit=%s\n' "draft-boundary-flat" "$?"
grep -E 'FAIL:|G1a/error' "$OUT/draft-boundary-flat.out" | sed 's/^/    /'

# ---------------------------------------------------------------------------
# F. Cross-pilot control (crypto-mixed): same convention, different root.
#    Only status/validate are run; crypto-mixed has Kani evidence and check /
#    gate-g14 would rerun harnesses.
# ---------------------------------------------------------------------------
CRYPTO="$PILOT/../crypto-mixed"
if [ -d "$CRYPTO" ]; then
  rm -rf "$SCRATCH/crypto"
  rsync -a --exclude 'target/' --exclude '.git/' --exclude 'upstream/' "$CRYPTO/" "$SCRATCH/crypto/"
  CC="$SCRATCH/crypto/crates/crypto-mixed-core/specs"
  cp "$CC/cha_cha20.json" "$CC/_boundaries/cha_cha20.json"
  run crypto-concept-in-boundaries-status "$SCRATCH/crypto" status
  run crypto-concept-in-boundaries-validate "$SCRATCH/crypto" validate
  cp "$CC/cha_cha20.json" "$CC/../.cha_cha20.copy"
  rm -rf "$SCRATCH/crypto2"; cp -a "$SCRATCH/crypto" "$SCRATCH/crypto2"
  rm -f "$SCRATCH/crypto2/crates/crypto-mixed-core/specs/_boundaries/cha_cha20.json"
  mkdir -p "$SCRATCH/crypto2/crates/crypto-mixed-core/specs/_concepts"
  mv "$SCRATCH/crypto2/crates/crypto-mixed-core/specs/cha_cha20.json" \
     "$SCRATCH/crypto2/crates/crypto-mixed-core/specs/_concepts/cha_cha20.json"
  run crypto-concept-in-underscore-status "$SCRATCH/crypto2" status
  run crypto-concept-in-underscore-validate "$SCRATCH/crypto2" validate
  rm -rf "$SCRATCH/crypto2"
  rm -rf "$SCRATCH/crypto"
fi

say "artifacts"
printf 'raw outputs: %s\nscratch retained: %s\n' "$OUT" "$SCRATCH"
