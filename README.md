### Current ligature binary: 1.3.5 (2026-10-12)

`tools/ligature/ligature.pyz` is **ligature 1.3.5**, bundle SHA-256
`1a62e34b16af64065b35708575d81249b02e5025174a27fec23c7a467cb71bd7`
(`sha256sum -c SHA256SUMS` -> OK); the attested content hash is
`sha256:c0fcf84301affba6ead846db0e29477a732c6560b38158afb5ad9888dce9060c`.
The attestation records clean source commit
`dda2bcc73cf115e2b6db75f5c0243ab84ab6bbbf`. Chainlink #43 initialized this
pilot on 2026-10-12. `status --json` reports a valid descriptor, current
installation, and pinned gate integrity. Reviewer `roger-codex-luna6` completed
the descriptor checkpoint on 2026-10-12. Existing CodeSight and upstream analysis,
tooling, oracle inputs, and workspace configuration are protected; only the
crate source/tests, the comparison ledger, and PORT-GAPS are writable; CodeSight analysis remains protected.
No Rust crate or Kani harness has been created yet.

When this pilot reaches authoring, use the 1.3.5 verbs at their workflow
boundaries: `authorize-write` issues a bounded grant; `scaffold-crate`
creates a declared crate skeleton; `generate-work-package` creates Stage 7
metadata; and `accept-policy --reviewer HUMAN --version NAME@MAJOR.MINOR`
is a human checkpoint. Do not run these early or treat a command's
availability as permission to write. Tier rules and migration severity
criteria are in [`../PROTECTED-WRITES.md`](../PROTECTED-WRITES.md) and
[`../WORKER-CONTRACT.md`](../WORKER-CONTRACT.md).

### P3 upstream baseline (Chainlink #41)

Botan 3.13.0 is pinned at commit
`2a81eef56c96c237e590c27f9a75e60317c9c700`. Its native `configure.py`/Make
build and complete upstream test suite passed: 4,124,473 tests, all OK. The
release has no CMake build files, so the documented upstream build path was
used. See the [baseline report](analysis/upstream/botan-3.13.0-baseline.md),
[full successful pass list](analysis/upstream/botan-3.13.0-make-check-success.log),
and [machine-readable source pin](upstream/upstream-pin.json).

### P3 verifier decision

Pilot: randombit/botan 3.13.0. The first pass uses **Kani only** with
`closure_kind: bounded` across the Crypto Mixed port. Verus integration is
deferred to P4, after the Kani first pass. Creusot is not selected for this
pilot.

The pinned upstream oracle uses Botan's `configure.py` and `make check`; see
the [baseline report](analysis/upstream/botan-3.13.0-baseline.md). The workspace
Nix shell is `crypto-mixed`.

### P3 Codesight analysis (Chainlink #42)

Indexed 1,199 Botan files and 15,643 symbols. The report records the scalar
ChaCha/Poly1305 paths, imports, call graph, and measured header, call-graph,
template, macro, and SIMD gaps. The pre-init `extract-c-static` diagnostic is
also captured; its comparison with Codesight is scheduled after #43 initializes
the pilot. See the [analysis report](analysis/codesight/README.md) and
[`PORT-GAPS.md`](PORT-GAPS.md).
