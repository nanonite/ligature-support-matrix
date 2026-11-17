# icl-creusot-verus — Boost.ICL mixed-verifier port (setup record)

**Status: setup only (Chainlink #177, 2026-11-14).** This directory is an
independent Git repository (branch `main`, no commits yet). It is **not** a
complete Ligature workspace: `project-descriptor.json`, `.ligature/`, protected
Cargo manifests/locks, nested toolchain files and an approved Ligature bundle
are operator-managed and do not exist here. No production port, proof or risk
claim is made.

## Assignment

- Plan entry: **M4 Boost.ICL**
- Verifiers: creusot, verus
- Upstream: <https://github.com/boostorg/icl> tag `boost-1.88.0` at commit
  [`2741c3a1b7b79f7326360c26c3e1588b385c9e53`](https://github.com/boostorg/icl/commit/2741c3a1b7b79f7326360c26c3e1588b385c9e53)
- Intake/native-oracle issue: #179
- Portfolio plan: `../P4-MIXED-PORT-PLAN.md`

### Approved slice

Discrete interval algebra and canonical interval sets/maps: empty, singleton, open and closed endpoints; union, intersection and difference; insertion and erasure; split/coalesce; membership and segment iteration. Initial concrete endpoint types i32 and i64 plus one explicit additive integer map codomain. Generic endpoint/combiner law obligations must be attempted; one scalar instantiation is not a port of the C++ templates.

### Ownership hypothesis (freeze after intake)

- **creusot** — Endpoint/order/interval algebra and high-level set operations.
- **verus** — Canonical segment storage, mutation, split/coalesce, and representation/iterator invariants.

### Candidate real call edges (verify in intake; not yet demonstrated)

- C->V: interval_base_set::add calls _add; interval_set delegates to segment mutation.
- V->C: _add consults icl::is_empty; mutation uses left_subtract/right_subtract and endpoint algebra.

### Selected upstream files

- `include/boost/icl/interval_base_set.hpp`
- `include/boost/icl/interval_set.hpp`
- `include/boost/icl/interval_map.hpp`
- `include/boost/icl/concept/interval.hpp`

### Initial exclusions

- All of Boost outside the selected ICL slice
- continuous/floating endpoint semantics
- arbitrary allocator/comparator/codomain policies
- pointer/iterator address identity and performance parity

## Per-verifier roots

| Cargo root | Verifier | Manifest/lock status | Task-specific target | Durable evidence |
|---|---|---|---|---|
| `rust/icl-creusot/` | creusot | protected / operator-managed | `/tmp/p4-<issue>-icl-creusot-verus/icl-creusot/target` | `analysis/verification/<run-id>/icl-creusot/` |
| `rust/icl-verus/` | verus | protected / operator-managed | `/tmp/p4-<issue>-icl-creusot-verus/icl-verus/target` | `analysis/verification/<run-id>/icl-verus/` |

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
planning/p4-mixed-2026-10-26/setup/p4-root-smoke-check.sh --probe icl-creusot-verus
```

## Baseline preservation

`date-creusot/`, `swisstable-verus/` and `crypto-mixed/` remain separate
baseline records. #177 did not modify them.

## Workspace setup record

The shared #177 evidence, toolchain qualification, exact protected-write
enumeration and smoke-check commands are in
`../planning/p4-mixed-2026-10-26/setup/README.md`.
