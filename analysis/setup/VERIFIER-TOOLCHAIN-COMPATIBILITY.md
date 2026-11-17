# LevelDB verifier compatibility record

Local pilot record for `leveldb-three-verifiers`; this is not a Ligature
1.4.3 upstream support claim and not a production proof.

| Verifier | Measured version | Synthetic result | Limit |
|---|---|---|---|
| Creusot | `cargo-creusot 0.12.0-dev`, matching `creusot-std 0.12.0-dev`, `nightly-2026-04-21` / rustc `1.97.0-nightly` | P4 synthetic obligation proved, exit 0 | Does not validate the declared 0.14 shell or LevelDB contracts. |
| Verus | `0.2026.05.24.ecee80a`, Rust `1.95.0` | Synthetic obligation succeeded, one verified, zero errors | Does not prove LevelDB behavior. |
| Kani | `cargo-kani 0.67.0`, CBMC `6.8.0`, Rust `1.95.0` | Synthetic harness succeeded, zero failures | Bounded synthetic coverage only; no storage-format/source claim. |

Ligature bundle: `1.4.3`, SHA-256
`1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1`.
The enclosing workspace aggregates the same matrix and Nix hashes in
`planning/p4-mixed-2026-10-26/setup/LIGATURE-VERIFIER-COMPATIBILITY.md`.
That sibling file is not required to use this independent Git root.

Before production use, Ligature must supply a reproducible per-root Nix pin
and publish its tested verifier matrix. The matching local Creusot 0.12 store
output is not a portable flake pin; the declared 0.14 shell mismatch remains
open on epic #2.
