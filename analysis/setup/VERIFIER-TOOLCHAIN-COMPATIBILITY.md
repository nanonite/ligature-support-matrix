# Snappy verifier compatibility record

Local pilot record for `snappy-verus-kani`; this is not a Ligature 1.4.3
upstream support claim and not a production proof.

| Verifier | Measured version | Synthetic result | Limit |
|---|---|---|---|
| Verus | `0.2026.05.24.ecee80a`, Rust `1.95.0` | Synthetic obligation succeeded, one verified, zero errors | Does not prove Snappy behavior. |
| Kani | `cargo-kani 0.67.0`, CBMC `6.8.0`, Rust `1.95.0` | Synthetic harness succeeded, zero failures | Bounded synthetic coverage only; no codec/source claim. |

Ligature bundle: `1.4.3`, SHA-256
`1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1`.
The enclosing workspace aggregates the same matrix and Nix hashes in
`planning/p4-mixed-2026-10-26/setup/LIGATURE-VERIFIER-COMPATIBILITY.md`.
That sibling file is not required to use this independent Git root.

Before production use, Ligature must provide a reproducible per-root verifier
environment and publish its tested verifier matrix. The current declared
workspace Creusot shell mismatch remains open on epic #2; no Creusot tool is
part of this project's selected matrix.
