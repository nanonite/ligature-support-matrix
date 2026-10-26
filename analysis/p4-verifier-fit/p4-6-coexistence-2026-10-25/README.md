# Chainlink #160 — scratch verifier coexistence (2026-10-25)

## Result and scope

The smallest layout demonstrated here has **two independent Cargo roots**: one Creusot crate and one Verus crate. Kani overlays the Creusot crate and checks the same executable `increment` function. Each verifier run uses its own target directory; proof output is separate from compiler targets. All obligations are synthetic arithmetic controls. They establish no production P3 guarantee.

The fixtures were built under `/tmp/ligature-p160-prototype-20261025`, not in the live P3 source tree. The P3 1.4.3 bundle used by the earlier #159 intake is SHA-256 `1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1`; this prototype did not call Ligature to create or promote evidence. No production source, descriptor, CI, Cargo manifest/lock, policy, toolchain, flake, or grant ledger was changed. No `_closure` directory is in the retained fixture.

## Demonstrated results

| Run | Exact result | Exit |
|---|---|---:|
| Matching Creusot control, `cargo-creusot 0.12.0-dev` + `creusot-std 0.12.0-dev`, nightly-2026-04-21 | `Proved (verif/p160_creusot_kani_rlib/increment.coma) ✔` | 0 |
| Verus 0.2026.05.24.ecee80a + Rust 1.95.0 | Root JSON: `p160_verus::increment`, `success=true`, `verified=1`, `errors=0`; vstd also reported 1690 verified, 0 errors | 0 |
| Kani 0.67.0 / CBMC 6.8.0, exact harness `increment_matches_postcondition_for_all_nonmax_inputs` | `SUMMARY: ** 0 of 3 failed`; `VERIFICATION:- SUCCESSFUL`; `1 successfully verified harnesses, 0 failures` | 0 |
| Creusot after the Verus and Kani runs, fresh target + external output root | Again `Proved (verif/p160_creusot_kani_rlib/increment.coma) ✔` | 0 |
| Preservation check after that later Creusot run | `sha256sum -c sequence-before.sha256`: **27 of 27 OK**, including earlier source, manifests, both locks, proof output, command records, and Kani GOTO input | 0 |

The Kani harness calls the same executable function as the Creusot contract. Its `#[cfg(kani)]` harness assumes `x < u32::MAX` and checks the increment result. The Verus version is in its own verifier-specific crate. These are synthetic obligations, not production ports.

The post-Kani rerun used a new `CARGO_TARGET_DIR` and `--output-dir`; the generated `.coma` was outside the crate. The archive contains the original 27-entry hash manifest and the separate four-file hash manifest for this later run. The full earlier `verus-build-later` control returned zero but emitted no stdout and only Cargo's `Finished` line (a cache hit); it is not counted as a second Verus proof. The later Creusot run is the actual fresh-target proof-preservation check.

## Scratch layout

```text
ligature-p160-prototype-20261025/
  creusot/                         # independent Cargo root and Cargo.lock
    rust-toolchain.toml             # nightly-2026-04-21 + rust-src
    .cargo/config.toml              # scratch-only patch to copied Creusot 0.12 source
    src/lib.rs                       # increment + Creusot contract + Kani overlay
    verif/.../increment.coma         # generated synthetic proof input
    verif/.../increment/proof.json   # Creusot proof record
  verus/p160_verus/                 # independent Cargo root and Cargo.lock
    rust-toolchain.toml             # 1.95.0
    src/lib.rs                       # Verus-specific increment proof
  targets/
    creusot-final/                  # Creusot compiler target
    creusot-after-kani/             # independent later Creusot target
    verus/                          # Verus compiler target
    kani/                           # Kani/CBMC target; one GOTO .out is archived
  outputs/
    creusot-external-proof/         # explicit-pattern `.coma` output
    creusot-after-kani/             # later `.coma` output
    verus/proof-results.json         # root proof-results JSON
  commands/                         # argv, cwd, env overrides, exit and timestamps
  logs/                             # stdout/stderr, including setup/negative controls
  sequence-before.sha256            # 27 pre-rerun hashes
  sequence-after-kani-added.sha256   # four hashes for the later proof command/output
```

The archive excludes compiled target trees except the 33 KB Kani GOTO input named in the original hash list. It retains crate inputs, local 0.12 source copies used only by this scratch control, locks, toolchain files, Why3 scratch config, proof results, command records, logs, and hash lists. Its `contents.sha256` has 247 entries. After extracting under `/tmp`, all 247 fixture hashes, all 27 earlier-sequence hashes, and all 4 later-proof hashes verified with exit 0. The tar listing contains no `_closure` path. The fixture is archived as `prototype-fixture.tar.gz` so no copied artifact directory is live to discovery.

## Tool inventory and qualification

Inventory ran inside `nix develop --no-write-lock-file /home/goya/storage/full-ligature-port-workspace#crypto-mixed`. In the shell cwd, default Rust selection was stable 1.99.1. `rustup`, `rustc`, `cargo`, and `cargo-kani` resolved through `/home/goya/.cargo/bin`; `cargo-creusot` resolved to `/nix/store/3ll0vqpzkjaimvg7s0r6qw7j1vk8lgiw-creusot-wrapped/bin/cargo-creusot`; Verus and `cargo-verus` to `/nix/store/57l94534x07sysi7gjf4zkkpai6cw6vc-verus-tools/bin/`. `PATH` must retain the Cargo shim directory before the Nix tool paths. The inventory command, full resolved paths, and output are in the archive.

| Role | Toolchain used by the successful prototype | Qualification |
|---|---|---|
| Creusot | Installed Nix path `/nix/store/9y9g4kpsppxn6zqmyfkvfcc2234qkdwv-creusot-wrapped`; cargo-creusot / creusot-std 0.12.0-dev; nightly-2026-04-21 (rustc 1.97.0-nightly) | This is the matching legacy control only. It does **not** validate the current shell. Why3 1.8.2+git, why3find 1.3.0+dev, Alt-Ergo 2.6.3, Z3 4.15.3, CVC4 1.8, CVC5 1.3.1. |
| Verus | Verus 0.2026.05.24.ecee80a; Rust 1.95.0; `vstd = 0.0.0-2026-05-24-0157` | Explicit `cargo +1.95.0`; crate-local pin also selects 1.95.0. |
| Kani | cargo-kani 0.67.0; CBMC 6.8.0 | Explicit `cargo +1.95.0`; harness is selected by exact name. |
| Declared crypto-mixed shell Creusot | cargo-creusot 0.14.0-dev; nightly-2026-08-03; initialized creusot-std 0.14.0 | Existing finding `crypto-creusot-002` remains unresolved. The recorded initialization exits 1 with `Error: creusot-std is newer than Creusot; creusot-std 0.14.0; creusot 0.14.0-dev`. No proof was run with this pair. |

The current-shell version probe also prints Alt-Ergo 2.6.2 (recommended 2.6.4) and a CVC5 1.4.1 “bad CVC5 version” diagnostic while the version command itself exits 0. Those are tool-version diagnostics, not proof failures. They are retained in `logs/creusot-014-shell-version.stdout.txt`. The successful 0.12 proof is not evidence that this current 0.14 shell works; #161 must keep the matching-pair prerequisite visible, and the shell gap is reported on epic #2.

The first sandboxed Why3 attempt stalled while connecting to its local Unix solver socket and was interrupted. An approved rerun with access to that local socket completed with exit 0 and proved the obligation. The scratch `XDG_CONFIG_HOME` and `why3find.json` were outside the repository. Treat socket denial as environment denial, not as a proof failure.

## Exact successful invocations

Every invocation below was recorded as JSON with exact absolute argv, cwd, environment overrides, times, exit code, and paths to stdout/stderr in `commands/` and `logs/`. `CARGO_NET_OFFLINE=true` was set. Use the archived fixture's path in place of `$P` when replaying.

```bash
P=/tmp/ligature-p160-prototype-20261025

# Creusot, initial real proof (cwd: $P/creusot)
CARGO_HOME=/home/goya/.cargo RUSTUP_HOME=/home/goya/.rustup \
CARGO_NET_OFFLINE=true CARGO_TARGET_DIR="$P/targets/creusot-final" \
XDG_CONFIG_HOME="$P/config" \
PATH=/home/goya/.cargo/bin:/nix/store/9y9g4kpsppxn6zqmyfkvfcc2234qkdwv-creusot-wrapped/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  /home/goya/.cargo/bin/rustup run nightly-2026-04-21 \
  /nix/store/9y9g4kpsppxn6zqmyfkvfcc2234qkdwv-creusot-wrapped/bin/cargo-creusot \
  creusot --output-dir "$P/creusot"

# Verus (cwd: $P/verus/p160_verus)
CARGO_HOME=/home/goya/.cargo RUSTUP_HOME=/home/goya/.rustup \
CARGO_NET_OFFLINE=true CARGO_TARGET_DIR="$P/targets/verus" \
PATH=/home/goya/.cargo/bin:/nix/store/57l94534x07sysi7gjf4zkkpai6cw6vc-verus-tools/bin:/nix/store/3ll0vqpzkjaimvg7s0r6qw7j1vk8lgiw-creusot-wrapped/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  /home/goya/.cargo/bin/cargo +1.95.0 verus build \
  --manifest-path "$P/verus/p160_verus/Cargo.toml" --offline \
  --target-dir "$P/targets/verus" -- \
  --log-dir "$P/outputs/verus/logs" --output-json

# Exact Kani harness overlay on the Creusot crate (cwd: $P/creusot)
CARGO_HOME=/home/goya/.cargo RUSTUP_HOME=/home/goya/.rustup \
CARGO_NET_OFFLINE=true CARGO_TARGET_DIR="$P/targets/kani" \
KANI_HOME=/home/goya/.cache/kani \
PATH=/home/goya/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  /home/goya/.cargo/bin/cargo +1.95.0 kani \
  --harness increment_matches_postcondition_for_all_nonmax_inputs \
  --exact --target-dir "$P/targets/kani"

# Real later Creusot proof after Verus and Kani (cwd: $P/creusot)
CARGO_HOME=/home/goya/.cargo RUSTUP_HOME=/home/goya/.rustup \
CARGO_NET_OFFLINE=true CARGO_TARGET_DIR="$P/targets/creusot-after-kani" \
XDG_CONFIG_HOME="$P/config" \
PATH=/home/goya/.cargo/bin:/nix/store/9y9g4kpsppxn6zqmyfkvfcc2234qkdwv-creusot-wrapped/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  /home/goya/.cargo/bin/rustup run nightly-2026-04-21 \
  /nix/store/9y9g4kpsppxn6zqmyfkvfcc2234qkdwv-creusot-wrapped/bin/cargo-creusot \
  creusot --output-dir "$P/outputs/creusot-after-kani" \
  verif/p160_creusot_kani_rlib/increment.coma

# Preservation check (cwd: $P)
sha256sum -c sequence-before.sha256
```

The output pattern in the final command is deliberate: an external `--output-dir` with no pattern previously produced `No files to prove`; the explicit `.coma` pattern succeeded and wrote the proof input under the external output root. The generated output is separate from `CARGO_TARGET_DIR`. `--output-into-files` for Kani was also tried and rejected because it requires unstable `-Z`; the successful Kani run keeps stdout/stderr and the generated GOTO input instead.

## Boundary decisions for #161

**Adopt for the prototype:** independent Cargo roots are the simplest demonstrated arrangement for the distinct nightly-2026-04-21 and Rust-1.95 pins. Each owns its lockfile and `rust-toolchain.toml`; commands still explicitly use `rustup run nightly-2026-04-21`, `cargo +1.95.0`, or `cargo +1.95.0 kani` so shell cwd/default selection cannot change the compiler. A shared Cargo workspace was not tested and is not claimed to be impossible; it adds a shared lock and makes the tested root/toolchain separation less explicit without reducing the required output separation.

**Share only what was exercised:** Kani and Creusot use the same plain executable function in the Creusot crate, with verifier attributes/import gated out of Kani. Verus remains verifier-specific in its own crate. Sharing an implementation module between Verus and Creusot is untested; make it a separate #161 decision and require a compile/proof probe before relying on it.

**Keep these outputs separate:** one `CARGO_TARGET_DIR` per tool/run (`creusot`, `verus`, `kani`); Creusot's output root separate from its target root; Verus proof JSON/log directory separate from target; Kani stdout/stderr retained as logs and its `.out` kept as a proof input. Scratch targets and Why3 configuration belong in a task-specific `/tmp` root. Archive only the minimal replay fixture and human-review outputs in `analysis/p4-verifier-fit/**`; do not copy `_closure` trees as live directories.

**Proposed production tree (subject to #161 approval):**

```text
crypto-mixed/
  crates/
    crypto-mixed-core/                 # current Kani bytes layer, unchanged by #160
    crypto-mixed-creusot/              # independent Cargo root, Creusot + possible Kani overlay
      Cargo.toml
      Cargo.lock
      rust-toolchain.toml
      src/
    crypto-mixed-verus/                # independent Cargo root, Verus-specific source
      Cargo.toml
      Cargo.lock
      rust-toolchain.toml
      src/
  analysis/p4-verifier-fit/             # allowed durable plans/reports/archives
    targets-<task-id>/...               # only if operator chooses repo-local targets
    results-<task-id>/...
```

Prefer task-specific `/tmp` targets over repo-local build trees. Keep Why3 config and Unix socket runtime under the task-specific temporary root. Use external Creusot proof output with an explicit `.coma` pattern. Before production, probe where a fresh Creusot crate writes all companion proof metadata (`proof.json` included) when `--output-dir` is external; this prototype established external `.coma` placement, not a clean-tree destination for every generated file.

## Proposed write-set and creation rules

Current P3 `allowed_roots` are `crates/*/src/`, `crates/*/tests/`, findings/PORT-GAPS, oracle, `analysis/stage8c/**`, and `analysis/p4-verifier-fit/**`. Current `protected_roots` include `crates/*/Cargo.toml` and the exact existing core lock, but do not declare a general nested lockfile or nested rust-toolchain pattern. The descriptor currently declares only `crates/crypto-mixed-core`. Thus the new crate manifests are protected, and new lock/toolchain files are currently outside the allowed set. Do not create them under #160 or infer a grant from this proposal.

At #161, the operator must decide crate identities, descriptor registrations, exact compiler/dependency pins, and assurance ownership. Then explicitly decide the file policy for each new `Cargo.toml`, `Cargo.lock`, and nested `rust-toolchain.toml` (prefer narrow crate-specific protected patterns or reviewed exact entries); decide whether `analysis/p4-verifier-fit/**` remains the durable output root; and keep targets in `/tmp` unless the operator explicitly expands allowed roots. `project-descriptor.json` itself is not an allowed worker root and must be handled as an operator/human checkpoint.

For an approved declared crate, the available path is `ligature scaffold-crate --issue N --crate NAME --grant-id ID --json` under an exact active manifest grant. For an existing declared Verus crate, `configure-crate --issue N --crate NAME --profile cargo-verus --grant-id ID --json` is the typed profile path; if it refuses due unavailable `vstd`, stop and report it rather than hand-editing. There is no Creusot configure profile, and the current sanctioned verbs do not provide a general lockfile or nested toolchain writer. #161 must either establish an approved operator-managed mechanism for those protected files or authorize a narrowly scoped policy change before any worker creates them. `authorize-write` records a grant; it does not itself write a file. After any sanctioned production write, run `write-set-check --issue N --json` and the matching validator/gate. #160 issued no grants.

No CI, Cargo, descriptor, policy, shell, flake, or lockfile change is proposed as part of #160. Source files should wait for #161's human decision and a subsequent implementation issue. Keep CG1/CG3 in scope: mixed Creusot+Verus evidence in one closure still triggers CG1; Kani evidence affects the current workspace-wide CG3 check. A working coexistence layout does not establish deductive closure or assurance composition.

## Write-set and Git audit

The pre-work root and P3 statuses are preserved in `git-pre-evidence.json`. They already contained dirty issue DB/contract/submodule states and the P3 #159/upgrade paths; this work preserved them. Baseline hashes for the root flake/lock, P3 descriptor/envrc, existing core and oracle manifests/locks are in that file and are rechecked in `protected-hash-check.json`.

The post-work Ligature read-only `write-set-check --issue 160 --json` report is retained as `write-set-check.json`; actual result is `state=clean`, `violations=[]`, `mutated_workspace=false`, and `authorized_writes=[]`. Its detail also says 1343 of 1370 protected-surface files are in locations the pipeline writes nothing into and are audit-only, so the checker explicitly does not attribute those files; no new file was placed in those paths. The post-work root/P3 `git status --short --branch` and diff names are retained in `git-post-evidence.json`. The only new P3 path is this allowed analysis directory. The preexisting dirty paths remain present. No commit or push was made.

## Retained evidence

- `prototype-fixture.tar.gz` — compact archive of a 1.8 MB uncompressed fixture, including inputs, locks, toolchain files, logs, proof outputs, exact command records, 27 hash-covered earlier artifacts, the later proof hashes, and one Kani GOTO input; no `_closure` paths.
- `contents.sha256` inside the archive — per-file hashes for the archived fixture contents.
- `evidence.sha256` — hashes every other deliverable in this directory.
- `git-pre-evidence.json`, `git-post-evidence.json`, `protected-hash-check.json`, `write-set-check.json` — before/after repository and write-set evidence.
- The earlier #159 files remain unchanged under `p4-5-probes/`; no prior evidence was replaced.

## Concrete #161 decisions

1. Confirm the two independent crate identities and ownership split; decide whether the current core remains Kani-only or any executable source should be shared.
2. Approve exact Creusot/Verus/Kani compiler, verifier, std-library, and dependency pins. Resolve the current 0.14 Creusot pair before claiming the declared shell can run Creusot; the 0.12 control is not a substitute.
3. Decide the exact file policy and sanctioned creation route for descriptor entries, protected manifests, independent locks, and nested toolchain pins; no blanket grant is implied.
4. Approve separate per-tool target/output roots and the durable evidence destination; require the fresh-tree Creusot companion-output probe before production.
5. Decide closure ownership and CG1/CG3 handling for mixed deductive and Kani evidence. Build coexistence alone is not closure.

## Review corrections

The Ligature checksum above was corrected to all 64 hexadecimal characters. Seven failed-control command records previously pointed to the later successful `creusot-proof-first` logs. Six now point to their retained per-control stdout/stderr. For `creusot-proof-second`, the original output was overwritten and is explicitly marked unavailable with null output references; its recorded exit/timing alone is not independent evidence of a specific diagnostic. No verifier was rerun, and successful proof outputs and the 27 + 4 sequence hashes are unchanged.

The corrected archive SHA-256 is `b60289f053f0a0be41fe374841ea72d9d642598af9807712309fa7e5c517455b`. It supersedes `d3bc1bb6f9d5ec311b940ee7ff34ea32ecfe2b403e9e6b2307e913c7d7f17294` in the historical #160 handoff/comment retained here. `review-corrections.json` records the metadata changes. The archive contents inventory still verifies all 247 entries.

A subsequent review also corrected `commands/kani-unstable-output-file-control.command.json`: its exit-2 control now references the existing `kani-unstable-output-file-control.stdout.txt` and `.stderr.txt`, which report the required unstable-options flag. This supersedes archive hash `967e25afb5918195c4dfcb33e6143b7da0741341e2cfbc9875b8d3ff3ecf15b3`; no verifier output was changed or verifier rerun.
