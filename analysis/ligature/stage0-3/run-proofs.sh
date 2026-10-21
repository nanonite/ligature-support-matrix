#!/usr/bin/env bash
# Regenerate every Stage 0-3 proof artefact for chainlink #28 into
# analysis/ligature/stage0-3/ on throwaway rsync scratch copies.
#
# Five proofs, all against ligature 1.2.1 in copies of THIS pilot root:
#   1. drafting.txt           -- every artifact body, its command line, and its exit code
#   2. approval-proof.txt     -- approving in the documented order, then every validator
#   3. order-constraints.txt  -- deliberately wrong orders, to establish what the order IS
#   4. draft-collection.txt   -- which validators collect a staged .draft, one kind at a time
#   5. post-111-g2plus.txt    -- what validate() says once a concept spec is resolvable,
#                               i.e. the state epic #1 #111 asks for (PROBE ONLY: it makes the
#                               concept specs resolvable by a protected_roots copy, which is why
#                               #111 is filed; never performed on the live root)
#
# Each scratch copy is cleaned of every pipeline artifact first, so every proof is
# reproducible from artifacts.py alone rather than from whatever the live root happens
# to hold. Only the five transcript files land in the live root; the scratch trees and
# the --reviewer string that approve() writes into their ci/results/review_log.jsonl
# are deleted at the end.
set -u
PILOT=$(cd "$(dirname "$0")/../../.." && pwd)
OUT="$PILOT/analysis/ligature/stage0-3"
SCRATCH=${SCRATCH_BASE:-/tmp/opencode/p2-proof}
mkdir -p "$OUT"

fresh() { # fresh <name> [--keep-drafts]
  rm -rf "$SCRATCH/$1"
  mkdir -p "$SCRATCH"
  rsync -a --exclude 'upstream/' --exclude 'analysis/codesight/index/' \
        --exclude 'tools/codesight-mcp/' --exclude 'analysis/ligature/stage0-3/*.txt' \
        "$PILOT/" "$SCRATCH/$1/"
  if [ "${2:-}" != "--keep-drafts" ]; then
    rm -rf "$SCRATCH/$1/evidence" "$SCRATCH/$1/rust/swisstable-verus-core" "$SCRATCH/$1/specs"
    mkdir -p "$SCRATCH/$1/rust"
    : > "$SCRATCH/$1/rust/.gitkeep"
  fi
}
stage_all() { (cd "$SCRATCH/$1" && python3 analysis/ligature/stage0-3/artifacts.py --root "$SCRATCH/$1" > /dev/null 2>&1); }

echo "== proof 1: drafting =="
fresh draft; stage_all draft
cp "$SCRATCH/draft/analysis/ligature/stage0-3/drafting.txt" "$OUT/drafting.txt"
echo "   $(grep -c '^### ' "$OUT/drafting.txt") artifacts, $(tail -1 "$OUT/drafting.txt")"

echo "== proof 2: approving in order =="
fresh approve; stage_all approve
cp "$PILOT/analysis/ligature/stage0-3/approve-in-order.sh" "$SCRATCH/approve/analysis/ligature/stage0-3/"
(cd "$SCRATCH/approve" && bash analysis/ligature/stage0-3/approve-in-order.sh "$SCRATCH/approve" "$OUT/approval-proof.txt" > /dev/null 2>&1)
echo "   wrote approval-proof.txt"

echo "== proof 3: order constraints (deliberately wrong orders) =="
{
  echo "Order constraints for the #28 Stage 0-3 approve run. Each experiment runs a"
  echo "deliberately WRONG order on a fresh scratch copy and records what refuses."
  echo "Binary: ligature 1.2.1, sha256 30e504d388d5fb2acf1185fe3bfc17c96ec82483771d8d59a37fb3749009aacd."
  echo
  for spec in \
    "no-evidence conflicts|conflict resolutions approved with NO evidence promoted" \
    "no-evidence interactions validate-interaction|interactions approved with NO boundaries and NO evidence" \
    "no-evidence bridges validate-bridge|bridges approved with NO boundaries promoted" \
    "evidence boundaries interactions bridges validate-interaction validate-bridge check|the documented order, as a control"; do
    order=${spec%%|*}; label=${spec##*|}
    echo "================================================================"
    echo "EXPERIMENT: $label"
    echo "ORDER:     $order"
    echo "================================================================"
    name="ord-$(echo "$label" | tr ' ' '-' | tr -cd 'a-z-')"
    fresh "$name"; stage_all "$name"
    cp "$PILOT/analysis/ligature/stage0-3/order-probe.sh" "$SCRATCH/$name/analysis/ligature/stage0-3/"
    (cd "$SCRATCH/$name" && bash analysis/ligature/stage0-3/order-probe.sh "$SCRATCH/$name" "$order" /dev/null 2>&1 \
      | grep -E '^  \(no evidence|^  (evidence|boundaries|interactions|bridges|conflicts|validate-interaction|validate-bridge|check)|conditions:|G2/error|R2/error|G1b/error' | sed 's|/tmp/opencode/p2-proof/[a-z-]*/||' | head -22)
    echo
  done
  cat <<'EPILOGUE'
================================================================
READING THE ABOVE
================================================================
Three order constraints are enforced by the binary, all fail-closed:

  evidence  BEFORE  conflict resolution   G1b, dangling evidence id
  boundaries BEFORE interactions          R2, eligible I edge with no boundary
                                           contract and no reviewed exemption
  boundaries BEFORE bridges               G2, boundary_id does not resolve to any
                                           real boundary contract

One cross-reference is NOT enforced, and that is load-bearing for the runbook:
an interaction's `evidence_links` are never resolved against the evidence set, at
either approve or validate time. In the second experiment above, with NO evidence
record promoted at all, the single `inform` interaction
(`raw_table_find_to_hash_mix_h2`, which declares `evidence_links: ["E-001"]`)
approved at exit 0 and `validate-interaction` then reported 15/15 R2-covered. By
contrast a conflict-resolution record's `evidence` list IS resolved (experiment 1).
`doctor` declares the underlying gap in its own "Not yet implemented" section
("G4/G5 evidence tracing/grounding ... need cross-referencing interaction
evidence_links (#16) to evidence ids (#20)"), so it is a known unimplemented gate
rather than a defect; recorded as a pilot finding, not filed as an escalation.
EPILOGUE
} > "$OUT/order-constraints.txt"
echo "   wrote order-constraints.txt"

echo "== proof 4: which validators collect a staged .draft =="
{
  echo "Which validator collects a staged <target>.json.draft of its own kind, measured one"
  echo "kind at a time from a clean tree (every other pipeline artifact removed first)."
  echo "Binary: ligature 1.2.1. Filed as epic #1 #110."
  echo
  printf '%-14s %-30s %-6s %s\n' "draft kind" "validator" "exit" "check --json exit"
  for kind in boundary interaction bridge witness exemption conflict concept; do
    fresh "dc-$kind"
    (cd "$SCRATCH/dc-$kind" && python3 analysis/ligature/stage0-3/draft-one.py "$kind" "$SCRATCH/dc-$kind" > /dev/null 2>&1)
    case $kind in
      boundary) v=validate ;; interaction) v=validate-interaction ;; bridge) v=validate-bridge ;;
      witness) v=validate-witness ;; exemption) v=validate-exemption ;; conflict) v=validate-conflict-resolution ;;
      concept) v="(none: approve has no concept-spec branch)" ;;
    esac
    (cd "$SCRATCH/dc-$kind"
     out=$(python3 tools/ligature/ligature.pyz $v 2>&1); rc=$?
     out2=$(python3 tools/ligature/ligature.pyz check --json 2>&1); rc2=$?
     printf '%-14s %-30s %-6s %s\n' "$kind" "$v" "$rc" "$rc2"
     printf '%s\n' "$out" | grep -E 'OK|FAIL|G1a/error' | sed 's/^/      /')
  done
  echo
  echo "Conclusion: validate and validate-interaction SKIP staged drafts (chainlink #97,"
  echo "fixed in 1.2.0). validate-bridge, validate-witness, validate-exemption and"
  echo "validate-conflict-resolution still COLLECT them, fail closed on the missing"
  echo "review block, and turn check --json into exit 3 / human_decision_required."
} > "$OUT/draft-collection.txt"
echo "   wrote draft-collection.txt"

rm -rf "$SCRATCH"
echo "== proof 5: the post-#111 G2+ outcome (PROBE ONLY) =="
# Proof 5 runs last and deletes its own scratch tree (probe-post111.sh does that).
# It measures what `validate` would say once a concept spec is resolvable, which is
# the state epic #1 #111 asks for. Copying a concept spec into rust/*/specs/** by hand
# is a protected_roots write SKILL.md forbids -- that is exactly the escalation -- so
# this only ever happens inside the throwaway copy, and the transcript says so.
fresh post111; stage_all post111
cp "$PILOT/analysis/ligature/stage0-3/probe-post111.sh" "$SCRATCH/post111/analysis/ligature/stage0-3/"
(cd "$SCRATCH/post111" && bash analysis/ligature/stage0-3/probe-post111.sh "$SCRATCH/post111" "$OUT/post-111-g2plus.txt" > /dev/null 2>&1)
echo "   wrote post-111-g2plus.txt"
grep -E '^  (validate|check --json) -> exit' "$OUT/post-111-g2plus.txt" | sed 's/^/   /'
echo "done"