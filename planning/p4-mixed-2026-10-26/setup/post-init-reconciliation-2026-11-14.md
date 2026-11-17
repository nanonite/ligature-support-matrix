# Post-init reconciliation for Chainlink #177

Observed 2026-11-14 after the operator directed installation and Ligature
initialization per independent project Git root. This note supersedes the
pre-init state in `README.md`, `setup-status.json`,
`protected-write-enumeration.{json,md}`, and each original
`analysis/setup/root-setup.json`. Those earlier files remain as evidence of the
pre-init check and are not current path inventories.

## Current four-root state

| Root | Git state | Ligature | Descriptor template | Selected verifiers |
|---|---|---|---|---|
| `icl-creusot-verus/` | independent `.git`, branch `main`, zero commits | 1.4.3 bundle installed and `init` scaffolding present | one generic `crates/icl-creusot-verus-core` crate; default `creusot`; placeholder reviewer | Creusot + Verus |
| `tinyxml2-creusot-kani/` | independent `.git`, branch `main`, zero commits | 1.4.3 bundle installed and `init` scaffolding present | one generic `crates/tinyxml2-creusot-kani-core` crate; default `creusot`; placeholder reviewer | Creusot + Kani |
| `snappy-verus-kani/` | independent `.git`, branch `main`, zero commits | 1.4.3 bundle installed and `init` scaffolding present | one generic `crates/snappy-verus-kani-core` crate; default `creusot` (not the selected combination); placeholder reviewer | Verus + Kani |
| `leveldb-three-verifiers/` | independent `.git`, branch `main`, zero commits | 1.4.3 bundle installed and `init` scaffolding present | one generic `crates/leveldb-three-verifiers-core` crate; default `creusot`; placeholder reviewer | Creusot + Verus + Kani |

All four `tools/ligature/ligature.pyz` files have SHA-256
`1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1` and pass
the bundle's `sha256sum -c SHA256SUMS` check. `ligature init --mode port` added
the project descriptor, Ligature prompts/schemas, shared schemas, install
manifest, renderer and XML helper, and a reliance-policy placeholder.

The per-root invocation shape was:

```bash
python3 tools/ligature/ligature.pyz --workspace "$PWD" init --mode port --name <root-name>
```

Root names: `icl-creusot-verus`, `tinyxml2-creusot-kani`,
`snappy-verus-kani`, and `leveldb-three-verifiers`. The earlier command output
was not retained verbatim; the current tree, descriptor hashes, and bundle
checksums are the retained post-action observations. The compatibility
version/hash commands are retained under `evidence/`.

## Still pending

- The descriptor reviewer value `example-reviewer` is a generated template,
  not an identity or review. The policy placeholder has not been accepted.
- The descriptor crate path/default-verifier fields remain generic. In
  particular, Snappy still says `creusot`. No final per-verifier crate
  assignment is recorded in these descriptors.
- No project Cargo manifest or lock, nested `rust-toolchain.toml`, Cargo
  config, Nix flake/lock, upstream checkout, source port, or durable project
  proof output exists. No outer `.gitmodules` registration exists.
- No formal Ligature issue/path grant was created. The operator's direct
  instruction was used for the bundle installation and init action only; it
  does not create a reusable capability or authorize unrelated protected
  writes. No `authorize-write` or `accept-policy` command was run.
- No project proof, production claim, risk acceptance or assurance closure is
  made. Existing scratch proof evidence remains synthetic and centralized.

## Toolchain direction recorded

The operator directed that each independent root keep its own verifier
environment, that Ligature supply a reproducible Nix Creusot/`creusot-std`
pair, and that each Ligature version publish its tested verifier versions.
The measured local matrix and the 1.4.3 CLI/schema limitation are in
[`LIGATURE-VERIFIER-COMPATIBILITY.md`](LIGATURE-VERIFIER-COMPATIBILITY.md).
The current successful Creusot 0.12 control is not a recoverable portable Nix
pin from the retained path metadata. The declared 0.14 shell mismatch remains
open on epic #2. No root `flake.nix` or `flake.lock` was written.

## Write-set and next actions

The init-generated protected files are now present. The new
[`post-init-protected-paths-2026-11-14.json`](post-init-protected-paths-2026-11-14.json)
compares the same 98 path classes with the current roots: 7 entries are
present and 16 absent in each two-verifier root; 7 are present and 22 absent
in the three-verifier root. This is an observation only and issues no grant.
The prior `protected-write-enumeration.{json,md}` remains a pre-init snapshot.
The proposed source-only worker roots remain as approved in #161 and the
existing root setup records. For each project, the next protected setup steps
still need exact paths, a sanctioned creation route or direct operator action,
and applicable human checkpoints:

1. Replace template descriptor values with the project-owned verifier crates
   and truthful write set; identify the real reviewer before recording any
   review or accepting the reliance policy.
2. Decide/publish the Ligature-provided Nix pin and version-level tested-tool
   matrix; resolve the 0.14 shell mismatch and make the Creusot companion-output
   procedure production-ready.
3. Enumerate and authorize exact Cargo manifest/lock, nested compiler pin,
   verifier config and per-tool output paths before crate creation.
4. Create upstream checkouts only at their intake issues, then verify oracle
   builds and source ownership. Register outer submodules only after the
   independent roots have approved remotes and baseline commits.

The source ports and downstream issue stages remain untouched.
