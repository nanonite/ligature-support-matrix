# leveldb-three-verifiers — C++→Rust transfer gaps

This file is created at setup time (Chainlink #177). No production port has
been implemented or proved, so entries are limited to setup-visible tooling
gaps. Intake #191 must add source-bound gaps with pinned
`file:line` locations before any implementation claim.

### SETUP-001 — Creusot external proof output does not isolate every companion file

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** n/a (verifier tooling; applies to every C++ source in this root)
- **What the Rust port does instead:** `cargo-creusot 0.12.0-dev` writes the
  generated `.coma` under an external `--output-dir`, but writes
  `verif/<crate>/<file>/proof.json` and the `.why3find/` cache inside the crate,
  and `--only prove` will not consume a `.coma` that exists only under the
  external output root.
- **Why:** Verified in the #177 probe; the proof driver resolves patterns under
  the crate's `verif/` tree and keeps its companion metadata there.
- **Impact:** A durable per-run proof record needs a fresh crate/target plus an
  explicit copy/allowlist step for `proof.json` and `.why3find/`; the external
  output root alone is not a complete evidence boundary.
- **Status:** open
- **Finding ids:** `leveldb-three-verifiers-004`
- **Generalizable lesson:** An external verifier output directory is not proof
  that the source tree stayed clean; enumerate every companion artifact before
  treating a proof run as reproducible evidence.

