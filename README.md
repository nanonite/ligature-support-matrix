# Ligature support matrix

Workspace for porting C++ libraries to verified Rust with Ligature, one pilot
per verifier, and for planning the mixed-verifier matrix (chainlink epic #154).

| Pilot | Upstream | Verifier | Where it lives |
|---|---|---|---|
| `date-creusot/` (P1) | Howard Hinnant's `date` | Creusot | nested repo, branch `pilot/date-creusot` |
| `swisstable-verus/` (P2) | Abseil SwissTable | Verus | tracked in this repo |
| `crypto-mixed/` (P3) | Botan ChaCha20-Poly1305 | Kani | nested repo, branch `pilot/crypto-mixed` |

`crypto-mixed/` and `date-creusot/` keep their own git repositories because
Ligature's work-package generation requires each pilot to be a Git repository
root. This repo ignores them; their histories are published to this remote as
the `pilot/<name>` branches. To refresh a branch from the workspace root:

```sh
git fetch ./crypto-mixed main:pilot/crypto-mixed
git fetch ./date-creusot main:pilot/date-creusot
```

Shared material at the root: `WORKER-CONTRACT.md`, `PROTECTED-WRITES.md`,
`oracle-PROTOCOL.md`, `rdb-divergence-workflow.md`, `findings-schema.md`,
`oracle-example/`, the Nix flake (`nix develop path:.#<pilot>`), and the
chainlink issue database in `.chainlink/`.
