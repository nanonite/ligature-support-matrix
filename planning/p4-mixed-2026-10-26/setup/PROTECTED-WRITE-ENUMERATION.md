# Exact protected-path enumeration for the four P4 roots (#177)

> **Historical pre-init snapshot.** The operator later directed bundle
> installation and Ligature `init` in all four roots. This file's all-absent
> statuses are no longer current. Use
> [post-init-protected-paths-2026-11-14.json](post-init-protected-paths-2026-11-14.json)
> for the observed current statuses; neither file grants further writes.

Generated from each root's `analysis/setup/root-setup.json`. Every entry is
**absent** and requires an exact operator action or a sanctioned command with an
issue/path grant. `#177` issues no grant and performs no protected write.

- Total exact entries: **98**
- All absent: **true**
- Present entries: none

| Root | Project | Verifiers | Entries |
|---|---|---|---:|
| `icl-creusot-verus/` | M4 | creusot, verus | 23 |
| `leveldb-three-verifiers/` | M7 | creusot, verus, kani | 29 |
| `snappy-verus-kani/` | M6 | verus, kani | 23 |
| `tinyxml2-creusot-kani/` | M5 | creusot, kani | 23 |

## `icl-creusot-verus/`

| Exact path | Status | Creation route | Grant in #177 |
|---|---|---|---|
| `project-descriptor.json` | absent | Operator runs the approved `ligature.pyz init` in this root (T2/operator action); no path-specific grant exists in #177. | no |
| `.ligature/**` | absent | Created by the approved `ligature.pyz init`; operator-managed. | no |
| `schemas/**` | absent | Supplied by the approved Ligature install/init; operator-managed. | no |
| `tools/ligature/**` | absent | Operator installs the approved bundle (1.4.3, SHA-256 1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1) with SHA256SUMS/PROVENANCE; no copy performed by #177. | no |
| `rust/icl-creusot/Cargo.toml` | absent | `ligature.pyz scaffold-crate --issue <N> --crate <name> --grant-id <id> --json` under an exact active manifest grant, or operator exact-path write. | no |
| `rust/icl-verus/Cargo.toml` | absent | `ligature.pyz scaffold-crate --issue <N> --crate <name> --grant-id <id> --json` under an exact active manifest grant, or operator exact-path write. | no |
| `rust/icl-creusot/Cargo.lock` | absent | No sanctioned general lock writer in Ligature 1.4.3; operator exact-path action under an exact issue/path grant. | no |
| `rust/icl-verus/Cargo.lock` | absent | No sanctioned general lock writer in Ligature 1.4.3; operator exact-path action under an exact issue/path grant. | no |
| `rust/icl-creusot/rust-toolchain.toml` | absent | No sanctioned nested-toolchain writer; operator exact-path action under an exact issue/path grant. | no |
| `rust/icl-verus/rust-toolchain.toml` | absent | No sanctioned nested-toolchain writer; operator exact-path action under an exact issue/path grant. | no |
| `rust/icl-creusot/.cargo/config.toml` | absent | Operator exact-path action; carries verifier-specific config/patch. | no |
| `rust/icl-verus/.cargo/config.toml` | absent | Operator exact-path action; carries verifier-specific config/patch. | no |
| `rust/icl-creusot/build.rs` | absent | Operator exact-path action; protected by policy proposal. | no |
| `rust/icl-verus/build.rs` | absent | Operator exact-path action; protected by policy proposal. | no |
| `rust/icl-creusot/specs/**` | absent | Ligature `draft`/promotion workflow under issue-specific grants; never hand-written. | no |
| `rust/icl-verus/specs/**` | absent | Ligature `draft`/promotion workflow under issue-specific grants; never hand-written. | no |
| `ci/**` | absent | Operator/sanctioned exact-path action; no grant in #177. | no |
| `scripts/**` | absent | Operator/sanctioned exact-path action; no grant in #177. | no |
| `tests/harnesses/**` | absent | Operator/sanctioned exact-path action; no grant in #177. | no |
| `.envrc` | absent | Operator-managed local environment file. | no |
| `.mcp.json` | absent | Operator-managed local MCP configuration. | no |
| `.github/**` | absent | Operator-managed CI configuration. | no |
| `.codex/skills/ligature/**` | absent | Managed with the approved Ligature install. | no |

## `leveldb-three-verifiers/`

| Exact path | Status | Creation route | Grant in #177 |
|---|---|---|---|
| `project-descriptor.json` | absent | Operator runs the approved `ligature.pyz init` in this root (T2/operator action); no path-specific grant exists in #177. | no |
| `.ligature/**` | absent | Created by the approved `ligature.pyz init`; operator-managed. | no |
| `schemas/**` | absent | Supplied by the approved Ligature install/init; operator-managed. | no |
| `tools/ligature/**` | absent | Operator installs the approved bundle (1.4.3, SHA-256 1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1) with SHA256SUMS/PROVENANCE; no copy performed by #177. | no |
| `rust/leveldb-creusot/Cargo.toml` | absent | `ligature.pyz scaffold-crate --issue <N> --crate <name> --grant-id <id> --json` under an exact active manifest grant, or operator exact-path write. | no |
| `rust/leveldb-verus/Cargo.toml` | absent | `ligature.pyz scaffold-crate --issue <N> --crate <name> --grant-id <id> --json` under an exact active manifest grant, or operator exact-path write. | no |
| `rust/leveldb-kani/Cargo.toml` | absent | `ligature.pyz scaffold-crate --issue <N> --crate <name> --grant-id <id> --json` under an exact active manifest grant, or operator exact-path write. | no |
| `rust/leveldb-creusot/Cargo.lock` | absent | No sanctioned general lock writer in Ligature 1.4.3; operator exact-path action under an exact issue/path grant. | no |
| `rust/leveldb-verus/Cargo.lock` | absent | No sanctioned general lock writer in Ligature 1.4.3; operator exact-path action under an exact issue/path grant. | no |
| `rust/leveldb-kani/Cargo.lock` | absent | No sanctioned general lock writer in Ligature 1.4.3; operator exact-path action under an exact issue/path grant. | no |
| `rust/leveldb-creusot/rust-toolchain.toml` | absent | No sanctioned nested-toolchain writer; operator exact-path action under an exact issue/path grant. | no |
| `rust/leveldb-verus/rust-toolchain.toml` | absent | No sanctioned nested-toolchain writer; operator exact-path action under an exact issue/path grant. | no |
| `rust/leveldb-kani/rust-toolchain.toml` | absent | No sanctioned nested-toolchain writer; operator exact-path action under an exact issue/path grant. | no |
| `rust/leveldb-creusot/.cargo/config.toml` | absent | Operator exact-path action; carries verifier-specific config/patch. | no |
| `rust/leveldb-verus/.cargo/config.toml` | absent | Operator exact-path action; carries verifier-specific config/patch. | no |
| `rust/leveldb-kani/.cargo/config.toml` | absent | Operator exact-path action; carries verifier-specific config/patch. | no |
| `rust/leveldb-creusot/build.rs` | absent | Operator exact-path action; protected by policy proposal. | no |
| `rust/leveldb-verus/build.rs` | absent | Operator exact-path action; protected by policy proposal. | no |
| `rust/leveldb-kani/build.rs` | absent | Operator exact-path action; protected by policy proposal. | no |
| `rust/leveldb-creusot/specs/**` | absent | Ligature `draft`/promotion workflow under issue-specific grants; never hand-written. | no |
| `rust/leveldb-verus/specs/**` | absent | Ligature `draft`/promotion workflow under issue-specific grants; never hand-written. | no |
| `rust/leveldb-kani/specs/**` | absent | Ligature `draft`/promotion workflow under issue-specific grants; never hand-written. | no |
| `ci/**` | absent | Operator/sanctioned exact-path action; no grant in #177. | no |
| `scripts/**` | absent | Operator/sanctioned exact-path action; no grant in #177. | no |
| `tests/harnesses/**` | absent | Operator/sanctioned exact-path action; no grant in #177. | no |
| `.envrc` | absent | Operator-managed local environment file. | no |
| `.mcp.json` | absent | Operator-managed local MCP configuration. | no |
| `.github/**` | absent | Operator-managed CI configuration. | no |
| `.codex/skills/ligature/**` | absent | Managed with the approved Ligature install. | no |

## `snappy-verus-kani/`

| Exact path | Status | Creation route | Grant in #177 |
|---|---|---|---|
| `project-descriptor.json` | absent | Operator runs the approved `ligature.pyz init` in this root (T2/operator action); no path-specific grant exists in #177. | no |
| `.ligature/**` | absent | Created by the approved `ligature.pyz init`; operator-managed. | no |
| `schemas/**` | absent | Supplied by the approved Ligature install/init; operator-managed. | no |
| `tools/ligature/**` | absent | Operator installs the approved bundle (1.4.3, SHA-256 1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1) with SHA256SUMS/PROVENANCE; no copy performed by #177. | no |
| `rust/snappy-verus/Cargo.toml` | absent | `ligature.pyz scaffold-crate --issue <N> --crate <name> --grant-id <id> --json` under an exact active manifest grant, or operator exact-path write. | no |
| `rust/snappy-kani/Cargo.toml` | absent | `ligature.pyz scaffold-crate --issue <N> --crate <name> --grant-id <id> --json` under an exact active manifest grant, or operator exact-path write. | no |
| `rust/snappy-verus/Cargo.lock` | absent | No sanctioned general lock writer in Ligature 1.4.3; operator exact-path action under an exact issue/path grant. | no |
| `rust/snappy-kani/Cargo.lock` | absent | No sanctioned general lock writer in Ligature 1.4.3; operator exact-path action under an exact issue/path grant. | no |
| `rust/snappy-verus/rust-toolchain.toml` | absent | No sanctioned nested-toolchain writer; operator exact-path action under an exact issue/path grant. | no |
| `rust/snappy-kani/rust-toolchain.toml` | absent | No sanctioned nested-toolchain writer; operator exact-path action under an exact issue/path grant. | no |
| `rust/snappy-verus/.cargo/config.toml` | absent | Operator exact-path action; carries verifier-specific config/patch. | no |
| `rust/snappy-kani/.cargo/config.toml` | absent | Operator exact-path action; carries verifier-specific config/patch. | no |
| `rust/snappy-verus/build.rs` | absent | Operator exact-path action; protected by policy proposal. | no |
| `rust/snappy-kani/build.rs` | absent | Operator exact-path action; protected by policy proposal. | no |
| `rust/snappy-verus/specs/**` | absent | Ligature `draft`/promotion workflow under issue-specific grants; never hand-written. | no |
| `rust/snappy-kani/specs/**` | absent | Ligature `draft`/promotion workflow under issue-specific grants; never hand-written. | no |
| `ci/**` | absent | Operator/sanctioned exact-path action; no grant in #177. | no |
| `scripts/**` | absent | Operator/sanctioned exact-path action; no grant in #177. | no |
| `tests/harnesses/**` | absent | Operator/sanctioned exact-path action; no grant in #177. | no |
| `.envrc` | absent | Operator-managed local environment file. | no |
| `.mcp.json` | absent | Operator-managed local MCP configuration. | no |
| `.github/**` | absent | Operator-managed CI configuration. | no |
| `.codex/skills/ligature/**` | absent | Managed with the approved Ligature install. | no |

## `tinyxml2-creusot-kani/`

| Exact path | Status | Creation route | Grant in #177 |
|---|---|---|---|
| `project-descriptor.json` | absent | Operator runs the approved `ligature.pyz init` in this root (T2/operator action); no path-specific grant exists in #177. | no |
| `.ligature/**` | absent | Created by the approved `ligature.pyz init`; operator-managed. | no |
| `schemas/**` | absent | Supplied by the approved Ligature install/init; operator-managed. | no |
| `tools/ligature/**` | absent | Operator installs the approved bundle (1.4.3, SHA-256 1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1) with SHA256SUMS/PROVENANCE; no copy performed by #177. | no |
| `rust/tinyxml2-creusot/Cargo.toml` | absent | `ligature.pyz scaffold-crate --issue <N> --crate <name> --grant-id <id> --json` under an exact active manifest grant, or operator exact-path write. | no |
| `rust/tinyxml2-kani/Cargo.toml` | absent | `ligature.pyz scaffold-crate --issue <N> --crate <name> --grant-id <id> --json` under an exact active manifest grant, or operator exact-path write. | no |
| `rust/tinyxml2-creusot/Cargo.lock` | absent | No sanctioned general lock writer in Ligature 1.4.3; operator exact-path action under an exact issue/path grant. | no |
| `rust/tinyxml2-kani/Cargo.lock` | absent | No sanctioned general lock writer in Ligature 1.4.3; operator exact-path action under an exact issue/path grant. | no |
| `rust/tinyxml2-creusot/rust-toolchain.toml` | absent | No sanctioned nested-toolchain writer; operator exact-path action under an exact issue/path grant. | no |
| `rust/tinyxml2-kani/rust-toolchain.toml` | absent | No sanctioned nested-toolchain writer; operator exact-path action under an exact issue/path grant. | no |
| `rust/tinyxml2-creusot/.cargo/config.toml` | absent | Operator exact-path action; carries verifier-specific config/patch. | no |
| `rust/tinyxml2-kani/.cargo/config.toml` | absent | Operator exact-path action; carries verifier-specific config/patch. | no |
| `rust/tinyxml2-creusot/build.rs` | absent | Operator exact-path action; protected by policy proposal. | no |
| `rust/tinyxml2-kani/build.rs` | absent | Operator exact-path action; protected by policy proposal. | no |
| `rust/tinyxml2-creusot/specs/**` | absent | Ligature `draft`/promotion workflow under issue-specific grants; never hand-written. | no |
| `rust/tinyxml2-kani/specs/**` | absent | Ligature `draft`/promotion workflow under issue-specific grants; never hand-written. | no |
| `ci/**` | absent | Operator/sanctioned exact-path action; no grant in #177. | no |
| `scripts/**` | absent | Operator/sanctioned exact-path action; no grant in #177. | no |
| `tests/harnesses/**` | absent | Operator/sanctioned exact-path action; no grant in #177. | no |
| `.envrc` | absent | Operator-managed local environment file. | no |
| `.mcp.json` | absent | Operator-managed local MCP configuration. | no |
| `.github/**` | absent | Operator-managed CI configuration. | no |
| `.codex/skills/ligature/**` | absent | Managed with the approved Ligature install. | no |

