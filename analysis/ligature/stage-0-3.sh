#!/usr/bin/env bash
# Stage 0-3 driver for chainlink #13 (pilot date-creusot).
#
# Drives the pinned tools/ligature/ligature.pyz through the whole of Stages 0
# and 3 using the shipped `manual` llm_backend: for each artifact the script
# calls `draft`, piping the JSON response body kept verbatim in
# analysis/ligature/draft-responses/, then calls `approve` with the workspace's
# declared reviewer. The binary's verdict and the exit code of every command
# are printed, so the transcript is evidence and not a paraphrase.
#
# Run with the pilot root as cwd, inside the date-creusot nix shell:
#   nix develop ..#date-creusot -c bash -lc \
#     'cd date-creusot && bash analysis/ligature/stage-0-3.sh'
#
# Nothing here is interactive: with llm_backend.kind = manual, `draft` renders
# the stage prompt to stdout and reads the "model response" from stdin, and
# the response bodies are files.
#
# ####################  HUMAN CHECKPOINT GUARD  ####################
# There are TWO human promotion checkpoints in this script, and attempt 2 of
# chainlink #13 guarded only one of them, which the reviewer caught:
#
#   (a) Stage 0's evidence `mv` loop  -- the tool has no promotion path for
#       evidence at all (chainlink #78), so moving the staged draft to the
#       target path IS the promotion, and it is a hand step.
#   (b) Stage 3's `approve` calls     -- the tool-mediated promote.
#
# Attempt 1 ran both unattended and was rejected: the hash-pinned authority text
# in .codex/skills/ligature/SKILL.md says "Human approval remains human" and
# "Do not cross an approve/promote checkpoint on your own". Attempt 2 added a
# guard for (b) only, and its banner claimed "nothing was approved" while the
# 15 evidence records were being moved -- a false statement, and the reason
# attempt 2's own "tested both ways" evidence was worthless: the test ran
# against an already-promoted copy where the idempotency fix silently dropped
# the identical drafts and hid the hole.
#
# So: the guard now covers BOTH, and the banner reports what actually happened
# instead of asserting something the reader has to take on trust. Every
# `draft` still runs -- that is the agent's own work and it is not a
# checkpoint. Nothing is promoted unless a human sets
# LIGATURE_HUMAN_APPROVAL=1, which is the documented way to say "I have read
# these artifacts and I am the one promoting them".
#
#   LIGATURE_HUMAN_APPROVAL=1 bash analysis/ligature/stage-0-3.sh
#
# Rationale for why the guard exists rather than a comment: a missing tool
# guardrail is not permission to cross the checkpoint. See
# analysis/ligature/stage-3-decisions.md sections 5 and 9.
# What the guard actually did, so the banner can report it instead of
# asserting "nothing was approved" -- which was false in attempt 2.
evidence_moved=0
evidence_dropped=0
evidence_blocked=0
tool_promotes_blocked=0

# How many staged .draft files are sitting on disk right now. A staged draft is
# a BLOCKING finding for check and validate-evidence (date-ligature-020), so an
# unflagged run is not a clean no-op: it promotes nothing but it does leave
# drafts behind, and the reviewer was right that the banner has to say so.
staged_drafts_now() {
  local n=0 f
  for f in evidence/*.draft rust/date-creusot-core/specs/*/*.draft; do
    [ -e "$f" ] && n=$((n + 1))
  done
  printf '%s' "$n"
}

# Emit the guard banner. Takes the checkpoint name so the message says which
# one it stopped at, prints the real counters, and -- critically -- reports the
# staged drafts this run is leaving on disk.
guard_stop() {
  local where="$1" staged
  staged="$(staged_drafts_now)"
  cat >&2 <<GUARD
  STOPPED at a human promotion checkpoint: $where

  What this run actually did, counted, not asserted:
    evidence records moved .draft -> .json : $evidence_moved
    identical drafts dropped, target already promoted : $evidence_dropped
    evidence moves withheld by this guard             : $evidence_blocked
    tool-mediated 'approve' promotions withheld       : $tool_promotes_blocked
    staged .draft files now sitting on disk          : $staged

  Every \`draft\` ran and was schema-checked by the binary. Promotion did not.

  THIS RUN IS NOT A CLEAN NO-OP. It promoted nothing, but the \`draft\` steps
  still staged their output, and a staged .draft is a BLOCKING finding: \`check\`
  and \`validate-evidence\` will report it, and \`check\` exits 3
  human_decision_required while any interaction draft exists. On a tree that
  was already promoted you will get 8 fresh staged drafts in
  rust/date-creusot-core/specs/{_boundaries,_interactions}/ and \`check\` will
  drop from exit 0 to exit 3. To undo a run you did not intend, delete the
  staged .draft files; the promoted .json files are not touched.

  Both promotion paths are human checkpoints and this script will not cross
  either unattended. To promote, a human must read the staged drafts, then:

      LIGATURE_HUMAN_APPROVAL=1 bash analysis/ligature/stage-0-3.sh

  Rulings needed: stage-3-decisions.md section 9.1 (the eight 'review' blocks),
  section 5.2 (the evidence move, chainlink #78), section 3.1 (the hand-declared
  constraint ids).
GUARD
}

approve() {
  if [ "${LIGATURE_HUMAN_APPROVAL:-0}" != 1 ]; then
    tool_promotes_blocked=$((tool_promotes_blocked + 1))
    guard_stop "Stage 3 tool-mediated approve, for $1"
    return 3
  fi
  local target="$1" rc
  printf '\n$ python3 %s approve %s --reviewer %s --reviewed-at %s\n' \
    "$pyz" "$target" "$reviewer" "$reviewed_at"
  python3 "$pyz" approve "$target" --reviewer "$reviewer" --reviewed-at "$reviewed_at"
  rc=$?
  printf '    EXIT=%d\n' "$rc"
  return $rc
}

# ###########################################################################

# The rendered prompt is suppressed for every invocation except the first, whose
# prompt is kept in full because it is the one that interpolates
# {{reliance_policy}} (chainlink #78, date-ligature-018).
set -u
shopt -s nullglob

root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root" || exit 127
pyz=tools/ligature/ligature.pyz
resp=analysis/ligature/draft-responses
reviewer=chainlink-reviewer
reviewed_at=2026-09-25
descriptor="$(cat project-descriptor.json)"
policy="$(cat docs/reliance-policy.md)"
no_spec='(no concept-to-code spec is reachable in ligature v1.0; see analysis/ligature/stage-3-decisions.md section 3)'
no_prior='(none - first draft, no prior artifact exists and no finding triggered re-entry)'
first=1

hdr()  { printf '\n===== %s =====\n' "$*"; }

# Show the binary's own verdict lines, plus the whole rendered prompt the very
# first time so the interpolation is on the record.
verdict() {
  local f="$1" keep="$2"
  if [ "$keep" = 1 ]; then sed 's/^/      | /' "$f"
  else printf '      | (rendered prompt suppressed: %s lines)\n' "$(wc -l <"$f")"; fi
  grep -E '^(staged draft|OK:|FAIL:|approved:|error:|usage:)' "$f" | sed 's/^/      > /'
  grep -E '^ +- \[' "$f" | sed 's/^/      > /'
}

# draft <stage> <template> <target> <keep-prompt> -- <var=value>...
draft() {
  local stage="$1" tmpl="$2" target="$3" keep="$4"; shift 5
  local f rc first=1
  f="$(mktemp)"
  printf '$ python3 %s draft %s %s %s' "$pyz" "$stage" "$tmpl" "$target"
  for v in "$@"; do
    if [ "$first" = 1 ]; then printf ' '; else printf ' \\\n    '; fi
    printf '%s' "$v" | cut -c1-72
    first=0
  done
  printf '\n'
  python3 "$pyz" draft "$stage" "$tmpl" "$target" "$@" >"$f" 2>&1
  rc=$?
  verdict "$f" "$keep"
  printf '    EXIT=%d\n' "$rc"
  rm -f "$f"
  return $rc
}

snake() { printf '%s' "$1" | sed -E 's/([a-z0-9])([A-Z])/\1_\2/g' | tr '[:upper:]' '[:lower:]'; }

################################################################################
hdr 'preflight'
( cd tools/ligature && sha256sum -c SHA256SUMS ) | sed 's/^/    /'
python3 "$pyz" version | sed 's/^/    /'
printf '    descriptor sha256:      %s\n' "$(sha256sum project-descriptor.json | cut -d' ' -f1)"
printf '    reliance-policy sha256: %s\n' "$(sha256sum docs/reliance-policy.md | cut -d' ' -f1)"
printf '    upstream/date HEAD:     %s\n' "$(git -C upstream/date rev-parse HEAD)"
printf '    upstream/date porcelain:[%s]\n' "$(git -C upstream/date status --porcelain)"

################################################################################
hdr 'STAGE 0 -- evidence (15 records, workspace-level evidence/)'
e() {  # e <id> <material>
  local keep=0; [ "$first" = 1 ] && { keep=1; first=0; }
  draft 0 evidence-intake "evidence/$1.json" "$keep" -- \
    --var "project_descriptor=$descriptor" \
    --var "source_material=$2" \
    --var "prior_artifact=$no_prior" \
    --var "finding=$no_prior" <"$resp/$1.json"
}
e E-1  'include/date/date.h:2976-2993  year_month_day::to_days()'
e E-2  'include/date/date.h:3090-3109  year_month_day::from_days()'
e E-3  'include/date/date.h:1826-1832  weekday::weekday_from_days()'
e E-4  'include/date/date.h:3009-3017  year_month_day::ok()'
e E-5  'include/date/date.h:2739-2754  year_month_day_last::day()'
e E-6  'include/date/date.h:2981-2984  the two static_asserts'
e E-7  'include/date/iso_week.h:438-445  iso_week::weekday::weekday_from_days()'
e E-8  'include/date/iso_week.h:422-436  to_iso_encoding / from_iso_encoding'
e E-9  'test/date_test/year_month_day.pass.cpp:208-216'
e E-10 'test/iso_week/weekday.pass.cpp:88-105'
e E-11 'include/date/date.h:2976-3017  CONSTCD14 / CONSTCD11 levels'
e E-12 'include/date/date.h:401-427  date::year representation, min, max, ok'
e E-13 'analysis/ligature/evidence-probe.out  z = 0, -1, -4, -5, 3, 4'
e E-14 'analysis/ligature/evidence-probe.out  18-case sample and E-14 totals'
e E-15 'analysis/ligature/evidence-probe.out  the 1900-02-29 and 2023-02-29 rows'

hdr 'STAGE 0 -- evidence has no promotion path (approve refused by design)'
printf '$ python3 %s approve evidence/E-1.json --reviewer %s --reviewed-at %s\n' \
  "$pyz" "$reviewer" "$reviewed_at"
python3 "$pyz" approve evidence/E-1.json --reviewer "$reviewer" --reviewed-at "$reviewed_at" 2>&1 \
  | fold -s -w 92 | sed 's/^/    | /'
printf '    EXIT=%d\n' "${PIPESTATUS[0]}"

hdr 'STAGE 0 -- move each staged draft to the target path draft itself named'
# THIS LOOP IS A HUMAN PROMOTION CHECKPOINT, not a cleanup step. The tool has no
# promotion path for evidence at all (chainlink #78): approve refuses evidence
# permanently, so moving the staged draft to the target path IS the promotion.
# Attempt 2's guard covered only Stage 3 and the reviewer caught that these 15
# moves happened unattended while the banner claimed nothing was approved.
#
# Idempotent as well: a re-run must not leave an orphan .draft behind, because a
# staged draft is a *blocking* finding for validate-evidence and check
# (date-ligature-020).
for f in evidence/E-*.json.draft; do
  t="${f%.draft}"
  if [ -e "$t" ]; then
    if cmp -s "$t" "$f"; then
      rm -f "$f"; evidence_dropped=$((evidence_dropped + 1))
      printf '    drop  %s (identical to the promoted target; nothing to promote)\n' "$f"
    else
      printf '    CONFLICT %s differs from the promoted %s -- left in place, not overwritten\n' "$f" "$t"
    fi
  elif [ "${LIGATURE_HUMAN_APPROVAL:-0}" = 1 ]; then
    mv -n "$f" "$t" && evidence_moved=$((evidence_moved + 1)) \
      && printf '    mv    %s -> %s\n' "$f" "$t"
  else
    evidence_blocked=$((evidence_blocked + 1))
    printf '    WITHHELD %s -> %s  (human promotion checkpoint, see chainlink #78)\n' "$f" "$t"
  fi
done
if [ "$evidence_blocked" -gt 0 ]; then
  guard_stop "Stage 0 evidence promotion, $evidence_blocked record(s)"
fi

################################################################################
BD=rust/date-creusot-core/specs/_boundaries
ID=rust/date-creusot-core/specs/_interactions
mkdir -p "$BD" "$ID"

hdr 'STAGE 3 -- boundary contracts (O)'
b() {  # b <id> <target-file> <caller_concept> <caller_method> <callee_concept> <callee_method>
  draft 3 boundary-drafting "$BD/$2" 0 -- \
    --var "caller_concept=$3" --var "caller_method=$4" \
    --var "callee_concept=$5" --var "callee_method=$6" \
    --var "caller_concept_snake=$(snake "$3")" \
    --var "callee_concept_snake=$(snake "$5")" \
    --var "caller_spec=$no_spec" --var "callee_spec=$no_spec" \
    --var "reliance_policy=$policy" \
    --var "prior_artifact=$no_prior" --var "finding=$no_prior" <"$resp/$1.json"
}
b O-1 year_month_day_to_days__to__weekday_weekday_from_days.json \
     YearMonthDay to_days Weekday weekday_from_days
b O-2 year_month_day_to_days__to__year_month_day_from_days.json \
     YearMonthDay to_days YearMonthDay from_days
b O-3 year_month_day_ok__to__year_month_day_last_day.json \
     YearMonthDay ok YearMonthDayLast day
b O-4 iso_week_weekday__to__weekday_iso_encoding.json \
     IsoWeek weekday Weekday iso_encoding

hdr 'STAGE 3 -- approve the boundary contracts'
for t in "$BD"/*.json.draft; do approve "${t%.draft}"; done

hdr 'STAGE 3 -- interactions (I)'
i() {  # i <id> <target-file> <interaction_id> <cc> <cm> <kc> <km>
  draft 3 interaction-drafting "$ID/$2" 0 -- \
    --var "interaction_id=$3" \
    --var "caller_concept=$4" --var "caller_method=$5" \
    --var "callee_concept=$6" --var "callee_method=$7" \
    --var "caller_spec=$no_spec" --var "callee_spec=$no_spec" \
    --var 'target_triple=x86_64-unknown-linux-gnu' \
    --var "prior_artifact=$no_prior" --var "finding=$no_prior" <"$resp/$1.json"
}
i I-1 I-year-month-day-to-days-to-weekday-weekday-from-days.json \
     I-year-month-day-to-days-to-weekday-weekday-from-days \
     YearMonthDay to_days Weekday weekday_from_days
i I-2 I-year-month-day-to-days-to-year-month-day-from-days.json \
     I-year-month-day-to-days-to-year-month-day-from-days \
     YearMonthDay to_days YearMonthDay from_days
i I-3 I-year-month-day-ok-to-year-month-day-last-day.json \
     I-year-month-day-ok-to-year-month-day-last-day \
     YearMonthDay ok YearMonthDayLast day
i I-4 I-iso-week-weekday-to-weekday-iso-encoding.json \
     I-iso-week-weekday-to-weekday-iso-encoding \
     IsoWeek weekday Weekday iso_encoding

hdr 'STAGE 3 -- approve the interactions'
for t in "$ID"/*.json.draft; do approve "${t%.draft}"; done

################################################################################
hdr 'postflight -- read-only state only (no validate*/gate*/report: that is chainlink #14 and #16)'
python3 "$pyz" status;              printf '    EXIT=%d\n' "$?"
python3 "$pyz" check;               printf '    EXIT=%d\n' "$?"
python3 "$pyz" doctor 2>&1 | sed -n '/^Installation:/,$p' | sed 's/^/    /'
printf '    descriptor sha256:      %s\n' "$(sha256sum project-descriptor.json | cut -d' ' -f1)"
printf '    reliance-policy sha256: %s\n' "$(sha256sum docs/reliance-policy.md | cut -d' ' -f1)"
printf '    upstream/date porcelain:[%s]\n' "$(git -C upstream/date status --porcelain)"
printf '\n===== done =====\n'
