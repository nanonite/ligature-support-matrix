# Ligature support matrix

Workspace for porting C++ libraries to verified Rust with Ligature, one pilot
per verifier, and for planning the mixed-verifier matrix (chainlink epic #154).

| Pilot | Upstream | Verifier | Where it lives |
|---|---|---|---|
| `date-creusot/` (P1) | Howard Hinnant's `date` | Creusot | submodule, branch `pilot/date-creusot` |
| `swisstable-verus/` (P2) | Abseil SwissTable | Verus | tracked in `main` |
| `crypto-mixed/` (P3) | Botan ChaCha20-Poly1305 | Kani | submodule, branch `pilot/crypto-mixed` |

Everything is in this one GitHub repo. `crypto-mixed/` and `date-creusot/`
keep their own git repositories because Ligature's work-package generation
requires each pilot to be a Git repository root. Their histories are the
`pilot/<name>` branches here, and `main` pins the exact pilot commit as a
submodule pointing back at this same repo. Clone everything with:

```sh
git clone --recurse-submodules git@github.com:nanonite/ligature-support-matrix.git
```

After new commits in a pilot, update its branch and pin from the workspace
root, then commit and push `main` together with the branch:

```sh
git fetch ./crypto-mixed main:pilot/crypto-mixed && git add crypto-mixed
git fetch ./date-creusot main:pilot/date-creusot && git add date-creusot
git commit -m "Pin pilot commits"
git push origin main pilot/crypto-mixed pilot/date-creusot
```

Shared material at the root: `WORKER-CONTRACT.md`, `PROTECTED-WRITES.md`,
`oracle-PROTOCOL.md`, `rdb-divergence-workflow.md`, `findings-schema.md`,
`oracle-example/`, the Nix flake (`nix develop path:.#<pilot>`), and the
chainlink issue database in `.chainlink/`.
