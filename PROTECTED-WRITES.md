# Protected-root writes: command-mediated, issue-scoped

Status: operational guidance originally written for the Ligature 1.2.2
rollout; updated for the 1.3.2 bundle on 2026-10-08.
This document does not change a pilot descriptor, grant a capability, widen
worker roots, or authorize a human checkpoint. The worker remains Tier 0.
Tier 1 means only the named, deterministic commands below, under a matching
issue-scoped grant. Normative choices remain Tier 2.

No generic scratch/rsync/apply wrapper for arbitrary supervisor edits was
implemented in this rollout. Tier 1 is limited to the native, grant-aware
verbs below. If a mechanical repair has no sanctioned verb, request a human
decision rather than treating this document or an LLM wrapper as authority.

## Why a separate Tier 1 lane exists

The worker's write set is a real safety boundary. A Cargo.toml changes the
build graph and dependency surface; a Stage 7 manifest changes what gates
consider proved, assumed, and covered; policy text changes what claims the
project makes. Letting workers hand-write those files, or widening
allowed_roots to include them, would make intent difficult to audit and would
grant more authority than a port task needs.

At the same time, repeatedly stopping for purely mechanical protected writes
stalls ordinary work (#30 took 14 attempts before the missing crate manifest
was escalated), while unconstrained hand edits make generated metadata
nondeterministic. Ligature supplies bounded verbs for the recurring mechanical
cases. They derive files from declared project state and structured
inputs, validate them, and attach an issue/grant audit trail. This is why a
Tier 1 lane is useful: it narrows a repeatable transformation, not the
worker's general authority.

The verbs do not decide policy, proof scope, assumptions, or what counts as a
claim. Those remain human decisions. A grant is not a general permission to
edit the target by hand.

## Tiers

| Tier | Actor | Authority |
|---|---|---|
| T0 — worker | Chainlink-loop worker | Existing allowed_roots only. It may request a protected write, but must not make one directly. |
| T1 — supervisor/tool lane | Named supervisor explicitly listed in descriptor write_set.authorized_supervisors, or a human-issued issue grant consumed by a sanctioned verb | Only the structured transformation and exact path/op authorized for that issue. No arbitrary protected-file editing. |
| T2 — human | Project operator / reviewer | Policy text, write-scope changes, approvals and rulings, proof/spec claims, verifier and closure decisions, and any change that changes what a gate or proof asserts. |

The supervisor identity is not implicitly trusted because it is an LLM. A
supervisor grant is accepted only when the named identity is declared in the
project descriptor. On 2026-10-07, the operator explicitly authorized the
SwissTable pilot's `opencode-swisstable-t1` identity for the supervisor lane;
each grant remains bound to one issue, exact path, operation, and TTL. The same
operator authorized only the root-level `PORT-GAPS.md` path in `allowed_roots`
so the #30 porting deliverable can be completed. These are pilot-specific
authorizations, not a general widening of worker roots.

## Protected-write verbs and where they fit

| Workflow point | Command | What it is for / boundary |
|---|---|---|
| Before a sanctioned protected write | authorize-write --issue N --path P --op write --issuer NAME [--issuer-kind human or supervisor] [--ttl SECONDS] [--one-shot] --json | Issues a capability record for one issue, path/op, issuer, and expiry. It appends to ci/results/protected-writes.jsonl. A supervisor issuer must be descriptor-authorized; a human issuer is a human checkpoint. |
| New declared crate, before implementation (#30) | scaffold-crate --issue N --crate NAME [--grant-id ID] --json | Derives the Cargo.toml and canonical source skeleton from a crate already declared in the descriptor. It is not a free-form manifest editor. Requires a matching grant for the protected manifest. |
| Configure an existing Verus crate (#30) | configure-crate --issue N --crate NAME --profile cargo-verus [--grant-id ID] --json | Applies the typed Verus Cargo profile to one existing descriptor-declared crate under an exact Cargo.toml grant. It is not a hand-edit authorization. On the 1.3.2 SwissTable pilot, the command refuses with `vstd-version-unavailable` for the Nix-packaged Verus toolchain; local escalation #124 tracks that blocker. Do not bypass the refusal with a manual Cargo.toml edit. |
| Stage 7 work-package creation (#29) | generate-work-package --plan PLAN --issue N --toolchain VALUE --target TRIPLE [--feature NAME ...] [--grant-id ID] --json | Generates the canonical work-package manifest from structured plan/descriptor inputs and validates the generated shape. It replaces hand-authored Stage 7 bookkeeping; it does not choose new proof claims on the operator's behalf. |
| Release install/upgrade | migrate --upgrade | Updates files Ligature owns and refreshes its installation/gate-integrity metadata. It does not rewrite user-owned project policy or decide whether a preserved project artifact is semantically safe. Do not use --force or --prune as routine upgrade switches. |
| Human policy acceptance (Stage 4.5) | accept-policy --reviewer HUMAN --version NAME@MAJOR.MINOR | Human-only. It stamps the Policy version marker and records acceptance; it changes no other policy prose. A human must author/review the actual policy and select the version. |
| After a protected write | write-set-check --issue N --json | Checks the write set while consuming only grants for issue N. Without --issue, no grant is consumed and an otherwise-ungranted protected write is a blocking violation. Follow with the relevant validators and gates. |

The intended sequence for a mechanical protected write is:

1. Worker emits a PROTECTED-WRITE REQUEST with issue, exact path, operation,
   proposed command, and why the operation is mechanical.
2. Supervisor checks that the request is within the command's structured
   inputs and does not change policy or proof claims. If it is Tier 2, stop
   and ask the operator.
3. A human or an already-authorized supervisor issues the exact grant.
   Then run the sanctioned command, not a hand edit.
4. Run write-set-check with the same issue number, the command-specific
   validator, doctor, and check --json. Record results with the issue.

Do not treat authorize-write as the generator: it records a bounded
capability; the sanctioned verb performs the transformation. Do not fabricate
historical grant records. The incident table below is the historical record;
the protected-writes ledger records grants actually issued by the command.

The --one-shot option is an attribution label, not a strict edit counter:
write-set-check sees a workspace snapshot, not every intermediate edit. Its
TTL bounds the attribution window. A pattern grant can authorize multiple
writes during its TTL. Prefer one exact path, a short TTL, and a separate
grant for each issue/write.

## Migration severity: decide by workflow impact

migrate is a mechanical updater, not a complete semantic reviewer. Its exit
code and notices are evidence, not the final severity classification. Apply
these rules:

| Classification | Use when | Required response |
|---|---|---|
| Hard error / stop | migrate fails; output is malformed or incomplete; an active managed gate/skill/schema/prompt has a conflict or unpinned hash; descriptor or required artifact is invalid; a protected write lacks an active matching grant; or a gate required by the current phase fails because of the migration | Do not continue or close the phase. Preserve the before-state, identify the exact path and consumer, and resolve through the owning human or sanctioned tool path. Never force-overwrite to make the check green. |
| Warning, with a named deadline | A preserved user-owned or optional artifact has a known issue outside the current code-authoring decision, and no active phase gate consumes it as valid input | Record owner, path, affected later stage, and recheck condition. Defer only for that phase; do not call the artifact accepted. |
| Informational | The workspace is not initialized and no project migration was applicable, or the output confirms unchanged managed files with current hashes | Record the state. Do not run project gates as if initialization had happened. |

Example from the 1.2.2 rollout: SwissTable migrate reported its user-owned
reliance-policy file still has the template Policy version placeholder. That
is a warning for code-authoring work while the policy is not being accepted.
It makes doctor exit 1, however, so under WORKER-CONTRACT §1 it blocks
Ligature-dependent verification and issue closure until the human resolves
the marker/content checkpoint. It is also a hard blocker before Stage 4.5
policy acceptance or promotion. accept-policy --version can stamp a
human-selected version; it cannot author the policy's project-specific
substance. The distinction is: code authoring may continue, but no clean
verification/close may be claimed.

Conversely, failure to pin or validate a managed file used by the active gate
is a hard blocker even if migrate calls it a notice. A warning is never a
waiver for a proof assumption, verifier choice, write scope, active manifest,
or gate input.

## Historical incident record (seven cases)

| Issue | Pilot / path | Kind | 1.2.2 disposition |
|---|---|---|---|
| #87 | date-creusot, ci/manifest/WP-DATE-CREUSOT.json required_guarantees | Self-reference in the work-package's own inputs | Mechanical manifest correction was separately diagnosed and applied. The generator helps prevent invalid new manifests; it does not retroactively repair this file. |
| #92 | date-creusot, WP report.emit | Report/assurance path collision | Resolved upstream in 1.1.1; no protected write needed. |
| #103 | date-creusot, depends_on and gate_integrity | Manifest dependency repair plus managed hash refresh | migrate owns managed installation hashes only. A user-owned work-package dependency still needs an explicit, validated project edit. |
| #105 | date-creusot, project-descriptor and manifest write_policy | Protected write-scope change | T2: the operator selected the scope. Do not automate a scope change. |
| #29 | swisstable-verus, ci/manifest/WP-SWISSTABLE-VERUS.json | Stage 7 bookkeeping | The existing manifest was hand-authored under 1.2.1. 1.2.2 now has generate-work-package for future generation from a structured plan and a matching grant. |
| #114 | swisstable-verus, docs/reliance-policy.md | Normative policy content/version | T2. 1.2.2 accept-policy --version removes the placeholder-marker dead end, but the human still authors/reviews policy content and chooses the version. |
| #30 | swisstable-verus, rust/swisstable-verus-core/Cargo.toml | Missing declared-crate scaffold | scaffold-crate is now available and requires an issue grant. No grant has been issued for #30 in this rollout. |

The upstream 1.2.2 implementations for protected-write enforcement,
authorize-write, scaffold-crate, work-package generation, migration, and
policy-version stamping are shipped. Historical evidence above is not itself
a capability grant. Do not invent records to make the protected-write ledger
look complete; retain the dated incident history here.

## Current workspace rollout findings

- date-creusot and swisstable-verus now use the checksum-verified 1.2.2
  bundle and report installation current with gate integrity pinned after
  migrate --upgrade.
- date-creusot check and gate-r1-g16 still report five blocking R1
  absent-from-I findings. This is live project work, not a migration failure.
- swisstable-verus migrate preserved the user-owned policy placeholder with
  the stage-scoped warning described above; doctor exits 1 on this state.
  Its current check finding is the missing C_static report, not a failed
  migration.
- crypto-mixed has the 1.2.2 CLI but is uninitialized; no migrate was run.
- No capability grants were issued during this rollout.

## Local epic #1 audit against 1.2.2

As of 2026-10-06, the local epic still has open children even where the
upstream defect is fixed. IDs in this section are from this port workspace's
Chainlink database; upstream issue numbers differ. The release-level outcomes
are:

- Addressed in 1.2.2 (local issue status still open): #72 descriptor
  closure/diagnostics; #75 verifier-policy schema and second-verifier
  declaration; #79 missing authoring/promotion paths; #90 protected-write
  false negative; #106 missing-draft approval crash; #107 missing-descriptor
  extractor crash; #110 staged-draft collection; #112 Stage 3 template
  contradiction; #113 bridge-template/G9 mismatch; #114 policy-version
  stamping; and #116–#119 authorize-write, scaffold-crate,
  generate-work-package, and migrate hash refresh.
- Not complete in the live P1 workspace: #91. The current
  gate-r1-g16 still reports five blocking cross-concept calls absent from
  the interaction set. The old claim that there was no worker-reachable
  draft path is superseded, but the required specs and human approval,
  ruling, and promotion checkpoints have not been completed. Keep this
  issue open until those artifacts and gates are actually reviewed.

This is a verification result, not permission to close local issues. The
local tracker has not been mutated. For current P2, #30 is next; its blockers
#29 and #4 are closed, but scaffold-crate still needs an issue-scoped grant.
