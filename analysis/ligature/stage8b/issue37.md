# Chainlink #37: C.10 iteration/reference exclusion and shared hash input

Date: 2026-10-10

## Scope and result

The C++ oracle uses `IdentityHash-v1(key) == key`; the Rust replay supplies that same raw `u64` as its hash input. This is a shared input mapping, not a claim that Abseil and the Rust table share their internal hash mixing, seeds, control-byte layout, or slot placement. `E-011`'s implementation precondition is exercised by the oracle, while its evidence record remains `lifecycle: deferred` pending operator review.

The oracle compares action results, sizes, and logical key/value contents after sorting by key. It does not compare iteration order or pointer/reference identity or stability. The pinned Abseil source documents that `PerTableSeed` randomizes iteration order (`raw_hash_set.h:597-599`) and that `flat_hash_map` invalidates pointers/references on rehash and move (`flat_hash_map.h:69-70,108-114,482-483`). The Rust port does not provide an equivalent C++ reference-stability contract. These properties remain explicit scope exclusions under C.10 / EC-1.

No Kani scope, mixed-verifier cluster, descriptor, production Rust module, Cargo manifest, or workspace flake file changed.

## Oracle changes

- Added `boundary-map-sequence-reversed-insert-0001`, inserting keys in order 9, 2, 17, 5 and then reserving. The C++ golden emits entries in canonical key order: `[[2,20],[5,50],[9,90],[17,170]]`.
- Added `boundary-map-sequence-iteration-pointer-excluded-0001` with an explicit C.10 exclusion reason. The C++ golden is the protocol placeholder `{"case_id":"boundary-map-sequence-iteration-pointer-excluded-0001","status":"ok","value":null}`; the Rust test validates the exclusion metadata and does not compare behavior.
- Regenerated the static C++ golden and Rust tests. The case suite now has 16 cases total (14 comparable and 2 excluded). The test-map remains a source-declaration inventory: 2 of 409 upstream test forms are mapped; 407 remain unmapped.
- Added finding `swisstable-verus-036` and the matching ruled-scope-cut entry in `PORT-GAPS.md`.

## Commands and results

Build the pinned C++ driver:

    cmake --build /tmp/swisstable-verus-oracle-build --target oracle_driver -j2
    [100%] Built target oracle_driver

Regenerate both result streams (both commands exited 0):

    /tmp/swisstable-verus-oracle-build/oracle_driver oracle/cases.jsonl oracle/golden/results.jsonl
    /tmp/swisstable-verus-oracle-build/oracle_driver oracle/random-cases.jsonl oracle/golden/random-results.jsonl

Regenerate Rust checks:

    python3 oracle/generate_oracle_tests.py
    generated 16 nextest cases; mapped 2 of 409 upstream tests

Run the Rust side:

    cd rust/swisstable-verus-core
    cargo nextest run --locked --profile ci --config-file ../../oracle/nextest.toml
    Summary [   0.017s] 16 tests run: 16 passed, 0 skipped

JUnit: `rust/swisstable-verus-core/target/nextest/ci/junit.xml` — 16 testcases, 0 failures, 0 errors. Nextest run ID: `bfec0b55-807a-410e-8c5a-b57ef1713ee1`.

No differential mismatch occurred, so the rdb divergence workflow was not invoked. The 16 passes establish only the mapped observable operation slice; they do not establish iterator-order or pointer/reference stability parity.

## Reproducibility hashes

- `oracle/cases.jsonl`: `5762d4d2b81b42ea1a2c5e7af36c84a60ed942678b47c8c6b1474a94f5be8690`
- `oracle/golden/results.jsonl`: `1de9d261c32f39be4166a2990dd956ebff5c537aa6735132f6551817b838b175`
- `rust/swisstable-verus-core/tests/generated_cases.rs`: `460832ad37eb0e2ab8eefc0282a139bf74b44469a668170d0cae3f407f69739b`


## Scope check

Command:

    python3 tools/ligature/ligature.pyz write-set-check --issue 37 --json
    {"state":"clean","violations":[]}

The check returned exit 0. It listed the existing protected-unvouched Cargo manifest and staged draft artifacts as audit-only; none was edited for #37. The changed files are within the pilot's allowed `analysis/**`, `findings/**`, `oracle/**`, `rust/*/tests/`, `README.md`, and `PORT-GAPS.md` roots. No Kani cluster, verifier selection, or descriptor change was made. The workspace `flake.nix` and `flake.lock`, the pilot descriptor, Cargo manifest, and production Rust source have mtimes dated before this #37 run and were not targeted by any command.
