# Chainlink #32: bounded differential oracle

Date: 2026-10-10

## Scope

The port remains owned by Verus. This issue adds a black-box C++ oracle and
runtime Rust comparison tests; it does not add Kani, combine verifier outputs,
change the Ligature descriptor, modify the production Rust modules, or modify
Cargo.toml.

The C++ driver builds from the pinned Abseil checkout at commit
2065f4ded0558c6f89fee67c8e5228feb4eb960e (tag 20260817.0). It uses a strict
JSONL/schema reader and a shared IdentityHash-v1 mapping for u64 keys. Results
record each action result, current size, and key-sorted contents. Capacity,
allocation, pointer/reference stability, traversal order, native hash
algorithms, probe scheduling, and performance are not compared. Key zero has
an explicit excluded case because the Rust table reserves it as NO_HASH.

The case corpus has 14 entries:

- Two translated upstream cases: FlatHashMap.EraseIf and the observable
  contents portion of FlatHashMap.Reserve. The latter's C++ reference
  stability assertion is not compared.
- Three comparable hand-written boundaries: low H1-bit collisions with
  distinct H2 tags; replacement plus clear; and reserve followed by growth.
- One key-zero exclusion, which checks only the protocol's reason and null
  golden placeholder.
- Eight random action sequences from SplitMix64-v1, seed 20261010.

The test map inventories 409 source-declared test forms from the eleven
SwissTable-relevant upstream test files already listed in README.md. Two are
mapped to cases and 407 are marked unmapped. A source-level TYPED_TEST or
TYPED_TEST_P declaration is listed once; its type instantiations are not
expanded into separate upstream runtime names. Most unmapped cases exercise
generic APIs, node storage, allocators/lifetimes, iterator or sanitizer
behavior, architecture-specific SIMD/control-byte internals, or
inlined-vector behavior absent from this specialized map port. The map is a
coverage inventory, not a claim that all 409 declarations or the upstream
242-target CTest baseline have Rust parity.

## Build and deterministic generation

The driver was configured against the checked-out pin with Abseil testing
disabled, so the oracle build did not fetch GoogleTest:

    cmake -S oracle -B /tmp/swisstable-verus-oracle-build -DCMAKE_BUILD_TYPE=Release -DABSL_BUILD_TESTING=OFF
    cmake --build /tmp/swisstable-verus-oracle-build --target oracle_driver -j2

The build completed with:

    [100%] Built target oracle_driver

The C++ executable produced oracle/golden/results.jsonl and
oracle/golden/random-results.jsonl from the two case files. Both outputs were
regenerated to temporary files and compared byte-for-byte with the checked-in
goldens. The random case file and manifest were regenerated with the recorded
seed, then the Rust generator and test map were regenerated; all artifacts
were byte-identical.

The driver rejected a schema-shaped case with an undeclared field before
creating its result file. Reversing the valid case input order still produced
case-ID-sorted output.

Reproducibility hashes:

    cases.jsonl: 051a69e5bf7c93aad5cc22e7421b088967eeb2c652a71381e412bc0b3a592d53
    random-cases.jsonl: a346f14d26b5601239f7b1f0082ee798743d12702d729234f48b5b16dd1f472f
    random manifest: a56f3e4964e2ae8b6743e907baf8c2ed49833323461fca001dc13473fe76892f
    static golden: 6f522bb6a00930aae9b04862203882bb4e6d20d944f48a5e4b1f95ddf1dcfac2
    random golden: f14c94cb19a1de48bc0c585e501563b13842924476f329885f789835088fa070
    test map: 8d4cb524fa432680c394d82375d666b0ac6211f20185389627a9efa201fcf3b7

## Runtime result

Command:

    cd rust/swisstable-verus-core
    cargo nextest run --locked --profile ci --config-file ../../oracle/nextest.toml

Actual output:

    Starting 14 tests across 2 binaries
    Summary [   0.012s] 14 tests run: 14 passed, 0 skipped

The configured nonempty JUnit report is
rust/swisstable-verus-core/target/nextest/ci/junit.xml (3006 bytes; 14 tests,
0 failures, 0 errors; nextest run ID
88b44edc-4593-4630-bde5-657256c17b8c). Every test reads its case and C++ golden at runtime,
replays the actions through SwissTable, and compares the complete canonical
result object. The C++ goldens sort their results by case ID and normalize
entries by key.

No mismatch occurred, so the rdb divergence workflow was not invoked. There
was no divergence finding to minimize or debug. The pilot write-set check for
issue 32 exited 0 with state clean and no violations; it separately reported
the pre-existing protected drafts and Cargo manifest as audit-only/unvouched.
No issue-32 write touched those paths or the workspace flake files.

## Evidence and limits

Fourteen nextest passes mean parity only for the two mapped source tests and
the observable operations represented in these cases. The 407 unmapped
source-declared tests remain explicit coverage gaps. In particular, these
results do not establish full Abseil suite parity, generic key/value or
allocator parity, pointer/reference stability, exact group/control-byte
behavior, iterator ordering, or performance parity.
