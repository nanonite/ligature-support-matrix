# Chainlink #31 — Stage 8A evidence

Initial run date: 2026-10-09; closeout rerun: 2026-10-10. Pilot:
`swisstable-verus/`. Ligature is the installed 1.3.3 bundle, SHA-256
`f0028d88a516be9c1c8c097f024286e1b28af6e5b38db8a49c4d047ffe45c1e1`, verified
with `(cd tools/ligature && sha256sum -c SHA256SUMS)`. Its reported content
hash is `sha256:1b8fd50a65e79138486119c6876a30402ae45ca84dd914ac6edef45e85a3f0d5`.

## C_static extraction and R1/G16

The target was taken from the installed Rust toolchain's `rustc -vV` host:
`x86_64-unknown-linux-gnu`. The extractor wrote
`ci/results/c_static/rust_swisstable-verus-core.json` (SHA-256
`3bd92f9127a08f86e0fec9de742adb22b14efe3ddfcbabf88e6ef7720215d75c`). The
report explicitly says its completeness claim is `discovered-lower-bound`;
it is not a complete call graph. It records 277 discovered, 46 resolved, and
231 unresolved callsites. Its attribution metadata records 305 out-of-scope
and 815 unattributed callsites.

| Command | Exit | Result |
|---|---:|---|
| `extract-c-static --target x86_64-unknown-linux-gnu` | 0 | Wrote the report above. |
| `validate-callsites` | 0 | All discovered reports pass G1a/G1b, including recomputed callsite coverage and callee shapes. This validates the report's structure, not graph completeness. |
| `gate-r1-g16` | 1 | 5 high R1 findings plus 462 medium, extractor-default risk decisions. |

The five definite cross-concept calls absent from the promoted interaction set
are:

- `CS-RAWTABLE-NEW-001`: `RawTable.new -> ControlBytes.new`
- `CS-RAWTABLE-NEW-SEQ-001`: `RawTable.new_seq -> ProbeSeq.new`
- `CS-RAWTABLE-INSERT-001`: `RawTable.insert -> HashMix.new`
- `CS-SWISSTABLE-NEW-001`: `SwissTable.new -> RawTable.new`
- `CS-SWISSTABLE-ITER-001`: `SwissTable.iter -> TableIterator.new`

All 15 interaction specs in the pilot are still staged as `.draft` files, so
the gate has no promoted interaction declarations to reconcile against. Its
next action is to author/update an interaction for the first missing edge.
That requires the normal spec review checkpoint; no spec was approved or
hand-edited in this run. The 462 G16/R1 risk decisions also remain for the
operator. A successful `validate-callsites` run does not resolve them. The
review inventory is
[`r1-g16-review-inventory.csv`](r1-g16-review-inventory.csv): 231 R1
possible-dispatch decisions and 231 G16 unresolved-call decisions, all marked
`PENDING HUMAN REVIEW` with no dispositions inferred.

## Bridge and witness commands

| Command | Exit | Result |
|---|---:|---|
| `check-bridges` | 0 | `0 artifact(s) written`; there are no promoted bridges to compile or dispatch. This is not a bridge-check pass. |
| `validate-witness` | 0 | Nothing to check: no witness artifacts were discovered. The two witness specs remain `.draft` files. |
| `render-witness --renderer group_bitmask W-CONTROLBYTES-COUNTEMPTY-001` | 1 | No genuinely valid canonical result exists under `ci/results/witnesses/`. |

The descriptor has no `witness_backend` or `verifier_backends` command, and no
canonical witness results exist. `check --json` therefore reports G9 and
G18–G20 as `not-applicable` for absent promoted artifacts; those outcomes are
not passes. No backend or descriptor change was made.

## Workspace status

After extraction, `check --json` exited 1 with conditions
`blocking_findings` and `human_decision_required`: 508 findings total (5 high
blocking, 41 informational, 462 medium human decisions). `status --json`
exited 0, reported the 1.3.3 installation current and gate integrity pinned,
and listed 462 pending human decisions. `doctor` exited 0. The
`write-set-check --issue 31 --json` exited 0 with zero violations; the new
C_static report is in the canonical generated-results path. No Rust source,
descriptor, promoted spec, or verifier backend was changed.

The complete issue result is a gate-blocked Stage 8A checkpoint, not a clean
assurance result. The R1/G16 blocker is recorded as
`swisstable-ligature-015` in `findings/limitations.jsonl` and in `PORT-GAPS.md`.

## Closeout — 2026-10-10

The Stage 8A commands were rerun for closeout against the checksum-verified
Ligature 1.3.3 bundle. Their output was:

```text
$ sha256sum -c SHA256SUMS
ligature.pyz: OK
$ python3 tools/ligature/ligature.pyz extract-c-static --target x86_64-unknown-linux-gnu
wrote /home/goya/storage/full-ligature-port-workspace/swisstable-verus/ci/results/c_static/rust_swisstable-verus-core.json: 277 discovered, 46 resolved, 231 unresolved (discovered-lower-bound)
$ python3 tools/ligature/ligature.pyz validate-callsites
OK: all C_static reports pass G1a/G1b (incl. recomputed callsite coverage and callee shapes) (1 discovered)
$ python3 tools/ligature/ligature.pyz gate-r1-g16
INFO: 41 non-blocking finding(s)
FAIL: 5 blocking finding(s)
exit=1
$ python3 tools/ligature/ligature.pyz --workspace "$PWD" check-bridges
OK: 0 artifact(s) written; every promoted bridge compiled and was dispatched
$ python3 tools/ligature/ligature.pyz validate-witness
OK (nothing to check: no witness artifacts discovered under .)
$ python3 tools/ligature/ligature.pyz render-witness --renderer group_bitmask W-CONTROLBYTES-COUNTEMPTY-001
error: no genuinely valid canonical result for witness_id 'W-CONTROLBYTES-COUNTEMPTY-001' under ci/results/witnesses/ -- run the fixture producer first, then `pipeline.py validate-witness --results` to confirm it is valid before generating from it
$ python3 tools/ligature/ligature.pyz check --json
"result":{"conditions":["blocking_findings","human_decision_required"],"exit_code":1}
```

The structured check result contained 5 high, 41 informational, and 462
medium findings; the 462 medium findings require individual risk decisions.

The bridge check had zero promoted bridges to compile or dispatch, and witness
validation found no witness artifacts; neither zero-input result is treated as
a pass. The five R1 blockers and all 462 R1/G16 human decisions remain
documented and unresolved. The 462-item inventory remains pending review; the
scope decision below does not silently disposition those callsites.

Operator scope decision: this port is **Verus-only**. Kani was intentionally
excluded from the port. Supporting multiple verifiers through one Ligature
binary is a separate phase that needs its own design across the three
verifiers. The accepted limitations recorded for this port do not authorize a
Kani cluster, mixed-verifier support, or a descriptor change. No Rust source,
descriptor, promoted spec, or verifier backend was changed for #31.

Closeout safeguards: `write-set-check --issue 31 --json` exited 0 with
`"state":"clean"` and `"violations":[]`; its output still notes eight
pre-existing protected files without a declaration, as audit-only. `doctor`
and `status --json` exited 0; status reported the installation current and
gate integrity pinned. The workspace-root `flake.nix` and `flake.lock` MD5s
were `8a3fdb4742c8aa8488ea889413611fa3` and
`f4bf5566bd4b89f6a6db076eb937f83d` before and after this closeout. The pilot
descriptor SHA-256 remained
`e19f79e9c1c1c1b83f0633b56aaf50498694cf6eba4f56812a44d7b3ab29b4f0`.
