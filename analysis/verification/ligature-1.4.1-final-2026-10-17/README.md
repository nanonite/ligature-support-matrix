# Ligature 1.4.1 final port verification — 2026-10-17

This record covers the final attested 1.4.1 artifact. It supersedes earlier withdrawn candidate-install audits under `closure-164-165-2026-10-17/`, which recorded a different adjudicator hash.

## Release identity

- Version: 1.4.1
- Source commit: `742cb253e0cb9753c7a34a0c32559936130e03ab` (clean at build)
- Bundle SHA-256: `973b883b3f4d19e60950ce6b9f0247828459d60fadd05f0d6e29d17d19c31ab8`
- Adjudicator/content hash: `sha256:2f975350565f3dfb09682d69b34ed137ae1dc6342decb7cf9c986ed56a7d733a`
- `RELEASE-SHA256SUMS` verifies the copied release artifact; embedded `version --verify` and `SHA256SUMS` passed in all three pilot-local bundles.

## Pilot installations

Each pilot had its own Ligature installation. Before installation, the original `tools/ligature/` directory was backed up under `analysis/verification/final-1.4.1-install-2026-10-17/backups/<pilot>/tools-ligature-before-1.4.1/`.

For date-creusot, crypto-mixed, and swisstable-verus, the sanctioned migration moved product/adjudicator metadata from 1.4.0 / `sha256:6e9072ba...` to 1.4.1 / `sha256:2f975350...`, returning `result=current`, no conflicts, and no required human action. `doctor` reports installation current. Each installation manifest records 1.4.1 and the final adjudicator hash; all 18 managed files per pilot match their recorded hashes.

Raw checksum, version, idempotent migration, and doctor outputs are in `install/<pilot>/`. `verification.json` records machine-readable readback and hash audit results.

## Live date-creusot checks

- `status --json`: product 1.4.1, descriptor `present-valid`, gate integrity `pinned`, installation `current`.
- `gate g14 --json`: exit 0; deductive cluster `date-creusot-core`; 9 provided, 9 evaluated, 9 unique obligations; expected scope `matched`. IDs: Month.C001, Weekday.C001–C003, Year.C001–C002, YearMonthDay.C002 and C007, YearMonthDayLast.C001.
- `gate-r1-g16 --json`: exit 0, accepted; 11 discovered / 11 checked, zero unresolved, zero configuration mismatches, complete interaction reconciliation.
- `validate-work-package ci/manifest/WP-DATE-CREUSOT.json`: exit 0 with two informational findings.
- `check --json`: exit 1 with 2 high write-set findings (`.gitignore`, `PORT-GAPS.md`) and 14 informational findings. G14 and R1 pass independently; no write-set policy was changed.

Raw outputs are stored at this evidence root. `PORT-GAPS.md` remains user-owned and was not edited.

## Historical 96-finding replay

`replay/` contains all 96 per-command stdout/stderr captures and the replay JSON produced by the existing scratch harness. It used the final 1.4.1 bundle SHA above, replayed the exact first 96 finding IDs from the append-only ledger, and passed its same-size/same-mtime reset corruption self-check. All 96 commands ran; none timed out. The inherited `CANDIDATE-*` labels and exit-code comparisons are not final verdicts. There are 39 exit-code differences from the original record, so those raw captures require manual review before classifying the affected findings. Nix commands were included with a 180-second timeout and `/tmp` cache.

The historical first 96 ledger lines still hash to `d4ee406c118c8efa4c72f70cb75805f3c7d50eb545b9edcb6980f1dea7879ebd`; the live ledger remains 102 lines and matches the replay's recorded full-ledger SHA. No finding row was changed by this verification.

A separate attempt to run `crypto-mixed status --json` timed out at 180 seconds. Its 1.4.1 checksum/version verification, migration, managed-resource hash audit, and `doctor` completed successfully. Track that timeout separately; it is not an installation failure. See `crypto-mixed-status-timeout.md`.

## Tracker status

Upstream Ligature #144–#160, #164, and #165 are closed. Upstream #143 and #161 remain open. Project-local date-creusot issues #136–#143 are closed; local #144 remains open for replay review and downstream handoff. Crypto-mixed #134/#135 remain open at the P3/P4 Kani CG3 boundary. No issue was closed based on the `CANDIDATE-*` labels.

## Review update — 2026-10-18

The 96 scratch replays have now been manually reviewed against their captured
outputs. The final disposition overlay is
[`replay/review-1.4.1.md`](replay/review-1.4.1.md), SHA-256
`5e077a8752ccc32bc414cd84691b7c29386fa8cf695f566af549e4ae3344dcf3`. It
contains 96 dispositions and a per-entry review of all 39 exit-code
differences. Counts: 5 REPRODUCES, 47 RESOLVED, 4 PARTIAL, 3 CHANGED, 1
ENVIRONMENT-BLOCKED, 26 NOT-COMPARABLE, 3 SUPERSEDED, and 7 MATCH. The earlier
sentence above describing the captures as awaiting manual review records the
state before this update. The first 96 historical ledger rows and the full
102-row ledger remain unchanged.

The date-creusot findings classified REPRODUCES in scratch are `date-mcp-001`,
`date-mcp-002`, `date-ligature-023`, `date-creusot-043`, and
`date-ligature-099`; their scope and observations are in the overlay. The
current command-specific exit-code contract gap from `date-ligature-023` is
tracked as local upstream issue #147. `date-ligature-004` and `-027` are
NOT-COMPARABLE, not current reproductions.

The 1.4.1 verifier-policy probe for local issue #75 is recorded at
[`verifier-policy-probe-1.4.1.md`](verifier-policy-probe-1.4.1.md), with its
scratch inputs and raw captures in `verifier-policy-probe/`. Issue #75 is
closed after rechecking the closed key set, verifier domain, and `supporting`
field on scratch copies.

Local #144 remains open for downstream follow-up: crypto-mixed #134 is blocked
on current managed-hash validation and protected manifest regeneration
prerequisites; #135 needs a human P4 Verus-versus-degradation decision; the
live crypto-mixed `status --json` timeout is tracked under #145/#146. The
documentation finding from #147 is also open. These are separate from the
completed 96-entry date replay review.

The older `date-creusot-060` replay capture records a CoCoALib fetch 404 from
the shell state at that time. The approved #142 toolchain alignment later
passed `cargo check --locked`, all 9 `cargo test --locked` known-answer tests,
and fresh `cargo creusot` (`Proved (93 files)`, with the `round_trip`
certificate's five Alt-Ergo children proved). A new 2026-10-18 scratch rerun
could not enter Nix: first the default fetcher-lock cache was read-only, then
redirecting `XDG_CACHE_HOME` to `/tmp` exposed denied Nix-daemon socket access.
No proof ran in that rerun. Its exact commands and raw outputs are under
[`fresh-creusot-rerun-2026-10-18/`](fresh-creusot-rerun-2026-10-18/). This
current sandbox access failure is distinct from the older CoCoALib capture and
does not establish the cvc5 URL condition.
