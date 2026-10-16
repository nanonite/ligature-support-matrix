# Reliance policy — `date-creusot`

> This file is the standing governance document referenced by the project
> structure descriptor's `compatibility_policy.reliance_policy_path`. Version it
> like any other policy document: every substantive change to the resolution rule
> or the project-specific additions below requires the same human-authority
> checkpoint as the rest of the pipeline.

Schema version this policy targets: `1.0`.
Owner: `full-ligature-port workspace owner`.
Policy version: date-creusot-reliance-policy@1.0

The `Policy version:` line above is read to compute a promotion receipt's
`policy_version` field (chainlink #45, #14). The consumer is the binary, not a
workspace script:

    ligature accept-promotion <cluster> --reviewer <name> \
        --policy-path docs/reliance-policy.md --artifact docs/reliance-policy.md ...

`accept-promotion --help` states the requirement as
`Policy version: <name>@<major>.<minor>`, read from the accepted policy
document, which must itself be one of `--artifact`. There is no `scripts/`
directory in this workspace and no ligature command creates or installs one;
an earlier version of this paragraph named a
`scripts/generate_promotion_receipt.py` that does not exist, and was corrected
on 2026-09-25 (see `analysis/ligature/init-check.txt`, attempt 6).

Two things are unverified as of that correction, and both are recorded rather
than worked around: the line is not parsed until Stage 4.5, so nothing checks
its form before then, and `accept-promotion` requires the path to be passed
explicitly — `compatibility_policy.reliance_policy_path` in
`project-descriptor.json` is *not* consulted, and nothing checks that the
flag names the same file the descriptor does (chainlink #77).

Keep the line well formed and bump the version on every substantive policy
change.

## Resolution rule (fixed — do not override)

This table resolves the schema-prose vs. G2+ conflict (plan.md §2) and is
identical across every project using this pipeline. It is not a
project-specific choice:

| Source in the concept spec | Lands in the boundary artifact as |
|---|---|
| callee **precondition** | bridge specification (plan.md §8.2) — never a `callee_guarantees` entry |
| callee **postcondition** / **invariant** relied on | `callee_guarantees` |
| adversary case (`A*`) | evidence / test seed — **never** a guarantee, never eligible for `callee_guarantees` |

G2+ (role safety, plan.md §12) enforces the third row mechanically: an
adversary-case id inside `callee_guarantees` is a hard error, not a style
warning.

## Project-specific additions

Everything below this line is this project's own governance, additive to
the fixed rule above — it can narrow or clarify, but never contradict or
weaken the resolution table.

- **Domain-specific evidence sources.** The pinned HowardHinnant/date v3.0.5
  checkout at commit `179a6b921ccd6179b5b04dce812a89f71a51b4df`, its upstream
  CTest inventory, and the project's differential C++ oracle are authoritative
  evidence sources for this Mode P port. The pre-implementation verifier and
  closure decision is recorded in `analysis/ligature/closure-intent.json`.
- **Additional role-safety checks specific to this project's domain.** Creusot
  obligations for era arithmetic must state overflow preconditions explicitly;
  loop and ghost invariants used by the calendar and ISO-week algorithms must
  appear as guarantees, never only as test observations.
- **Escalation path** for a boundary artifact that appears to need a rule this
  policy does not cover: the workspace owner decides, the decision is recorded
  in this document, and the policy version is bumped before the boundary is
  promoted. Ligature defects are filed under epic #1 instead.

## Change history

| Version | Date | Reviewer | Change |
|---|---|---|---|
| `1.0` | `2026-09-25` | `chainlink-reviewer` | Initial adoption for the date-creusot port; filled schema version, owner, policy version, and project-specific rules |
| `1.0` | `2026-09-25` | `chainlink-reviewer` | Non-substantive correction: the `Policy version:` provenance note named a `scripts/generate_promotion_receipt.py` that does not exist in this workspace. Resolution table and project-specific rules unchanged, so the version is deliberately not bumped; `policy_version` stays `date-creusot-reliance-policy@1.0` |
