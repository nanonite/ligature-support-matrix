# Ligature support matrix

Workspace for porting C++ libraries to verified Rust with Ligature. Preserve
the three single-verifier baselines and add four distinct mixed-verifier
projects under [the current P4 plan](P4-MIXED-PORT-PLAN.md) (epic #154).

| Pilot | Upstream | Verifier | Where it lives |
|---|---|---|---|
| `date-creusot/` (P1) | Howard Hinnant's `date` | Creusot | submodule, branch `pilot/date-creusot` |
| `swisstable-verus/` (P2) | Abseil SwissTable | Verus | submodule, branch `pilot/swisstable-verus` |
| `crypto-mixed/` (P3) | Botan ChaCha20-Poly1305 | Kani | submodule, branch `pilot/crypto-mixed` |

Four additional roots are planned, not yet initialized:

| Planned root | Distinct upstream | Verifiers | Project epic |
|---|---|---|---|
| `icl-creusot-verus/` (M4) | Boost.ICL | Creusot + Verus | #178 |
| `tinyxml2-creusot-kani/` (M5) | TinyXML2 | Creusot + Kani | #182 |
| `snappy-verus-kani/` (M6) | Snappy | Verus + Kani | #186 |
| `leveldb-three-verifiers/` (M7) | LevelDB storage-format slice | Creusot + Verus + Kani | #190 |

This is seven project workspaces total, including the three baselines, not
every port under every verifier combination. #161 remains the human scope,
toolchain, trust and write-policy checkpoint; #177 owns later setup. The
plan update itself creates no new repo, submodule, source checkout or port.

Everything is in this one GitHub repo. Each pilot keeps its own git
repository because Ligature's work-package generation requires each pilot to
be a Git repository root. Their histories are the
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
git fetch ./swisstable-verus main:pilot/swisstable-verus && git add swisstable-verus
git commit -m "Pin pilot commits"
git push origin main pilot/crypto-mixed pilot/date-creusot pilot/swisstable-verus
```

Shared material at the root: `P4-MIXED-PORT-PLAN.md` (the current P4 plan),
`VERIFIER-MATRIX.md` (coverage and measured assurance rules),
`WORKER-CONTRACT.md`, `PROTECTED-WRITES.md`,
`oracle-PROTOCOL.md`, `rdb-divergence-workflow.md`, `findings-schema.md`,
`oracle-example/`, the Nix flake (`nix develop path:.#<pilot>`), and the
chainlink issue database in `.chainlink/`.
