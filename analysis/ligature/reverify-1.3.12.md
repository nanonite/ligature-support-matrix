# Ligature 1.3.12 re-verification addendum

Date: 2026-10-16

This addendum records the post-release P1 verification without replacing the historical 1.2.0/1.3.11 measurements in `reverify-VERDICTS.md` and without changing the append-only `findings/limitations.jsonl` ledger.

## Release and installation

- Ligature: `1.3.12`
- Attested source commit: `34fb1a1372bd69e38a92f1468db6c4245a609518` (clean at build)
- Bundle SHA-256: `87ca4814b39def8f7f236f6c6a9be554992425112c339e22f0521e56c2e35028`
- Embedded content hash: `sha256:d6faedb62a7cc325b3373f3f3efdd52f7938c4b85a57359937c9dd5a56013a59`

The exact release bundle was copied to the three distinct pilot installations (`date-creusot`, `crypto-mixed`, and `swisstable-verus`). Each installation passed its `SHA256SUMS` check and `python3 -I tools/ligature/ligature.pyz version --verify`. `migrate --upgrade --json` returned `result=current`, no conflicts, and no required human action for all three. The 18 managed-resource hashes per pilot match. Product and adjudicator versions are `1.3.12`; each `@adjudicator` gate pin equals the attested content hash. User-owned descriptors and policies were not changed.

Installation-current does not mean descriptor-valid. The live `date-creusot/project-descriptor.json` still has `docs/*.md` in `allowed_roots`, overlapping protected `docs/reliance-policy.md`. On the live root, Ligature 1.3.12 `check --json` exits 5 with `invalid_input` and `gate_integrity_failed`; the gates are not evaluated. `doctor` exits 2 and names the same descriptor overlap. No live descriptor edit was made.

## 96-finding reruns

The harness replays each finding from a fresh scratch copy and records stdout, stderr, and exit code for every command. Results and all 96 command captures are under:

- Unmodified scratch: `/tmp/ligature-161-unmodified-1.3.12/`
- Scratch with the harness's documented descriptor normalization: `/tmp/ligature-161-normalized-1.3.12/`

Both `results.json` files contain 96 rows and each `out/` directory contains 96 raw captures. The normalized run changed only the scratch descriptor, replacing the overlapping `docs/*.md` allowance with `docs/evidence-promotion-exception.md`; it did not change the live descriptor. The harness's `CANDIDATE-*` labels are single-string probes for manual review, not final verdicts. Any conclusion below is based on captured command output or a focused command, not on those labels.

The historical ledger remains unchanged: `date-creusot/findings/limitations.jsonl` has 96 lines and SHA-256 `d4ee406c118c8efa4c72f70cb75805f3c7d50eb545b9edcb6980f1dea7879ebd`.

## Focused release behavior

### Declared crate roots

On a disposable copy with the docs overlap normalized, setting the declared crate root to `crates/no-such-crate` left the descriptor `present-valid` and gate integrity `pinned`, but `check --json` emitted a high `crate-prerequisite` finding: “declared crate root crates/no-such-crate does not exist or is not a directory; create or scaffold it before running extract-c-static”. An absolute crate root `/etc` was rejected as invalid with a workspace-relative/path-traversal diagnostic. Ligature now identifies a missing crate before recommending extraction. This is not live acceptance and no crate was scaffolded.

### Compile-time evidence and bundled schema inspection

The 1.3.12 evidence schema accepts `kind=compile-time`; a scratch `E-999` record passed `validate-evidence` with `OK: all evidence records pass G1a/G1b (16 discovered)`. The bundled schema explicitly defines this as evidence classification for compiler-enforced assertions or const evaluation. It does not prove that a compiler or verifier ran and is not an assurance-report evidence kind. No assurance result was inferred from it.

`schema show closure-profile` and `schema show degradation-record` both exited 0 and displayed their bundled schema names, versions, hashes, and JSON. The project does not need local copies of these schemas. The Stage 3 boundary prompt now points to `docs/reliance-policy.md`, the policy file initialized in the project.

### G14 scope and `round_trip`

On the normalized scratch workspace, `gate-g14 --json` exited 0 and reported:

- 5 unique, evaluated, provided obligation records;
- 0 required obligations;
- expected obligation scope `unpinned` / `not declared`;
- obligations: `Weekday.C1`, `Weekday.C2`, `Weekday.C3`, `YearMonthDay.C2`, and `YearMonthDayLast.C1`.

The report references and rechecks the five saved proof artifacts. It contains no `round_trip` obligation. No fresh `cargo creusot` run occurred, so the saved proof JSON is not a fresh proof. G14's successful result must not be represented as complete declared coverage while expected scope is unpinned.

### R1/G16 after a C_static refresh

On a separate normalized scratch copy, `extract-c-static --target x86_64-unknown-linux-gnu` exited 0 and reported `11 discovered, 11 resolved, 0 unresolved`. `gate-r1-g16 --json` exited 0 for gate acceptance, but explicitly reports `interaction_reconciliation=incomplete`: 6 of 11 calls checked, 5 undeclared warnings, 0 undeclared blocking calls. The five uncounted calls are:

- `YearMonthDay.ok -> Year.ok`
- `YearMonthDay.ok -> Month.ok`
- `YearMonthDayLast.ok -> Year.ok`
- `YearMonthDayLast.ok -> Month.ok`
- `YearMonthDayLast.day -> Year.is_leap`

The report calls these computed value-domain inquiries, but also says they remain drift and are not counted as checked against interactions. This is scratch evidence only; the live R1/G16 gate remains unevaluated until the descriptor decision is resolved.

### Shared feature-ledger and assurance-report path

On scratch, `report feature-ledger` exits 1 and refuses to overwrite the assurance report at `ci/results/feature_ledger.json`. It names the safe command order (run `record-assurance` last) or a distinct report path. The distinct path would change protected `ci/manifest/**`; no manifest edit was made. The operator must decide whether the feature-ledger projection is ephemeral or should be retained as a separate artifact.

### Constraint references

The normalized `check --json` still reports six G2+ `applies_to unverifiable` findings. The descriptor declares `specs_search_root=rust`, but the crate has no promoted concept-to-code specs under its `specs/` root. Ligature 1.3.12 names the missing concept specs and documents the supported `draft 3 concept-to-code` then human `approve` workflow; it will not infer constraint IDs. `analysis/ligature/constraint-ids.json` remains a pilot declaration, not gate evidence. No specs were staged or promoted.

### Codesight and Creusot tools

Codesight was reindexed independently from a scratch copy of the pinned upstream commit; this avoids treating the earlier `stale:true` index as a current result. `index-folder` succeeded with 122 files and 416 symbols. `get-file-outline` still reports `include/date/date.h` as language `c` with 7 symbols; `get-callers` for `days_from_civil` exits 1 with `Symbol not found`; `get-imports` for importers of `date.h` exits 0 with `result_count: 0`. These are parser/index limits, not evidence that callers or importers are absent.

The pinned Nix check stops before a fetch: `nix-store --realise /nix/store/5hh2pd1xlrnxf1dllb87pci3mw3bi69i-cvc5-1.3.1.drv` exits 1 with `cannot connect to socket at '/nix/var/nix/daemon-socket/socket': Operation not permitted`. The CoCoALib patch URL 404 was not rechecked. No fresh Creusot proof or build/emission verification was possible; no flake or lockfile change was made.

## Scope and repository provenance

The explicit port subset is already documented in `rust/date-creusot-core/src/lib.rs` and `PORT-GAPS.md`; it does not claim a complete Howard Hinnant/date replacement. The nested `upstream/date` Git repository is present, clean, and at `179a6b921ccd6179b5b04dce812a89f71a51b4df`. The workspace root is not a Git repository; it remains uninitialized.

## Project-local follow-up

After the release and both harness passes, project-local issues #136–#143 were filed under P1 epic #9. #143, the Codesight fresh-index investigation, is closed with the output above. #136–#142 remain open for operator decisions, approved artifact work, or the Nix environment dependency. These are not new Ligature defects. The main findings ledger and historical 1.2.0/1.3.11 measurements remain unchanged.

## Write-set check for this addendum

The live `write-set-check --json` cannot run while the live descriptor has the `docs/*.md` / `docs/reliance-policy.md` overlap. In a disposable copy with only that documented overlap normalization, `write-set-check --json` reports one pre-existing out-of-set path, `PORT-GAPS.md`; it does not report `analysis/ligature/reverify-1.3.12.md`, which is under the descriptor's existing `analysis/**` allowance. This scratch result does not make the pre-existing `PORT-GAPS.md` write authorized or the live workspace clean.
