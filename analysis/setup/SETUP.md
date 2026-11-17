# snappy-verus-kani setup record (Chainlink #177)

> **Status correction (2026-11-14):** The initial inventory below predates
> the operator-directed Ligature 1.4.3 install and `init` in this root. The
> current state is recorded at the end of this file; the pre-init protected
> path inventory is retained as history.

This file records setup decisions only. It creates no descriptor, Cargo
manifest/lock, toolchain file, proof output or Ligature state.

## Source pin

- Repository: <https://github.com/google/snappy>
- Tag: `1.2.2`
- Commit: `6af9287fbdb913f0794d0148c6aa43b58e63c8e3`
- Machine-readable pin: `SOURCE-PIN.json`
- Checkout: **none**. `upstream/` is created by intake #187 after
  the pin is re-verified. #177 does not clone or vendor upstream source.

## Ownership and edges

Ownership is the approved working hypothesis. Exact Rust contracts and the
real function/call map are intake evidence, not frozen here.

- **verus**: Tag/decoder state invariants, portable IncrementalCopySlow implementation/model, and reconstruction/round-trip properties over the selected raw format.
- **kani**: Bounded IncrementalCopy optimized paths, vector shuffle/unaligned access, tail/slop conditions, compared against scalar semantics.

Candidate edges:

- V->K: DecompressAllTags / AppendFromSelf dispatches IncrementalCopy.
- K->V: IncrementalCopy falls back to IncrementalCopySlow for tight buffers and tails.

## Per-verifier Cargo / target / proof / config roots

### `rust/snappy-verus/` (verus)

- Manifest: `rust/snappy-verus/Cargo.toml` — **absent, protected**. Creation route:
  `ligature.pyz scaffold-crate --issue <issue> --crate snappy-verus --grant-id <grant> --json`
  after the descriptor declares this crate, or the operator creates it under an
  exact issue/path grant. For a Verus crate, the typed follow-up is
  `configure-crate --issue <issue> --crate snappy-verus --profile cargo-verus --grant-id <grant> --json`.
- Lock: `rust/snappy-verus/Cargo.lock` — **absent, protected**. No sanctioned general
  lock writer exists in Ligature 1.4.3; operator-managed exact-path action
  required.
- Nested toolchain: `rust/snappy-verus/rust-toolchain.toml` — **absent, protected**.
  No sanctioned nested-toolchain writer; operator-managed exact-path action
  required. Intended pin: `1.95.0`.
- Cargo config: `rust/snappy-verus/.cargo/config.toml` — **absent, protected**;
  intended to carry the verifier-specific patch/config, including the Creusot
  `creusot-std` source patch when applicable.
- Build target: `/tmp/p4-<issue>-snappy-verus-kani/snappy-verus/target` (task-specific,
  disposable, never in Git).
- Config root: `/tmp/p4-<issue>-snappy-verus-kani/config/snappy-verus` (Why3 config/cache
  for Creusot; verifier-local config for others).
- Durable proof/evidence: `analysis/verification/<run-id>/snappy-verus/`
  (separate per tool; no shared proof output).

### `rust/snappy-kani/` (kani)

- Manifest: `rust/snappy-kani/Cargo.toml` — **absent, protected**. Creation route:
  `ligature.pyz scaffold-crate --issue <issue> --crate snappy-kani --grant-id <grant> --json`
  after the descriptor declares this crate, or the operator creates it under an
  exact issue/path grant.
- Lock: `rust/snappy-kani/Cargo.lock` — **absent, protected**. No sanctioned general
  lock writer exists in Ligature 1.4.3; operator-managed exact-path action
  required.
- Nested toolchain: `rust/snappy-kani/rust-toolchain.toml` — **absent, protected**.
  No sanctioned nested-toolchain writer; operator-managed exact-path action
  required. Intended pin: `1.95.0`.
- Cargo config: `rust/snappy-kani/.cargo/config.toml` — **absent, protected**;
  intended to carry the verifier-specific patch/config, including the Creusot
  `creusot-std` source patch when applicable.
- Build target: `/tmp/p4-<issue>-snappy-verus-kani/snappy-kani/target` (task-specific,
  disposable, never in Git).
- Config root: `/tmp/p4-<issue>-snappy-verus-kani/config/snappy-kani` (Why3 config/cache
  for Creusot; verifier-local config for others).
- Durable proof/evidence: `analysis/verification/<run-id>/snappy-kani/`
  (separate per tool; no shared proof output).


## Oracle dependencies

- Snappy 1.2.2 native oracle
- Native dependencies:
  - native snappy_unittests and shipped corrupted-input tests at the pinned commit
  - shipped testdata/ corpus at the pinned commit
- Comparison plan: Cross-decode native and Rust streams; compare decoded bytes, lengths and error outcomes. Compressed bytes are not required to be identical because the raw format has no canonical encoding.
- Native build root: `/tmp/p4-<issue>-snappy-verus-kani/oracle` (task-specific `/tmp` root).

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
planning/p4-mixed-2026-10-26/setup/p4-root-smoke-check.sh --probe snappy-verus-kani
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
  crate, defaults to Creusot despite this project's Verus/Kani selection, and
  has a template reviewer value. It is not an accepted review or a final
  verifier assignment.
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
