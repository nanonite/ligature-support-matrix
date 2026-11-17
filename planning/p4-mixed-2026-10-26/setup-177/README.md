# Chainlink #177 — four isolated mixed-verifier workspace setup

**Status: setup design, per-root path enumeration, toolchain verification, and a
reusable smoke check are complete. This attempt did not create the four roots.**
The operator's #177 write-set design approval issues no path grants, and the
approved design keeps descriptors/write policies, protected Cargo manifests and
locks, nested toolchain files, and outer-repository submodule registration
operator-managed or behind a sanctioned command with an exact issue/path grant.
This attempt therefore enumerates every per-root path and creation route before
any protected write, runs the required non-protected probes, and records the
missing grants as a blocker. No issue was closed.

Concurrency note: at final validation (2026-11-14T19:28Z) the four root
directories had appeared with empty `.git/` directories and no commits. They
were created by a concurrent process/workflow during this session; this attempt
did not create them and left them untouched. No descriptor, manifest, lock,
toolchain, or source file exists in them, and the planned-root descriptors
remain absent. Reviewers should reconcile the concurrent work before treating
setup as complete.

Parent checkpoint #161 is closed (2026-11-14T18:19:34Z), so #177's listed
blocker is satisfied. The three baseline pilots remain untouched records:
`date-creusot/`, `swisstable-verus/`, `crypto-mixed/`.

- Machine-readable enumeration: [`protected-paths.json`](protected-paths.json)
- Toolchain/probe evidence: [`evidence/toolchain-probe.json`](evidence/toolchain-probe.json)
- Reusable smoke check: [`scripts/smoke_check.py`](scripts/smoke_check.py)
- Self-test: [`scripts/selftest.sh`](scripts/selftest.sh),
  [`evidence/smoke-check-selftest.log`](evidence/smoke-check-selftest.log)
- Protected before-hashes: [`evidence/protected-hashes-before.json`](evidence/protected-hashes-before.json)

## 1. Planned roots and ownership

Each row is one independent Git/Ligature root with its own descriptor, write
policy, source pin, oracle, findings, and per-verifier Cargo roots. Verifier
ownership is the approved assignment hypothesis from
`planning/p4-mixed-2026-10-26/projects.json`; exact function/call maps remain
intake evidence with issue-local human review.

| Root | Project | Pin | Verifiers | Cargo roots (one per verifier) |
|---|---|---|---|---|
| `icl-creusot-verus/` | M4 Boost.ICL | `boost-1.88.0` @ `2741c3a1b7b79f7326360c26c3e1588b385c9e53` | Creusot + Verus | `rust/icl-creusot-verus-creusot/`, `rust/icl-creusot-verus-verus/` |
| `tinyxml2-creusot-kani/` | M5 TinyXML2 | `11.0.0` @ `9148bdf719e997d1f474be6bcc7943881046dba1` | Creusot + Kani | `rust/tinyxml2-creusot-kani-creusot/`, `rust/tinyxml2-creusot-kani-kani/` |
| `snappy-verus-kani/` | M6 Snappy | `1.2.2` @ `6af9287fbdb913f0794d0148c6aa43b58e63c8e3` | Verus + Kani | `rust/snappy-verus-kani-verus/`, `rust/snappy-verus-kani-kani/` |
| `leveldb-three-verifiers/` | M7 LevelDB storage slice | `1.23` @ `99b3c03b3284f5886f9ef9a4ef703d57373e61be` | Creusot + Verus + Kani | `rust/leveldb-three-verifiers-creusot/`, `...-verus/`, `...-kani/` |

Ownership split (fit hypothesis, frozen only after intake):

- **M4** — Creusot: endpoint/order/interval algebra and high-level set
  operations. Verus: canonical segment storage, mutation, split/coalesce,
  iterator/representation invariants.
- **M5** — Creusot: parser progress/recursive structure, DOM parent/sibling
  ownership, serialization, UTF32→UTF8 contracts. Kani: bounded `StrPair`
  normalization and entity scanning, length/radix/overflow buffer paths.
- **M6** — Verus: tag/decoder state invariants and portable
  `IncrementalCopySlow`. Kani: bounded optimized `IncrementalCopy`,
  vector/shuffle/unaligned/tail/slop paths against scalar semantics.
- **M7** — Creusot: ordered-map/operation-history and batch handler/replay
  semantics. Verus: block representation/restart/seek, log framing/reassembly,
  parser progress. Kani: bounded fixed/varint codecs, CRC32C arithmetic/masking,
  local buffers/faults.

The full edge candidates, oracle plans, coverage goals, and explicit exclusions
are copied from the approved project map into `protected-paths.json`.

## 2. Write-set design (approved, no grants issued)

Worker-authorable inside each root only:

```text
rust/*/src/
rust/*/tests/
rust/*/verif/            # raw Creusot .coma + proof.json for the owning crate
oracle/**
analysis/**
findings/limitations.jsonl
PORT-GAPS.md
```

Operator-managed or human T2:

```text
project-descriptor.json       .ligature/**        ci/**
tools/**                      upstream/**         analysis/upstream/**
Cargo.toml (root-level)       rust/*/Cargo.toml   rust/*/Cargo.lock
rust-toolchain.toml           rust/*/rust-toolchain.toml
rust/*/.cargo/**              rust/*/build.rs
specs/**                      rust/*/specs/**    specs/_closure/**
docs/reliance-policy.md       docs/*-schema.json  tests/harnesses/**
.envrc                        .mcp.json           .gitignore          README.md
```

No root-level Cargo workspace. Each verifier Cargo root owns its own
`Cargo.toml`, `Cargo.lock`, `rust-toolchain.toml`, `.cargo/config.toml`, and
target directory. There is no shared mutable manifest, lock, ledger, closure
directory, target, or proof output between roots.

Creation-route catalog (`protected-paths.json` → `route_catalog`):

| Route | Tier / grant | Meaning |
|---|---|---|
| `operator-git-root` | operator / none | `mkdir`, `git init`, initial baseline commit. Workers must not `git init`/commit/push. |
| `operator-ligature-bundle` | operator / **exact path grant** | Install the approved 1.4.3 bundle into `tools/ligature/` (`ligature.pyz`, `SHA256SUMS`, `PROVENANCE.json`). No Ligature verb writes this tree. |
| `operator-ligature-init` | operator / none | Root-local `ligature.pyz init`; descriptor/write policy is T2. |
| `sanctioned-scaffold-crate` | sanctioned / **exact manifest grant** | After descriptor declaration: `scaffold-crate --issue <stage> --crate <name> --grant-id <id>`. |
| `sanctioned-configure-crate-verus` | sanctioned / **exact manifest grant** | Verus crates only: `configure-crate --profile cargo-verus`; the historical `vstd` refusal (#124) must be reported, not hand-edited. |
| `operator-lockfile` | operator / none | No sanctioned writer exists for `Cargo.lock`. |
| `operator-toolchain-file` | operator / none | No sanctioned writer exists for nested `rust-toolchain.toml` or `.cargo/config.toml`. |
| `operator-source-pin` | operator / **exact path grant** | Place `upstream/**` at the immutable pin and record `upstream/upstream-pin.json`. |
| `worker-allowed` | worker / none | Inside `allowed_roots` under the approved design. |

The exact expanded list is per root in `protected-paths.json` (`paths`, 36/36/35/42
entries). That file is the pre-write enumeration the operator asked for; it
must be reviewed before any grant is issued.

## 3. Toolchains and output roots

Operator-selected P4 Creusot pair: **cargo-creusot / creusot-std 0.12.0-dev with
Rust nightly-2026-04-21**, demonstrated in the existing `#date-creusot` Nix
shell. This is the matching legacy control; it does **not** validate the
declared 0.14 shell mismatch, which remains a finding on epic #2.

| Role | Pin | Route |
|---|---|---|
| Creusot | cargo-creusot / creusot-std `0.12.0-dev`; nightly-2026-04-21; Why3 1.8.2+git; why3find 1.3.0+dev; z3 4.15.3; cvc5 1.3.1; cvc4 1.8; Alt-Ergo 2.6.3 | `nix develop --no-write-lock-file <ws>#date-creusot`; Rust via `rustup run nightly-2026-04-21` |
| Verus | `0.2026.05.24.ecee80a`; Rust 1.95.0; vstd `0.0.0-2026-05-24-0157` | `<ws>#swisstable-verus`; `cargo +1.95.0 verus build` |
| Kani | cargo-kani `0.67.0`; CBMC `6.8.0`; Rust 1.95.0 | `<ws>#crypto-mixed`; `cargo +1.95.0 kani` |

No P4-specific Nix shell exists and `flake.nix`/`flake.lock` must not be edited.
Reuse the declared shells above and pass the compiler explicitly; a missing
shell is a toolchain finding, not a worker flake edit.

Output roots:

```text
targets     /tmp/opencode/p4-<root>-<stage>/targets/<verifier>/
why3        /tmp/opencode/p4-<root>-<stage>/why3/{config,runtime}/
oracle      /tmp/opencode/p4-<root>-<stage>/oracle-build/
durable     <root>/analysis/<stage>/results-<verifier>/
creusot raw <root>/rust/<creusot-crate>/verif/
```

Why3 config and runtime live under the task-specific `/tmp` root. Durable proof
and evidence outputs stay separate per tool under each project.

## 4. Verification performed (scratch only)

All probes ran under `/tmp/opencode/p177` against a copy of the retained #160
fixture. No production root, descriptor, manifest, lock, toolchain, flake,
grant, commit, or push was touched.

**Matching Creusot pair proves.** Exact command with `CARGO_NET_OFFLINE=true`,
task-specific `CARGO_TARGET_DIR`, `XDG_CONFIG_HOME`, `XDG_RUNTIME_DIR`, and
`rustup run nightly-2026-04-21`:

```text
Proved (verif/p160_creusot_kani_rlib/increment.coma) ✔
exit 0
verif/p160_creusot_kani_rlib/increment.coma        1114 bytes
verif/p160_creusot_kani_rlib/increment/proof.json    99 bytes
proof.json: z3, vc_increment, 0.019 s
```

Logs: `evidence/creusot-proof.stdout.txt`, `creusot-proof.stderr.txt`,
`creusot-proof.json`.

**creusot-std path route avoids vendoring dependency source.** Patching
`[patch.crates-io] creusot-std = { path = "<wrapper>/share/creusot-std" }`
resolved the sibling `creusot-std-proc`/`pearlite-syn` path dependencies and
proved with exit 0. The wrapper `share/` tree is a workspace source root.

**External companion-output placement is limited.** On a fresh crate with
`verif/` removed:

- `--output-dir /tmp/.../out` wrote `verif/.../increment.coma` **externally**,
  then exited 1 with `Error: No files to prove`; it created no `verif/` or
  `proof.json` in the crate.
- Passing the external absolute `.coma` as the proof pattern exited 1 with
  `Error: Absolute path must contain prefix "<crate>"`.

Conclusion: 0.12.0-dev can generate a `.coma` under an external output root,
but proof replay and `proof.json` remain crate-relative. Setup route: keep raw
`.coma`/`proof.json` in `rust/<crate>/verif/`, then archive hashed copies under
`analysis/<stage>/results-creusot/`. Do not claim full external companion-output
support. Log: `evidence/creusot-external-output-probe.log`.

**Local Why3 solver-socket access works here.** The proof above completed with
Why3 1.8.2+git and z3 4.15.3 while `XDG_RUNTIME_DIR`/`XDG_CONFIG_HOME` were under
the task-specific `/tmp` scratch root. An explicit `AF_UNIX` bind/listen/connect
roundtrip under `/tmp/opencode/p177` also returned `ok`. This does not
reproduce the #160 sandbox denial and is environment evidence, not a proof
claim. Log: `evidence/why3-socket-probe.log`.

Verus and Kani version identity was rechecked (`Verus 0.2026.05.24.ecee80a`,
`cargo-kani 0.67.0`, rustc 1.95.0). Their measured build/proof evidence remains
the retained #160 coexistence run; no new proof was run in this setup issue.

## 5. Reusable per-root smoke check

`scripts/smoke_check.py` is read-only and supports two modes:

```bash
# validate the four-root setup manifest without creating anything
python3 planning/p4-mixed-2026-10-26/setup-177/scripts/smoke_check.py --plan

# validate one created root
python3 planning/p4-mixed-2026-10-26/setup-177/scripts/smoke_check.py \
  --root /path/to/icl-creusot-verus --json --hash-protected
```

Root mode checks: independent Git work-tree root; descriptor parse/name/crate
declarations/write-set/default verifier; root-local Ligature bundle checksum and
`version`; upstream pin against the manifest; per-verifier `Cargo.toml`,
`Cargo.lock`, `rust-toolchain.toml`, `.cargo/config.toml`; toolchain channel;
no repository-local `target/` and no `target-dir` override; `oracle/`,
`findings/limitations.jsonl`, `PORT-GAPS.md`; distinct per-tool
`analysis/*/results-<verifier>/`; no shared ledger/closure marker; optional
protected-file hashes.

Results this session:

- Plan mode: **59 passed, 0 warnings, 0 failed**.
- Self-test: a seeded synthetic root passes (exit 0); mutating it with a
  repository-local `target/` and a wrong toolchain channel fails (exit 1).
  See `evidence/smoke-check-selftest.log`.

The checker was exercised on a synthetic root only because the four real roots
do not exist. It is ready to run as the first gate after creation.

## 6. Protected hashes and scope checks

`scripts/hash_protected.py` hashes the root flake inputs and the descriptor /
manifest / lock surface of the three baseline pilots. The before-state is in
`evidence/protected-hashes-before.json`: 19 files present, all four planned
descriptors absent. The after-state records zero hash changes and the same
pre-existing dirty tracked surface; it additionally observed four `.git` roots
created concurrently at 19:27-19:28Z (empty at first observation, then seeded
with worker-authorable content by the concurrent workflow by 19:31Z), which
this attempt neither created nor modified. This run added only untracked files
under `planning/p4-mixed-2026-10-26/setup-177/`; it did not edit `flake.nix`,
`flake.lock`, `.gitmodules`, any baseline descriptor, manifest, lock, or
toolchain file.

Scope constraints confirmed:

- No `flake.nix`/`flake.lock` edit and no install outside Nix.
- No Ligature source or `ligature.pyz` contents inspected.
- No `git init`, commit, or push in the workspace root or any pilot.
- No protected write, grant, approval, promotion, or ruling.
- No production port, proof, oracle, or coverage claim.
- No shared target, lock, ledger, closure, or proof output.
- Unrelated dirty work preserved (`.chainlink/issues.db`, `CHANGELOG.md`,
  `README.md`, `VERIFIER-MATRIX.md`, `WORKER-CONTRACT.md`, submodule dirt,
  untracked plan/planning files).

## 7. Findings to carry into the project roots

These are setup/tool findings, not port results. Each must be entered in the
owning root's `findings/limitations.jsonl` when that root exists, linked from
`PORT-GAPS.md` only where it is a C++→Rust transfer gap.

1. **Creusot 0.12.0-dev external companion output is partial.** Generated
   `.coma` can be placed externally, but proof patterns must resolve under the
   crate prefix, and `proof.json` remains crate-relative. A fresh tree cannot
   prove with all companion outputs external. Worked-around route: in-crate
   `verif/` plus hashed durable copies under `analysis/<stage>/results-creusot/`.
2. **The declared crypto-mixed 0.14 Creusot shell remains unvalidated.** The
   matching 0.12.0-dev control proves, but it does not repair the recorded
   `creusot-std is newer than Creusot` mismatch. Keep that on epic #2; do not
   treat this setup as 0.14 shell evidence.
3. **Why3 solver communication needs a writable local runtime/config root.**
   This environment allowed it under `/tmp/opencode/...`; a sandbox that denies
   the local Unix socket is an environment failure, not a proof failure.
4. **Verus/Kani measured evidence is still the #160 coexistence run.** This
   setup rechecked version identity only; no new mixed proof was run.

## 8. Blocker: protected creation needs operator action / exact grants

The following cannot be done under the approved #177 design without a human
grant or operator action, and were deliberately not attempted:

1. **Git roots and initial commits.** `git init`, initial baseline commits, and
   `.gitmodules`/submodule registration are operator-only. Workers are also
   barred from commit/push.
2. **Ligature initialization and policy.** `project-descriptor.json`,
   `.ligature/**`, `ci/**`, descriptor `write_set`, `verifier_policy`, and
   `closure_kind` are operator/human T2 content. `ligature.pyz init` must be
   run in each new root by the operator.
3. **Ligature bundle installation.** `tools/ligature/**` needs an exact human
   grant before the verified 1.4.3 bundle is copied in; there is no sanctioned
   installer verb for this tree.
4. **Source pins.** `upstream/**` and `upstream/upstream-pin.json` need an exact
   grant or operator checkout at the immutable commits above.
5. **Crate manifests, locks, toolchains.** Each `Cargo.toml` needs an exact
   active manifest grant and `scaffold-crate` (Verus also `configure-crate
   --profile cargo-verus`). `Cargo.lock`, nested `rust-toolchain.toml`, and
   `.cargo/config.toml` have no sanctioned writer and remain operator-managed.

Required human outputs to unblock creation: an exact issue/path grant set (or
operator execution) for the paths enumerated in `protected-paths.json`, plus
confirmation of the 1.4.3 bundle copy route. With those, the ordered route in
each root's `creation_order` and the smoke check complete the setup.

Recorded as a blocker on #177; this issue is not closed.

## 9. Concurrent-workflow reconciliation (operator action)

A separate #177 workflow ran in this same shared worktree. Between
19:27Z and 19:31Z it created the four root directories as empty Git repositories
and wrote worker-authorable setup content into them, and it wrote its own setup
tree at `planning/p4-mixed-2026-10-26/setup/`. This attempt did not create or
edit any of that content.

Observed concurrent deliverables and divergence:

| Item | This attempt (`setup-177/`) | Concurrent workflow (`setup/` + roots) |
|---|---|---|
| Crate names | `rust/icl-creusot-verus-creusot/`, `...-verus/` | `rust/icl-creusot/`, `rust/icl-verus/` |
| Pin file | planned `upstream/upstream-pin.json` | `SOURCE-PIN.json` at root |
| Setup record | `planning/.../setup-177/` | root `analysis/setup/` + `planning/.../setup/` |
| Root content | none created | README, SOURCE-PIN, findings, oracle, analysis/setup |
| Protected files | none | none |

Both workflows independently reached the same protected boundary: the roots
contain no `project-descriptor.json`, `.ligature/`, `tools/ligature/`,
`upstream/` checkout, Cargo manifest/lock, nested toolchain, or outer submodule
registration. This attempt's read-only checker run against the concurrent roots
records 10 passed / 15 failed for each two-verifier root; see
`evidence/concurrent-roots-smoke-check.txt`. The concurrent checker records
"no protected paths created" as a pass under its own definition.

The operator must choose one consistent naming/evidence scheme before granting
protected creation; do not merge the two trees blindly.

