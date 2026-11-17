# P4 workspace setup record — Chainlink #177 (2026-11-14)

> **Historical snapshot notice:** The status claims below describe the
> pre-init inventory and evidence captured by the earlier #177 attempt. After
> that snapshot, the operator directed Ligature 1.4.3 installation and `init`
> in each independent root. See
> [post-init reconciliation](post-init-reconciliation-2026-11-14.md) and the
> [Ligature/verifier compatibility record](LIGATURE-VERIFIER-COMPATIBILITY.md)
> for current observed state. The old evidence and hashes are retained.

Read `../P4-MIXED-PORT-PLAN.md`, `../../WORKER-CONTRACT.md` and the per-root
`analysis/setup/SETUP.md` before using these roots.

## Result

Four independent Git roots now exist with worker-authored setup records:

| Root | Project | Verifiers | Source pin | Git | Ligature workspace |
|---|---|---|---|---|---|
| `icl-creusot-verus/` | M4 Boost.ICL | Creusot + Verus | `boost-1.88.0` @ `2741c3a1b7b79f7326360c26c3e1588b385c9e53` | `main`, no commits | **not initialized** |
| `tinyxml2-creusot-kani/` | M5 TinyXML2 | Creusot + Kani | `11.0.0` @ `9148bdf719e997d1f474be6bcc7943881046dba1` | `main`, no commits | **not initialized** |
| `snappy-verus-kani/` | M6 Snappy | Verus + Kani | `1.2.2` @ `6af9287fbdb913f0794d0148c6aa43b58e63c8e3` | `main`, no commits | **not initialized** |
| `leveldb-three-verifiers/` | M7 LevelDB storage slice | Creusot + Verus + Kani | `1.23` @ `99b3c03b3284f5886f9ef9a4ef703d57373e61be` | `main`, no commits | **not initialized** |

`date-creusot/`, `swisstable-verus/` and `crypto-mixed/` remain the three
baseline records and are unchanged by this work.

**No production port, proof, closure or risk claim is made.** The roots are Git
repositories with setup documentation; they are not Ligature-initialized
workspaces, contain no Cargo crate and no upstream checkout.

The earlier planning snapshot
`planning/p4-mixed-2026-10-26/dependency-check.json` still records
`planned_root_directories_created: false`; it is a hash-pinned pre-setup
snapshot and was not rewritten. `setup-status.json` is the current setup state.

## What was created (worker-allowed content only)

Each root has exactly:

```text
README.md                       root charter, ownership, pins, boundaries
SOURCE-PIN.json                 immutable upstream tag/commit pin
PORT-GAPS.md                    setup-visible transfer gaps only
.gitignore                      build/cache ignores
findings/limitations.jsonl      setup findings (schema-validated)
oracle/README.md                native oracle dependencies and comparison plan
oracle/oracle-PROTOCOL.md       workspace differential-testing protocol (copy)
analysis/setup/SETUP.md         exact protected-path routes and status
analysis/setup/root-setup.json  machine-readable setup record
```

No `project-descriptor.json`, `.ligature/`, `schemas/`, `tools/ligature/`,
Cargo manifest/lock, nested `rust-toolchain.toml`, `.cargo/config.toml`,
`ci/`, `scripts/`, `tests/harnesses/`, spec tree or upstream source exists in
any of the four roots.

## What is deliberately operator-managed (blocker for full setup)

`#177` has no path-specific grant. The exact per-root paths and the creation
route for each one are enumerated in
[`PROTECTED-WRITE-ENUMERATION.md`](PROTECTED-WRITE-ENUMERATION.md) and
[`protected-write-enumeration.json`](protected-write-enumeration.json):
**98 exact entries, all absent, no grant issued.**

The blocking prerequisites are:

1. **Approved Ligature bundle + `init`/descriptor.** Each root has no
   `tools/ligature/` bundle, so no `ligature.pyz` command can run there. An
   operator must install the approved bundle (currently 1.4.3, SHA-256
   `1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1`) and run
   the approved `init`. Exact flags must come from that bundle's own `--help`;
   they are not guessed here.
2. **Protected Cargo manifests and independent locks.** `scaffold-crate`
   requires a declared crate and an exact active manifest grant. There is no
   sanctioned general lock writer in 1.4.3.
3. **Nested toolchain and Cargo config files.** There is no sanctioned
   nested-toolchain writer and no Creusot `configure-crate` profile.
4. **Outer-repository submodule registration.** `.gitmodules` and the root
   submodule pins are operator-managed and were not touched.

Until 1–4 are granted/created, the roots are Git roots with setup records, not
usable Ligature work packages. This is recorded in every root as findings
`<root>-001` and `<root>-002` (severity `blocker`).

## Toolchain verification

### Operator-selected P4 Creusot pair — verified

`/nix/store/9y9g4kpsppxn6zqmyfkvfcc2234qkdwv-creusot-wrapped` was run with
rustup `nightly-2026-04-21`:

```text
cargo-creusot 0.12.0-dev
Rust toolchain nightly-2026-04-21
Why3 platform, version 1.8.2+git
why3find v1.3.0+dev
alt-ergo 2.6.3 (recommended 2.6.2)
z3 4.15.3
cvc4 1.8
cvc5 1.3.1
rustc 1.97.0-nightly (66da6cae1 2026-04-20)
```

The matching `creusot-std` source is
`/nix/store/22j5g9088m140fgx2l6vbskkmg5ra5pp-creusot-source/creusot-std`
(`0.12.0-dev`). One synthetic obligation proved:

```text
Proved (verif/p4_setup_creusot_probe_rlib/increment.coma) ✔
```

### Declared shell remains 0.14 — separate epic #2 finding

The workspace flake's declared shell still resolves Creusot `0.14.0-dev`
(`rustc 1.99.0-nightly`, `cargo-creusot 0.14.0-dev`, nightly-2026-08-03,
Alt-Ergo 2.6.2, Z3 5.1.0, and a `cvc5 bad CVC5 version` diagnostic), not the
selected 0.12 pair. Exact output:
`evidence/declared-shell-creusot.txt`. The P4 probes use the 0.12 wrapper
explicitly. This setup run does **not** validate the declared 0.14 shell; the
existing epic #2 finding stands and is repeated as `<root>-003` in each
Creusot root.

### Local Why3 solver socket — verified

`why3 config detect` under a private `XDG_CONFIG_HOME`, `TMPDIR` and
`XDG_RUNTIME_DIR` exited 0 and added 14 provers; a real proof then completed.
A traced run (`strace -f -e trace=network`) recorded the Why3 server binding,
connecting to and accepting on `why3server028131sock` (`AF_UNIX`):

```text
bind(4, {sa_family=AF_UNIX, sun_path="why3server028131sock"}, 110) = 0
connect(4, {sa_family=AF_UNIX, sun_path="why3server028131sock"}, 22) = 0
accept(4, {sa_family=AF_UNIX}, [110 => 2]) = 6
```

Local Unix-socket access to the solver server is therefore verified. Socket
denial would be an environment failure, not a proof result; none occurred.
See `evidence/creusot-0.12-probe/why3-socket-trace.txt`.

### External Creusot companion-output placement — verified with a limitation

`cargo-creusot creusot --only coma --output-dir <external>` writes the `.coma`
under the external root. However:

- `proof.json` is written **inside the crate** at
  `verif/<crate>/<file>/proof.json`, not under `--output-dir`.
- `.why3find/` is also **crate-local**.
- `--only prove` resolves patterns under the crate's `verif/` tree; a `.coma`
  that exists only under the external output root produces `No files to prove`.

Therefore an external output directory alone is not a complete evidence
boundary. Future proof runs must use a fresh crate/target and explicitly copy
or allowlist `proof.json` and `.why3find/` into the durable per-tool analysis
path. Recorded as `<root>-004` in each Creusot root and in `PORT-GAPS.md`.

### Verus and Kani

```text
Verus Version: 0.2026.05.24.ecee80a, Rust 1.95.0
  "success": true, "verified": 1, "errors": 0
cargo-kani 0.67.0 / CBMC 6.8.0, Rust 1.95.0
  SUMMARY: ** 0 of 3 failed
  VERIFICATION:- SUCCESSFUL
```

All probes used disposable `/tmp` roots and synthetic obligations only.

## Reusable per-root smoke check

```bash
planning/p4-mixed-2026-10-26/setup/p4-root-smoke-check.sh <root>
planning/p4-mixed-2026-10-26/setup/p4-root-smoke-check.sh --probe <root>
```

Without `--probe` it verifies the independent Git root, required setup files,
SOURCE-PIN consistency with `upstream-pins.json`, findings-schema validity,
oracle-protocol identity, absence of protected paths, and tool availability.
With `--probe` it additionally runs one synthetic Creusot/Verus/Kani obligation
per declared verifier in `/tmp`.

Recorded results (all exit 0):

| Root | No-probe | Full probe |
|---|---|---|
| `icl-creusot-verus` | pass | Creusot + Verus pass |
| `tinyxml2-creusot-kani` | pass | Creusot + Kani pass |
| `snappy-verus-kani` | pass | Verus + Kani pass |
| `leveldb-three-verifiers` | pass | Creusot + Verus + Kani pass |

Logs are in `evidence/smoke-*.log`.

## Baseline and protected-path preservation

`protected-hashes.py` snapshots 174 protected/operator-managed files in the
workspace root and three baseline pilots (root flake/lock, `.gitmodules`,
descriptors, `.ligature/`, CI/scripts, Cargo manifests/locks/toolchains, spec
trees, policy files). It also tracks 113 new-root protected targets.

- Before: `protected-hashes-before.json` (2026-11-14T19:26Z)
- After: `protected-hashes-after.json`
- Comparison: `protected-hashes-compare.json`

Result: every pre-existing protected file is byte-identical and every new-root
protected target is still absent. No protected write, flake edit or commit was
made. The pre-existing dirty workspace/submodule state was preserved.

## Evidence index

| Path | Content |
|---|---|
| `evidence/creusot-0.12-probe/` | version, compile/external/prove/why3 logs, probe result, generated-file inventory |
| `evidence/verus-1.95-probe/` | probe result and proof-result extract |
| `evidence/kani-0.67-probe/` | probe result and full Kani log |
| `evidence/smoke-*.log` | per-root smoke-check output |
| `probes/*.sh` | reusable verifier probes |
| `protected-write-enumeration.{json,md}` | exact 98 protected paths and routes |
| `protected-hashes-*.json` | before/after protected hashes |
| `setup-status.json` | machine-readable summary and non-claims |
| `evidence.sha256` | hashes every other setup deliverable; verify with `sha256sum -c` |

## Next steps (operator, then intake)

1. Operator: install a verified Ligature bundle in each root, run approved
   `init`, create the descriptor with the root-specific write policy, and issue
   exact grants for the manifest/lock/toolchain paths. Use
   `PROTECTED-WRITE-ENUMERATION.md` as the checklist.
2. Operator: register the four roots as submodules/pins in the outer repository
   and make the initial baseline commit in each root (the plan requires a
   committed baseline before Stage 7).
3. Then run intake #179 / #183 / #187 / #191 to check out the pinned upstream,
   verify the native oracle and freeze the real call/contract map.
4. Before any production proof: resolve the 0.14 shell mismatch on epic #2 and
   adopt the companion-output copy/allowlist procedure above.

## Explicit non-claims

- No P4 project builds, ports, proofs, closure or native oracle runs; the only
  proofs are the synthetic setup probes above.
- No claim that the declared 0.14 shell runs Creusot correctly.
- No claim that the selected pin is the latest release.
- No claim that a Git root is already a Ligature workspace.
- No grant, approval, risk acceptance or production promotion.
