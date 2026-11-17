# tinyxml2-creusot-kani — TinyXML2 mixed-verifier port (setup record)

**Status: setup only (Chainlink #177, 2026-11-14).** This directory is an
independent Git repository (branch `main`, no commits yet). It is **not** a
complete Ligature workspace: `project-descriptor.json`, `.ligature/`, protected
Cargo manifests/locks, nested toolchain files and an approved Ligature bundle
are operator-managed and do not exist here. No production port, proof or risk
claim is made.

## Assignment

- Plan entry: **M5 TinyXML2**
- Verifiers: creusot, kani
- Upstream: <https://github.com/leethomason/tinyxml2> tag `11.0.0` at commit
  [`9148bdf719e997d1f474be6bcc7943881046dba1`](https://github.com/leethomason/tinyxml2/commit/9148bdf719e997d1f474be6bcc7943881046dba1)
- Intake/native-oracle issue: #183
- Portfolio plan: `../P4-MIXED-PORT-PLAN.md`

### Approved slice

In-memory UTF-8 XML parsing plus an explicit DOM mutation/clone/serialization facade: elements, attributes, text, comments, declarations, CDATA, predefined and numeric character references, and newline/whitespace modes. Preserve the pinned implementation's actual errors and normalization instead of substituting a stricter XML interpretation.

### Ownership hypothesis (freeze after intake)

- **creusot** — Parser progress/recursive structure, DOM parent/sibling/ownership invariants, serialization, UTF32->UTF8 conversion.
- **kani** — Bounded StrPair normalization, entity scanning, length/radix/overflow buffer paths and XMLUtil::GetCharacterRef.

### Candidate real call edges (verify in intake; not yet demonstrated)

- C->K: DOM value access calls StrPair::GetStr / entity processing.
- K->C: XMLUtil::GetCharacterRef calls ConvertUTF32ToUTF8.

### Selected upstream files

- `tinyxml2.cpp`
- `tinyxml2.h`
- `xmltest.cpp`
- `resources/`
- `test/`

### Initial exclusions

- DTD/XSL (outside upstream TinyXML2's stated support)
- claims of complete XML-standard conformance
- raw C++ pointer identity and invalid-pointer traces
- all operating-system file behavior

## Per-verifier roots

| Cargo root | Verifier | Manifest/lock status | Task-specific target | Durable evidence |
|---|---|---|---|---|
| `rust/tinyxml2-creusot/` | creusot | protected / operator-managed | `/tmp/p4-<issue>-tinyxml2-creusot-kani/tinyxml2-creusot/target` | `analysis/verification/<run-id>/tinyxml2-creusot/` |
| `rust/tinyxml2-kani/` | kani | protected / operator-managed | `/tmp/p4-<issue>-tinyxml2-creusot-kani/tinyxml2-kani/target` | `analysis/verification/<run-id>/tinyxml2-kani/` |

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
planning/p4-mixed-2026-10-26/setup/p4-root-smoke-check.sh --probe tinyxml2-creusot-kani
```

## Baseline preservation

`date-creusot/`, `swisstable-verus/` and `crypto-mixed/` remain separate
baseline records. #177 did not modify them.

## Workspace setup record

The shared #177 evidence, toolchain qualification, exact protected-write
enumeration and smoke-check commands are in
`../planning/p4-mixed-2026-10-26/setup/README.md`.
