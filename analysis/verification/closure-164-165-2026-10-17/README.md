# Upstream closure evidence — 2026-10-17

**Final status: upstream delegation required.** The user explicitly retained
the black-box restriction. All three pilots have been restored to the exact
verified 1.4.0 bundles, installation metadata and managed resources saved
before the experimental candidate installation. The live assurance and
feature-ledger reports also match the original baseline. See
`rollback-results.json`, `final-preserved-inputs.json` and the restored gate
captures. No upstream issue was closed or upstream checkout changed.

Use `upstream-delegation-prompt.md` for the upstream owner. All 1.4.1 logs,
source test results and installation audits in this directory describe a
**withdrawn experiment**, not the installed version or completed acceptance.
The candidate replay was stopped before completion. Experimental source work
was moved out of this workspace to
`/tmp/ligature-164-165-quarantined-source-work/ligature` for optional upstream
review; it must not be treated as approved or shipped.

Work requested: resolve Ligature #164 (regeneration provenance) and #165
(standalone assurance integration fixtures), then satisfy #161/#143 replay
and downstream handoff criteria without waiving unfinished work.

Tracker identities matter: these are upstream Ligature issue numbers. In the
port-workspace tracker, #143 is the already-closed Codesight investigation;
#161/#164/#165 do not exist here. Local #144 tracks this verification effort.
Do not close or reopen local #143 to represent upstream progress.

## Baseline

Installed version: Ligature 1.4.0, source commit
`38e23b4188728abf19ec29e67ff6341c9daf8d8a`, bundle SHA-256
`1f04052e4fea0441bc807c4caf2c80ecad4d70b7f9f101665185eae7aa46dc9e`.

Captured command output is in `baseline-*.stdout` and `baseline-*.stderr`:

- `version --verify`: exit 0, attested executable.
- `status --json`: exit 0.
- `gate g14 --json`: exit 0, nine evaluated obligations.
- `gate-r1-g16 --json`: exit 0, 11 discovered/checked, zero unresolved,
  zero configuration mismatches, complete interaction reconciliation.
- `validate-work-package ci/manifest/WP-DATE-CREUSOT.json`: exit 0.
- `doctor`: exit 0, current installation and pinned adjudicator.
- `check --json`: exit 1; high findings are the existing `.gitignore` and
  `PORT-GAPS.md` write-set findings. Passing individual gates does not mean
  this overall command passed.

`baseline-hashes.json` records pre-work hashes of the root flake files, live
descriptor, append-only findings ledger, and protected work-package manifest.

The earlier 1.4.0 verification report now qualifies its regeneration claim:
a successful sanctioned update does not prove edited input is refused.

## Replay scope

The 96 IDs in the previous 1.3.12 replay match the first 96 current ledger
records exactly, ending with `date-creusot-062`. The current ledger has 102
records. The historical 96 form the required replay set; the six subsequent
records need separate accounting rather than silently changing that set.

Baseline scratch root: `/tmp/ligature-closure-164-165-baseline-1.4.0`.
Each command runs after a fresh reset through the existing `reverify.py`
harness, with `--slow` to attempt Nix commands as well. The command timeout
for this run is 90 seconds. Known repairs performed by the harness are
recorded in each capture. No descriptor normalization is requested because
the live descriptor no longer contains the historical docs overlap.

The baseline pass completed all 96 attempts with no command timeout. Results
and all 96 raw stdout/stderr captures are archived in `baseline-replay/`;
`baseline-replay/SHA256SUMS` covers those files. Fifteen Nix-dependent commands
initially stopped at the sandbox cache/daemon boundary, so their baseline
outputs cannot adjudicate the historical proof findings.

A separate Nix preflight with `XDG_CACHE_HOME=/tmp/ligature-closure-nix-cache`
and daemon-access escalation exited 0. Its output is saved as
`nix-preflight.stdout` and `nix-preflight.stderr`. The 15 Nix-dependent entries
are being retried in `/tmp/ligature-closure-164-165-nix-1.4.0` with a 180-second
command timeout and the same existing harness. These supplemental captures
must be retained alongside the original sandbox failures.

The three downstream bundles all verify as the same 1.4.0 artifact.
date-creusot and swisstable-verus status/doctor checks exit 0. crypto-mixed's
status check timed out at 60 seconds; its doctor check was not run in that
baseline batch. See `downstream-baseline-results.json`. This is a baseline
inventory, not installation of a corrected release.

Candidate labels from the harness are search aids, not reviewed verdicts.
A command failing because an old fixture or tool is unavailable does not
prove the original defect remains. The baseline run is not verification of
any future provenance fix.

## Remaining closure requirements

- Read the upstream issues and their complete acceptance criteria in the
  correct tracker (completed; local and upstream numbers are distinct).
- Reject regeneration when the existing manifest does not match trusted
  prior generation provenance for its package and canonical path. Cover
  edited manifests, missing provenance, valid regeneration, refusal
  preservation, and grant reuse with regression tests.
- Repair the three standalone-assurance fixtures through supported reviewed
  source intake; retain a negative test for absent reviewed source.
- Build and attest the corrected release, perform the required replay with
  reviewed verdicts, and preserve raw captures and release identity.
- Install and verify the corrected bundle in the downstream pilots through
  the supported managed upgrade route; record actual command results.
- Update the upstream tracker with evidence and close only satisfied issues.

WORKER-CONTRACT.md defines the pilot as black-box work. The user explicitly
confirmed that restriction and requested an upstream delegation prompt.
Source work is reserved for the upstream owner. The original upstream
checkout remains unchanged; no source changes are installed in the pilots.
