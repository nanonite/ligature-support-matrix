# icl-creusot-verus durable verification evidence

Each proof/verifier run gets its own `<run-id>/` directory, with one
subdirectory per verifier crate. Do not share a proof output, target
directory or cache between tools or runs.

| Crate | Durable evidence path |
|---|---|
| `icl-creusot` | `analysis/verification/<run-id>/icl-creusot/` |
| `icl-verus` | `analysis/verification/<run-id>/icl-verus/` |

Rules:

- Compiler targets are task-specific `/tmp` roots, never this tree.
- Creusot writes the `.coma` to the crate's `verif/` tree by default and
  to an external `--output-dir` only on the compile step. `proof.json` and
  `.why3find/` stay crate-local; copy them into `<run-id>/<crate>/` before
  teardown and record the exact command and hashes.
- Verus proof JSON/logs and Kani stdout/GOTO evidence are stored per run
  under the same convention.
- Add a machine-readable command record (argv, cwd, env overrides, exit
  code, inputs/outputs) with every retained result.
- Evidence is setup/proof evidence, not a production or closure claim.
