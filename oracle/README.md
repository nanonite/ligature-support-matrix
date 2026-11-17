# leveldb-three-verifiers native oracle

Setup record only (Chainlink #177). No native build or source checkout exists
in this root yet.

## Oracle identity

LevelDB 1.23 native storage-format oracle

Dependencies pinned by `SOURCE-PIN.json`:

- native db/log_test.cc and table/table_test.cc at the pinned commit
- a native wrapper over the selected modules with an in-memory Env/handler

## Comparison plan

Compare append/read/replay and block-build/seek traces, including short writes, truncation, checksum failures and malformed batches. Preserve partial handler effects on corruption; compression is disabled for this slice.

## Layout (planned)

- `oracle/cases/` — versioned JSONL cases/expectations (worker-authored).
- `oracle/rust-check/` — Rust harness that calls the native oracle
  (its `Cargo.toml`/`Cargo.lock` are protected; operator/sanctioned creation).
- `oracle/driver/` — native driver sources.
- Task-specific native build root: `/tmp/p4-<issue>-leveldb-three-verifiers/oracle`.
  Never build inside this repository.

Read `oracle-PROTOCOL.md` before writing any case, driver or Rust test
generator. Native agreement falsifies discrepancies; it does not replace a
proof, and it does not establish parity for excluded behaviour.
