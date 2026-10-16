# Fresh Creusot 0.14 verification — 2026-10-16

This is the fresh verification record after applying the approved Creusot source pin `553a8b732697ae8b8f2b66a64600b0d39e086f9f`. The previous verifier outputs and Cargo inputs are preserved under `analysis/verifier-history/2026-10-16-creusot-0.12.0-dev/`; they are historical and were not used as evidence for this run.

## Reproducible inputs

- Nix snapshot: `analysis/verification/workspace-root-flake/flake.nix` and `flake.lock`, copied byte-for-byte from the workspace root because that root is not a Git repository.
- Flake hashes: `flake.nix` SHA-256 `7f631c89297f25fcbbef7e860d6c931539e7236142b5dba7cf148459e3d4ab07`; `flake.lock` SHA-256 `a1945f624d7bff521a1742b5cf85b0a94dd44989fcd4c23d29100340cbf45137`.
- The approved Creusot input is `553a8b732697ae8b8f2b66a64600b0d39e086f9f`; the root nixpkgs input remains `b77b3de8775677f84492abe84635f87b0e153f0f`. The Creusot revision updates the solver environment to CVC5 1.4.1 and removes the broken CoCoALib patch-fetch path.
- `rust/date-creusot-core/Cargo.toml` now requires `creusot-std = "0.14.0-dev"`; `.cargo/config.toml` patches to the `creusot-std` in the matching Nix store output, and the tracked `creusot` link points to that output's `share` directory.
- Cargo.lock SHA-256 after resolution: `72aa7f4bccd37da533e8c94e1ca77b825f3dbadee3b3ca2f540427afe3932629`.

## Commands and results

Run from `rust/date-creusot-core/`:

```sh
nix develop --no-write-lock-file path:../../analysis/verification/workspace-root-flake#date-creusot -c cargo check --locked
nix develop --no-write-lock-file path:../../analysis/verification/workspace-root-flake#date-creusot -c cargo test --locked
nix develop --no-write-lock-file path:../../analysis/verification/workspace-root-flake#date-creusot -c cargo creusot --no-cache
```

- `cargo check --locked`: passed.
- `cargo test --locked`: passed, 9 known-answer tests; no unit or doc tests were defined.
- `cargo creusot --no-cache`: exited 0 and reported `Proved (93 files)`. The fresh run has 93 proof JSON files and 202 solver-leaf proof records. The `round_trip` certificate at `rust/date-creusot-core/verif/date_creusot_core_rlib/year_month_day/impl_YearMonthDay/round_trip/proof.json` has SHA-256 `32f58ce2ab4c120403f2c9f03626ecb615cc4375ef97d061733ccfdd94cb6ae2` and `vc_round_trip` with five Alt-Ergo children; all five are proved.
- The proof annotations and contract logic were preserved. The Rust source change for C2/C007 updates comments only; no semantic weakening was needed or made.
- The selected solver change is an accepted environment update, not a change to the proof claims. The recorded fresh `vc_round_trip` children use Alt-Ergo; CVC5 is available in the pinned shell but was not used by those proof obligations. `cargo creusot version` identified cargo-creusot 0.14.0-dev, Why3 1.8.2, Alt-Ergo 2.6.2, and CVC5 1.4.1; its version display labeled CVC5 `bad` while also naming 1.4.1 as the recommended version. The successful proof run and the proof JSON provide the observed verification result.
- The final live R1/G16 report is `analysis/verification/r1-g16-ligature-1.3.12-2026-10-16.json`: exit 0, 11 discovered / 11 checked, 0 unresolved, 0 blocking configuration mismatches. The live G14 report is `analysis/verification/g14-ligature-1.3.12-2026-10-16.json`: exit 1, 5 provided/evaluated IDs, expected scope mismatch against the reviewed nine IDs. `analysis/verification/check-ligature-1.3.12-2026-10-16.json` preserves the consolidated check output.
- The cache-disabled proof command printed source-location warnings for some Rust standard-library files that are not present at the compiler's recorded `/rustc/...` paths; Creusot nevertheless exited 0 and reported all 93 files proved.

## Scope limitation

The source-level `round_trip` contract is freshly proved here. This record does not claim that G14 consumed it. Ligature 1.3.12's Stage 7 generator resolves a provided obligation's assurance requirements only from interaction `reliances[]`. C007 is a standalone result contract for `YearMonthDay.round_trip`, not a callee guarantee in an existing interaction; adding it to an unrelated callee reliance or fabricating a caller edge would misstate the contract. The promotion receipt now hash-binds all 40 accepted artifacts, including the five reviewed concept specs. The exact nine-obligation closure is pinned and reviewed through `draft`/`approve`; its current hash also has a ratified `record-ruling` entry. The approved IDs are `Weekday.C001`, `Weekday.C002`, `Weekday.C003`, `YearMonthDay.C002` (`from_days`), `YearMonthDay.C007` (`round_trip`), `YearMonthDayLast.C001`, `Year.C001`, `Year.C002`, and `Month.C001`.

The live `gate-g14 --json` exits 1 because the existing generated manifest still declares five legacy IDs (`Weekday.C1/C2/C3`, `YearMonthDay.C2`, and `YearMonthDayLast.C1`), which do not match the approved nine-ID pin. The exact nine-ID Stage 7 plan exits 2 with `missing-source: no interaction reliance declares required_assurance for obligation 'YearMonthDay.C007'`; it writes no manifest. The old report path therefore remains in place.
The current receipt SHA-256 is `2d03fe3040664772fa895b0e2d317445d74a789ee5442c6696400a46afc1677f`, while the existing manifest still records `sha256:891099b32cb08bd2ac6bf8137cc019a7c3f6fffaec786618aedf1ef0ba9511b7` in `provenance.artifact_set_hash`. The manifest was not changed because Stage 7 refuses in-place regeneration when output bytes differ (`date-ligature-103`).

A disposable Stage 7 probe that omitted C007 was able to generate a manifest with the canonical `ci/results/WP-DATE-CREUSOT.json` path, but `record-assurance` then exited 1 at `Month.C001`: the accepted interaction requirement carries `minimum_scope.input_domain`, while the Creusot record contains only `proof_targets` and has no `evidence.scope.input_domain`. Ligature refused to copy the requirement into achieved evidence. No report was written. This is recorded as `date-creusot-064`; do not remove the accepted scope or hand-write a report to bypass it. Ligature 1.3.12 also refuses to regenerate an existing manifest when the derived bytes differ (`date-ligature-103`), so the live output path could not be updated. G14 must remain blocked until the generated manifest and assurance-intake gaps are resolved upstream.
