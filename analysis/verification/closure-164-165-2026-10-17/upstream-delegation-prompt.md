# Prompt for the Ligature upstream owner

Work in `/home/goya/agent-workspace/ligature-workspace` to resolve upstream
Ligature Chainlink issues #164 and #165 and produce an attested release for
downstream black-box verification. Read the applicable repository instructions
and the complete issues and comments before editing. This prompt authorizes
source work in the upstream project; the port workspace retains its black-box
restriction. Do not inspect bundles or edit source from the port workspace's
worker session.

Use the correct tracker explicitly:

```sh
chainlink --db /home/goya/agent-workspace/ligature-workspace/.chainlink --json issue show 164
chainlink --db /home/goya/agent-workspace/ligature-workspace/.chainlink --json issue show 165
chainlink --db /home/goya/agent-workspace/ligature-workspace/.chainlink --json issue show 161
chainlink --db /home/goya/agent-workspace/ligature-workspace/.chainlink --json issue show 143
```

These numbers belong to the upstream tracker. The port workspace's local
#143 is a different, already-closed Codesight issue. All local follow-ups
#136–#143 are currently closed. Local #144 records this handoff.

## #164: regeneration provenance

Ligature 1.4.0's regeneration identity check accepts changed JSON if it retains
the expected schema and package ID. That allows a manually changed manifest
to be overwritten under a fresh grant and described as generated content.

Bind the existing manifest's exact bytes to trustworthy prior generation
provenance for its canonical path and package before replacing it. Use the
latest successful generation state, not any historical matching hash, so
rollback cannot bypass the check. Keep full candidate validation, exact-path
issue-bound grants, grant replay protection, atomic updates and preservation
of existing bytes and audit state on refusal. An unchanged/no-op event must
not silently establish provenance for an untracked manifest. Check deletion
and malformed or orphan audit history as well.

If a legacy manifest has no prior generation audit, either refuse with an
actionable supported recovery path or provide explicit, grant-bound adoption
that cannot bless arbitrary edits. Document the audit ledger's trust boundary;
do not claim cryptographic authentication from an unsigned hash ledger.

Add meaningful source and packaged CLI regressions for same-package edits
(including report.emit and obligation scope), rollback, missing provenance,
valid regeneration, grant reuse and refusal preservation. Preserve assurance
and feature-ledger output coexistence.

The current downstream manifest is **not edited**: its SHA-256 is
`2adfab4a7d2c957ddc29d393c17b788630ccedb1a15a7d50fcd36cfe45bc61b2`
and matches its latest generation event. Its prior grant is
`GW-d354d42d53a0`. Avoid breaking this legitimate historical provenance merely
because its grant has since expired.

## #165: integration fixtures

The three failing IntegratedWorkspace tests in
`tests/test_generate_work_package.py` lack accepted assurance-source context
for `TaskQueue.C003`. Fix only test setup, using an approved concept constraint
or legitimate reviewed interaction reliance. The existing interaction fixture
references evidence `E-0143`; ensure that referenced evidence is supplied if
using the interaction route. A reviewed concept by itself may not satisfy the
fixture's bridge intake. Preserve refusal of absent or unreviewed sources;
do not weaken production assurance validation to admit fixtures.

Run the required focused suites:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider \
  tests/test_work_package_manifest.py tests/test_satisfies.py \
  tests/test_record_assurance.py tests/test_generate_work_package.py
```

Also run the relevant packaged acceptance tests against the **exact release
artifact**, including a same-package edited-manifest refusal. Compare broader
suite failures with the unchanged baseline and report existing failures
honestly; never describe a failing full suite as green.

## Release and downstream handoff

Build the corrected release from a clean, committed source state. Record the
version, full source commit, artifact SHA-256, content/adjudicator hash,
`SHA256SUMS`, `PROVENANCE.json`, `version --verify` output, and test results.
Make the source change and exact release artifact available to the downstream
worker through the normal upstream repository/release workflow.

Do not modify the port workspace's descriptors, policy, proof scope, approved
specifications, grants, protected manifests, historical verdicts or append-only
findings ledger. Return the release path and installation handoff instructions.
Close upstream #164/#165 only when their criteria are supported by evidence.
Leave #161 and parent #143 open until the downstream worker verifies the
release in all three pilot installations, performs sanctioned migrations and
pin checks, reruns the historical 96 findings with reviewed results, and
completes the remaining handoff criteria. No acceptance criteria are waived.

## Available downstream evidence

Directory:
`/home/goya/storage/full-ligature-port-workspace/date-creusot/analysis/verification/closure-164-165-2026-10-17/`

- `baseline-replay/`: 96 raw 1.4.0 command captures and results.
- `baseline-nix-retry/`: all 15 Nix-dependent commands retried with daemon
  access. Fresh scratch proof runs report `Proved (93 files)`; differential
  testing reports 143 passed. Some historical commands still reference
  obsolete fixtures or suppress proof output through grep.
- `rollback-results.json`: all three pilots restored to verified 1.4.0,
  including their exact original installation metadata and managed resources.
- `restored-1.4.0-*.stdout`: post-restoration pilot checks.
- The live date-creusot G14 covers exactly nine obligations including
  YearMonthDay.C007; R1/G16 reports 11 checked, zero unresolved and complete
  reconciliation. Overall check has two existing write-set findings for
  `.gitignore` and `PORT-GAPS.md`; do not misreport it as passing.

A previous worker prematurely prepared an experimental source branch and
candidate before the user chose to retain the black-box restriction. That
candidate was withdrawn and the pilots restored. The isolated work was moved
out of the port workspace to
`/tmp/ligature-164-165-quarantined-source-work/ligature`, branch
`fix/164-165-provenance-fixtures`, commit
`df59e6b79ed70e8f830595f303ad887a97b60fd2`. It is optional, unapproved reference
material for the upstream owner, not a shipped fix or authorization to reuse
it without review. The original upstream checkout was not changed. Treat
any 1.4.1 candidate logs in the evidence directory as withdrawn experiments,
not completion of #161 or authority to close the issues.
