# snappy-verus-kani — Snappy mixed-verifier port (setup record)

**Status: setup only (Chainlink #177, 2026-11-14).** This directory is an
independent Git repository (branch `main`, no commits yet). It is **not** a
complete Ligature workspace: `project-descriptor.json`, `.ligature/`, protected
Cargo manifests/locks, nested toolchain files and an approved Ligature bundle
are operator-managed and do not exist here. No production port, proof or risk
claim is made.

## Assignment

- Plan entry: **M6 Snappy**
- Verifiers: verus, kani
- Upstream: <https://github.com/google/snappy> tag `1.2.2` at commit
  [`6af9287fbdb913f0794d0148c6aa43b58e63c8e3`](https://github.com/google/snappy/commit/6af9287fbdb913f0794d0148c6aa43b58e63c8e3)
- Intake/native-oracle issue: #187
- Portfolio plan: `../P4-MIXED-PORT-PLAN.md`

### Approved slice

Raw Snappy block encode/decode, length/varint/tag parsing, literal and all three copy-tag forms, overlapping backreferences, malformed stream rejection, and at least one real optimized copy/shuffle path from the pinned source attempted under Kani against scalar semantics.

### Ownership hypothesis (freeze after intake)

- **verus** — Tag/decoder state invariants, portable IncrementalCopySlow implementation/model, and reconstruction/round-trip properties over the selected raw format.
- **kani** — Bounded IncrementalCopy optimized paths, vector shuffle/unaligned access, tail/slop conditions, compared against scalar semantics.

### Candidate real call edges (verify in intake; not yet demonstrated)

- V->K: DecompressAllTags / AppendFromSelf dispatches IncrementalCopy.
- K->V: IncrementalCopy falls back to IncrementalCopySlow for tight buffers and tails.

### Selected upstream files

- `snappy.cc`
- `snappy-internal.h`
- `snappy-sinksource.h`
- `snappy_unittest.cc`
- `format_description.txt`
- `testdata/`

### Initial exclusions

- framed/container formats and other codecs
- every architecture/ISA
- throughput parity and unbounded Kani claims
- stubbing an unsupported optimized path and calling it proved

## Per-verifier roots

| Cargo root | Verifier | Manifest/lock status | Task-specific target | Durable evidence |
|---|---|---|---|---|
| `rust/snappy-verus/` | verus | protected / operator-managed | `/tmp/p4-<issue>-snappy-verus-kani/snappy-verus/target` | `analysis/verification/<run-id>/snappy-verus/` |
| `rust/snappy-kani/` | kani | protected / operator-managed | `/tmp/p4-<issue>-snappy-verus-kani/snappy-kani/target` | `analysis/verification/<run-id>/snappy-kani/` |

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
planning/p4-mixed-2026-10-26/setup/p4-root-smoke-check.sh --probe snappy-verus-kani
```

## Baseline preservation

`date-creusot/`, `swisstable-verus/` and `crypto-mixed/` remain separate
baseline records. #177 did not modify them.

## Workspace setup record

The shared #177 evidence, toolchain qualification, exact protected-write
enumeration and smoke-check commands are in
`../planning/p4-mixed-2026-10-26/setup/README.md`.
