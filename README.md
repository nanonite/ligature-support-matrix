# leveldb-three-verifiers — LevelDB storage slice mixed-verifier port (setup record)

**Status: setup only (Chainlink #177, 2026-11-14).** This directory is an
independent Git repository (branch `main`, no commits yet). It is **not** a
complete Ligature workspace: `project-descriptor.json`, `.ligature/`, protected
Cargo manifests/locks, nested toolchain files and an approved Ligature bundle
are operator-managed and do not exist here. No production port, proof or risk
claim is made.

## Assignment

- Plan entry: **M7 LevelDB storage slice**
- Verifiers: creusot, verus, kani
- Upstream: <https://github.com/google/leveldb> tag `1.23` at commit
  [`99b3c03b3284f5886f9ef9a4ef703d57373e61be`](https://github.com/google/leveldb/commit/99b3c03b3284f5886f9ef9a4ef703d57373e61be)
- Intake/native-oracle issue: #191
- Portfolio plan: `../P4-MIXED-PORT-PLAN.md`

### Approved slice

A joined in-memory storage-format pipeline: WriteBatch Put/Delete and parsing/handler effects, log writer/reader fragmentation/checksum/truncation/error handling, prefix-compressed block builder/reader and restart seek/iteration, plus replay into a specified logical map. This is not a whole-database port.

### Ownership hypothesis (freeze after intake)

- **creusot** — Ordered-map/operation-history semantics, handler/replay state.
- **verus** — Prefix-compressed block representation, restart/seek/iteration, log framing/reassembly and parser progress.
- **kani** — Bounded fixed/varint codecs, CRC32C arithmetic/masking, and local buffer/fault cases.

### Candidate real call edges (verify in intake; not yet demonstrated)

- Creusot batch/replay orchestration consumes Verus-checked parsing/framing contracts.
- Verus log/block parsing calls Kani-owned coding/CRC helpers.
- WriteBatch::Iterate dispatches Creusot-owned Handler Put/Delete semantics.
- These are assignment hypotheses; intake must record exact real sites and reject disconnected three-demo designs.

### Selected upstream files

- `db/write_batch.cc`
- `db/log_writer.cc`
- `db/log_reader.cc`
- `db/log_test.cc`
- `table/block_builder.cc`
- `table/block.cc`
- `table/table_test.cc`
- `util/coding.cc`
- `util/crc32c.cc`
- `doc/log_format.md`
- `doc/table_format.md`

### Initial exclusions

- full DB API
- compaction scheduling, concurrent writers, filesystem durability
- real crash consistency, snapshots, and all platform Env implementations
- treating Flush as Sync or bounded in-memory faults as OS persistence

## Per-verifier roots

| Cargo root | Verifier | Manifest/lock status | Task-specific target | Durable evidence |
|---|---|---|---|---|
| `rust/leveldb-creusot/` | creusot | protected / operator-managed | `/tmp/p4-<issue>-leveldb-three-verifiers/leveldb-creusot/target` | `analysis/verification/<run-id>/leveldb-creusot/` |
| `rust/leveldb-verus/` | verus | protected / operator-managed | `/tmp/p4-<issue>-leveldb-three-verifiers/leveldb-verus/target` | `analysis/verification/<run-id>/leveldb-verus/` |
| `rust/leveldb-kani/` | kani | protected / operator-managed | `/tmp/p4-<issue>-leveldb-three-verifiers/leveldb-kani/target` | `analysis/verification/<run-id>/leveldb-kani/` |

No shared executable source, Cargo workspace, lock or proof output exists yet.
Sharing executable code between verifiers requires declared ownership, revision
and proof/TCB impact (operator decision recorded at #161).

## Toolchain pins

- **Creusot** (where listed): `cargo-creusot 0.12.0-dev` + `creusot-std
  0.12.0-dev` wrapper `/nix/store/9y9g4kpsppxn6zqmyfkvfcc2234qkdwv-creusot-wrapped`,
  Rust `nightly-2026-04-21`. This is the operator-selected P4 pair. The workspace
  flake's declared shell currently resolves Creusot `0.14.0-dev`; that mismatch
  remains the separate epic #2 finding and is **not** validated here.
- **Verus** (where listed): `0.2026.05.24.ecee80a`, Rust `1.95.0`.
- **Kani** (where listed): `cargo-kani 0.67.0`, CBMC 6.8.0, Rust `1.95.0`.

Tools are resolved through Nix or the existing user-level rustup/Cargo setup;
nothing was installed outside Nix by #177.

## Worker write set (proposed, not yet a descriptor policy)

Allowed for worker-authored content: `README.md`, `SOURCE-PIN.json`,
`PORT-GAPS.md`, `findings/**`, `oracle/**`, `analysis/**`,
`rust/*/src/**`, `rust/*/tests/**`, `rust/*/verif/**`, `.gitignore`.

Operator-managed / requiring an exact issue+path grant: `project-descriptor.json`,
`.ligature/**`, `schemas/**`, `tools/ligature/**`, `rust/*/Cargo.toml`,
`rust/*/Cargo.lock`, `rust/*/rust-toolchain.toml`, `rust/*/.cargo/config.toml`,
`rust/*/build.rs`, `rust/*/specs/**`, `ci/**`, `scripts/**`, `tests/harnesses/**`,
`.envrc`, `.mcp.json`, `.github/**`, and outer-repository submodule registration.

See `analysis/setup/SETUP.md` for the exact path-by-path creation routes.

## Oracle

`oracle/README.md` records the native dependencies and comparison plan;
`oracle/oracle-PROTOCOL.md` is the workspace differential-testing protocol.
Native builds use task-specific `/tmp` roots, never the repository.

## Smoke check

From the workspace root:

```bash
planning/p4-mixed-2026-10-26/setup/p4-root-smoke-check.sh --probe leveldb-three-verifiers
```

## Baseline preservation

`date-creusot/`, `swisstable-verus/` and `crypto-mixed/` remain separate
baseline records. #177 did not modify them.

## Workspace setup record

The shared #177 evidence, toolchain qualification, exact protected-write
enumeration and smoke-check commands are in
`../planning/p4-mixed-2026-10-26/setup/README.md`.
