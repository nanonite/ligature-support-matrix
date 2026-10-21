# Ligature issue #129 verification on v1.3.5

Date: 2026-10-12. Pilot: an isolated copy of `swisstable-verus`; the live P2 Rust source and CI assurance results were not changed by these probes. Bundle SHA-256: `1a62e34b16af64065b35708575d81249b02e5025174a27fec23c7a467cb71bd7`; attested content hash: `sha256:c0fcf84301affba6ead846db0e29477a732c6560b38158afb5ad9888dce9060c`; clean source commit: `dda2bcc73cf115e2b6db75f5c0243ab84ab6bbbf`.

## Fresh positive report

In the scratch copy, put this inner proof note in `ControlBytes::is_empty`'s `ensures` clause:

```rust
ensures
    #![verifier::proof_note("ligature:ControlBytes.C001")]
    r == self.is_empty_spec(slot as int)
```

Run the pinned Verus 0.2026.05.24.ecee80a binary:

```sh
PATH=/nix/store/57l94534x07sysi7gjf4zkkpai6cw6vc-verus-tools/bin:/nix/store/7igjywfjlfa7v2sknkd9dbvpv2s5qf6g-z3-4.15.4/bin:$PATH \
  verus --crate-type=lib --multiple-errors 200 --output-json \
  rust/swisstable-verus-core/src/lib.rs \
  > analysis/verus/issue129-135.json 2> analysis/verus/issue129-135.stderr.txt
```

Output summary: `verifier_success: True`, `verified/errors: 149 0`, and the target function had `obligation_proof_notes: ['ligature:ControlBytes.C001']`. Exit 0. Verus JSON SHA-256: `366ce2fb11acde57b59b8fce38003b4206ffc150256f0641193b9528fa708f58`.

Run Ligature:

```sh
python3 tools/ligature/ligature.pyz record-assurance WP-SWISSTABLE-VERUS \
  --verus-json analysis/verus/issue129-135.json \
  --verus-function ControlBytes.C001=lib::control_bytes::ControlBytes::is_empty
```

Output: `recorded assurance: ci/results/WP-SWISSTABLE-VERUS.json` and `ControlBytes.C001: verus-deductive-check supported -- 1 proved goal(s)`. Exit 0.

## Negative and repeatability checks

- Mismatch: bind that report to `ControlBytes.C002` while naming the same function. Exit 1: `does not bind ... to ControlBytes.C002: expected the exact Verus proof note 'ligature:ControlBytes.C002' in obligation_proof_notes`.
- Malformed JSON: pass `{broken json` as the report. Exit 2: `is not a readable Verus --output-json result` with the JSON parse location.
- Determinism: remove the output record and rerun the identical positive command against the same report. Both runs exited 0 and produced byte-identical `ci/results/WP-SWISSTABLE-VERUS.json`, SHA-256 `014773da2d28346197833c1b7a416bf82f8f01a4f1bc465b80e8ae3e48b15998`.
- Stale source: after generating that report, change the implementation from `self.bytes[slot] == EMPTY` to `self.bytes[slot] != EMPTY` without rerunning Verus. The source SHA-256 changed from `3a1153ec548a7894c50930bb74528fbbb200ad469ef69c192ad21177651b26e4` to `a0e9760013016d60355be066985b20f432b783ff6a83f5e7e52dd8c6c263d030`. Repeating the positive `record-assurance` command exited 1 with: `control_bytes.rs is newer than the Verus JSON result ... the result does not describe the current Rust sources; re-run Verus and record assurance again`. No stale record was written.

`record-assurance --help` now correctly says to put `#![verifier::proof_note("ligature:<obligation>")]` inside the `ensures` clause.

## Scope and G14 limit

These probes establish that v1.3.5 accepts a fresh Verus report, rejects mismatched, malformed, and stale evidence, and emits deterministic records. They do not demonstrate G14 closure acceptance: the live P2 pilot has no reviewed closure profile, and no profile was fabricated in the scratch copy.
