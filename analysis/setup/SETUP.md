# leveldb-three-verifiers setup record (Chainlink #177)

> **Status correction (2026-11-14):** The initial inventory below predates
> the operator-directed Ligature 1.4.3 install and `init` in this root. The
> current state is recorded at the end of this file; the pre-init protected
> path inventory is retained as history.

This file records setup decisions only. It creates no descriptor, Cargo
manifest/lock, toolchain file, proof output or Ligature state.

## Source pin

- Repository: <https://github.com/google/leveldb>
- Tag: `1.23`
- Commit: `99b3c03b3284f5886f9ef9a4ef703d57373e61be`
- Machine-readable pin: `SOURCE-PIN.json`
- Checkout: **none**. `upstream/` is created by intake #191 after
  the pin is re-verified. #177 does not clone or vendor upstream source.

## Ownership and edges

Ownership is the approved working hypothesis. Exact Rust contracts and the
real function/call map are intake evidence, not frozen here.

- **creusot**: Ordered-map/operation-history semantics, handler/replay state.
- **verus**: Prefix-compressed block representation, restart/seek/iteration, log framing/reassembly and parser progress.
- **kani**: Bounded fixed/varint codecs, CRC32C arithmetic/masking, and local buffer/fault cases.

Candidate edges:

- Creusot batch/replay orchestration consumes Verus-checked parsing/framing contracts.
- Verus log/block parsing calls Kani-owned coding/CRC helpers.
- WriteBatch::Iterate dispatches Creusot-owned Handler Put/Delete semantics.
- These are assignment hypotheses; intake must record exact real sites and reject disconnected three-demo designs.

## Per-verifier Cargo / target / proof / config roots

### `rust/leveldb-creusot/` (creusot)

- Manifest: `rust/leveldb-creusot/Cargo.toml` — **absent, protected**. Creation route:
  `ligature.pyz scaffold-crate --issue <issue> --crate leveldb-creusot --grant-id <grant> --json`
  after the descriptor declares this crate, or the operator creates it under an
  exact issue/path grant. There is no Creusot `configure-crate` profile in Ligature 1.4.3;
  the operator must create/update this manifest under an exact grant.
- Lock: `rust/leveldb-creusot/Cargo.lock` — **absent, protected**. No sanctioned general
  lock writer exists in Ligature 1.4.3; operator-managed exact-path action
  required.
- Nested toolchain: `rust/leveldb-creusot/rust-toolchain.toml` — **absent, protected**.
  No sanctioned nested-toolchain writer; operator-managed exact-path action
  required. Intended pin: `nightly-2026-04-21 (rustc 1.97.0-nightly 66da6cae1 2026-04-20)`.
- Cargo config: `rust/leveldb-creusot/.cargo/config.toml` — **absent, protected**;
  intended to carry the verifier-specific patch/config, including the Creusot
  `creusot-std` source patch when applicable.
- Build target: `/tmp/p4-<issue>-leveldb-three-verifiers/leveldb-creusot/target` (task-specific,
  disposable, never in Git).
- Config root: `/tmp/p4-<issue>-leveldb-three-verifiers/config/leveldb-creusot` (Why3 config/cache
  for Creusot; verifier-local config for others).
- Durable proof/evidence: `analysis/verification/<run-id>/leveldb-creusot/`
  (separate per tool; no shared proof output).

### `rust/leveldb-verus/` (verus)

- Manifest: `rust/leveldb-verus/Cargo.toml` — **absent, protected**. Creation route:
  `ligature.pyz scaffold-crate --issue <issue> --crate leveldb-verus --grant-id <grant> --json`
  after the descriptor declares this crate, or the operator creates it under an
  exact issue/path grant. For a Verus crate, the typed follow-up is
  `configure-crate --issue <issue> --crate leveldb-verus --profile cargo-verus --grant-id <grant> --json`.
- Lock: `rust/leveldb-verus/Cargo.lock` — **absent, protected**. No sanctioned general
  lock writer exists in Ligature 1.4.3; operator-managed exact-path action
  required.
- Nested toolchain: `rust/leveldb-verus/rust-toolchain.toml` — **absent, protected**.
  No sanctioned nested-toolchain writer; operator-managed exact-path action
  required. Intended pin: `1.95.0`.
- Cargo config: `rust/leveldb-verus/.cargo/config.toml` — **absent, protected**;
  intended to carry the verifier-specific patch/config, including the Creusot
  `creusot-std` source patch when applicable.
- Build target: `/tmp/p4-<issue>-leveldb-three-verifiers/leveldb-verus/target` (task-specific,
  disposable, never in Git).
- Config root: `/tmp/p4-<issue>-leveldb-three-verifiers/config/leveldb-verus` (Why3 config/cache
  for Creusot; verifier-local config for others).
- Durable proof/evidence: `analysis/verification/<run-id>/leveldb-verus/`
  (separate per tool; no shared proof output).

### `rust/leveldb-kani/` (kani)

- Manifest: `rust/leveldb-kani/Cargo.toml` — **absent, protected**. Creation route:
  `ligature.pyz scaffold-crate --issue <issue> --crate leveldb-kani --grant-id <grant> --json`
  after the descriptor declares this crate, or the operator creates it under an
  exact issue/path grant.
- Lock: `rust/leveldb-kani/Cargo.lock` — **absent, protected**. No sanctioned general
  lock writer exists in Ligature 1.4.3; operator-managed exact-path action
  required.
- Nested toolchain: `rust/leveldb-kani/rust-toolchain.toml` — **absent, protected**.
  No sanctioned nested-toolchain writer; operator-managed exact-path action
  required. Intended pin: `1.95.0`.
- Cargo config: `rust/leveldb-kani/.cargo/config.toml` — **absent, protected**;
  intended to carry the verifier-specific patch/config, including the Creusot
  `creusot-std` source patch when applicable.
- Build target: `/tmp/p4-<issue>-leveldb-three-verifiers/leveldb-kani/target` (task-specific,
  disposable, never in Git).
- Config root: `/tmp/p4-<issue>-leveldb-three-verifiers/config/leveldb-kani` (Why3 config/cache
  for Creusot; verifier-local config for others).
- Durable proof/evidence: `analysis/verification/<run-id>/leveldb-kani/`
  (separate per tool; no shared proof output).


## Oracle dependencies

- LevelDB 1.23 native storage-format oracle
- Native dependencies:
  - native db/log_test.cc and table/table_test.cc at the pinned commit
  - a native wrapper over the selected modules with an in-memory Env/handler
- Comparison plan: Compare append/read/replay and block-build/seek traces, including short writes, truncation, checksum failures and malformed batches. Preserve partial handler effects on corruption; compression is disabled for this slice.
- Native build root: `/tmp/p4-<issue>-leveldb-three-verifiers/oracle` (task-specific `/tmp` root).

## Protected paths: exact inventory and creation routes

Every path below is **absent** in this root. These are the paths that must not
be hand-written by a worker.

| Path | Status | Creation route |
|---|---|---|
| `project-descriptor.json` | absent | Operator runs the approved `ligature.pyz init` in this root (T2/operator action); no path-specific grant exists in #177. |
| `.ligature/**` | absent | Created by the same approved `init`; operator-managed. |
| `schemas/**` | absent | Supplied by the approved Ligature install/init; operator-managed. |
| `tools/ligature/**` | absent | Operator installs the approved bundle (currently 1.4.3, SHA-256 `1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1`) with checksums/provenance. |
| `rust/*/Cargo.toml` | absent | `scaffold-crate` under an exact active manifest grant, or operator-written under an exact issue/path grant. |
| `rust/*/Cargo.lock` | absent | No sanctioned general lock writer in 1.4.3; operator-managed exact-path action. |
| `rust/*/rust-toolchain.toml` | absent | No sanctioned nested-toolchain writer; operator-managed exact-path action. |
| `rust/*/.cargo/config.toml` | absent | Operator-managed exact-path action (verifier config/patches). |
| `rust/*/build.rs` | absent | Operator-managed protected path. |
| `rust/*/specs/**` | absent | Ligature `draft`/promotion workflow under issue-specific grants; not hand-written. |
| `ci/**`, `scripts/**`, `tests/harnesses/**` | absent | Operator/sanctioned only; no grant in #177. |
| `.envrc`, `.mcp.json`, `.github/**` | absent | Operator-managed local/CI configuration. |
| `.codex/skills/ligature/**` | absent | Supplied/managed with the approved Ligature install. |
| Outer submodule registration | absent | Operator action in the outer repository (`.gitmodules` + pin); not performed by #177. |

The corresponding policy proposal is in `root-setup.json`. It is a proposal
only; #177 issues no grant.

## Toolchain evidence (recorded outside this root)

- Creusot 0.12 pair probe, Why3 local-socket access, and external
  companion-output placement:
  `planning/p4-mixed-2026-10-26/setup/evidence/creusot-0.12-probe/`
- Verus 1.95 probe: `planning/p4-mixed-2026-10-26/setup/evidence/verus-1.95-probe/`
- Kani 0.67 probe: `planning/p4-mixed-2026-10-26/setup/evidence/kani-0.67-probe/`
- Before/after protected hashes and comparison:
  `planning/p4-mixed-2026-10-26/setup/protected-hashes-before.json`,
  `protected-hashes-after.json`, `protected-hashes-compare.json`.

## Smoke check

Canonical, reusable check (run from the workspace root):

```bash
planning/p4-mixed-2026-10-26/setup/p4-root-smoke-check.sh --probe leveldb-three-verifiers
```

Without `--probe` it verifies the Git root, required setup files, absence of
protected paths, and tool versions. With `--probe` it additionally runs one
synthetic obligation per declared verifier in a disposable `/tmp` fixture.

## Status

- Independent Git repository: yes (`git init -b main`, no commit).
- Ligature-initialized workspace: **no** — pending operator `init`/descriptor
  and bundle installation. This is a recorded setup blocker, not a silent
  omission.
- Production port claim: none.

## Current post-init state (2026-11-14)

- Independent Git root: yes; branch `main`, no commits.
- Ligature 1.4.3 bundle and init scaffolding: present; bundle SHA-256 is
  `1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1`.
- `project-descriptor.json` remains the generated template: it has one generic
  crate and a template reviewer value. It is not an accepted review or the
  final Creusot/Verus/Kani crate assignment.
- `docs/reliance-policy.md` remains the generated placeholder; no human policy
  acceptance is recorded.
- Cargo manifests/locks, nested Rust toolchain/config files, upstream checkout,
  source port, and per-tool proof output do not exist. No submodule is
  registered.
- The root-specific measured tool versions and limitations are in
  [VERIFIER-TOOLCHAIN-COMPATIBILITY.md](VERIFIER-TOOLCHAIN-COMPATIBILITY.md).
- The workspace-level compatibility aggregation is recorded in the enclosing
  worktree at `planning/p4-mixed-2026-10-26/setup/`; this repository's
  compatibility summary remains local and does not depend on that sibling
  path.
