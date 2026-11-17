# Setup evidence index (#177)

All probes are synthetic setup probes. They establish tool availability and
artifact placement only; they do not validate a P4 project, port, proof or
Ligature intake.

| Path | What it shows |
|---|---|
| `declared-shell-creusot.txt` | declared flake shell resolves `cargo-creusot 0.14.0-dev` / nightly-2026-08-03 (the unresolved epic #2 mismatch) |
| `creusot-0.12-probe/creusot-version.txt` | `cargo-creusot 0.12.0-dev`, nightly-2026-04-21, Why3/why3find/prover versions |
| `creusot-0.12-probe/compile-local.log` | local compile writes `verif/<crate>/<file>.coma` |
| `creusot-0.12-probe/compile-external.log` | external `--output-dir` writes the `.coma` outside the crate |
| `creusot-0.12-probe/prove.log` | `Proved (verif/p4_setup_creusot_probe_rlib/increment.coma) ✔` |
| `creusot-0.12-probe/why3-config-detect.log` | local Why3 configuration finds 14 provers under a private XDG root |
| `creusot-0.12-probe/why3-socket-trace.txt` | traced `AF_UNIX` bind/connect/accept on the Why3 server socket during a successful proof |
| `creusot-0.12-probe/probe-result.json` | machine-readable result, including companion-output placement |
| `creusot-0.12-probe/nix-path-info.json` | NAR hashes identifying the exact 0.12 wrapper and `creusot-std` source store paths |
| `creusot-0.12-probe/generated-files.txt` | exact generated-file inventory |
| `verus-1.95-probe/probe-result.json` | Verus 0.2026.05.24.ecee80a / Rust 1.95.0 result |
| `verus-1.95-probe/verus-build.extract.txt` | proof-result extract (`success=true`, `verified=1`, `errors=0`) |
| `kani-0.67-probe/probe-result.json` | Kani 0.67.0 / Rust 1.95.0 result |
| `kani-0.67-probe/kani.log` | `SUMMARY: 0 of 3 failed`, `VERIFICATION:- SUCCESSFUL` |
| `smoke-<root>.log` | per-root smoke check and probe output (all exit 0) |
| `protected-mtime-check.txt` | no baseline-root file (outside scratch/evidence trees) was modified after the run start; root flake/lock/.gitmodules hashes |

Reproduce the Creusot probe from the workspace root:

```bash
planning/p4-mixed-2026-10-26/setup/probes/creusot-0.12-probe.sh /tmp/p4-creusot-probe
```

The Nix store paths are the operator-selected existing 0.12 pair. The current
workspace flake does not build them; resolving that reproducible route is part
of the epic #2 0.14 mismatch. If a store path is garbage-collected, set
`P4_CREUSOT_WRAPPER` / `P4_CREUSOT_STD_SRC` to an equivalent matching pair; do
not substitute the 0.14 shell.
