# snappy-verus-kani native oracle

Setup record only (Chainlink #177). No native build or source checkout exists
in this root yet.

## Oracle identity

Snappy 1.2.2 native oracle

Dependencies pinned by `SOURCE-PIN.json`:

- native snappy_unittests and shipped corrupted-input tests at the pinned commit
- shipped testdata/ corpus at the pinned commit

## Comparison plan

Cross-decode native and Rust streams; compare decoded bytes, lengths and error outcomes. Compressed bytes are not required to be identical because the raw format has no canonical encoding.

## Layout (planned)

- `oracle/cases/` — versioned JSONL cases/expectations (worker-authored).
- `oracle/rust-check/` — Rust harness that calls the native oracle
  (its `Cargo.toml`/`Cargo.lock` are protected; operator/sanctioned creation).
- `oracle/driver/` — native driver sources.
- Task-specific native build root: `/tmp/p4-<issue>-snappy-verus-kani/oracle`.
  Never build inside this repository.

Read `oracle-PROTOCOL.md` before writing any case, driver or Rust test
generator. Native agreement falsifies discrepancies; it does not replace a
proof, and it does not establish parity for excluded behaviour.
