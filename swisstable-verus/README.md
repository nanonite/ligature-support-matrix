# SwissTable Verus Pilot
Pilot: abseil/abseil-cpp
Owning verifier: Verus
Intended closure_kind: deductive
Nix shell: swisstable-verus
Plan: /home/goya/.claude/plans/based-on-this-preliminary-gleaming-salamander.md

## Current ligature binary: 1.3.5 (2026-10-12)

`tools/ligature/ligature.pyz` is **ligature 1.3.5**, bundle SHA-256
`1a62e34b16af64065b35708575d81249b02e5025174a27fec23c7a467cb71bd7`
(`sha256sum -c SHA256SUMS` -> OK); the attested content hash is
`sha256:c0fcf84301affba6ead846db0e29477a732c6560b38158afb5ad9888dce9060c`.
The attestation records clean source commit
`dda2bcc73cf115e2b6db75f5c0243ab84ab6bbbf`. `migrate --upgrade --json`
reported `result: current`, updating the installed product from 1.3.4 with no
changed paths, conflicts, or required human actions. `status --json` reports a
valid descriptor, current installation, and pinned gate integrity; `doctor`
exits 0 and `write-set-check --json` reports clean.

`check --json` still exits 1 on the existing R1/G16 review findings; G14 is
not applicable because this pilot has no closure profiles. These are project
stage conditions, not migration failures. The v1.3.5 `record-assurance`
Verus path was independently rechecked in an isolated P2 copy; detailed command
outputs are in [`analysis/ligature/issue129-v1.3.5.md`](analysis/ligature/issue129-v1.3.5.md), with the issue inventory in
[`analysis/ligature/p2-binary-issues.md`](analysis/ligature/p2-binary-issues.md).

For #30, `configure-crate` completed under exact-path one-shot grant
`GW-264d36df32dd`. It resolved Verus `0.2026.05.24.ecee80a`, Rust
`1.95.0-x86_64-unknown-linux-gnu`, and the exact vstd pin
`0.0.0-2026-05-24-0157`; Cargo metadata/check, Cargo-Verus verify/build, Cargo
test, and Cargo.lock preservation all passed. The profile audit records the
selected manifest changing from SHA-256
`d0ee5d30955cde4946b4875d6f81c25ca06c810af407de82bff1c21389156f4c` to
`ccc7fd83f3131f66d926b49ec80008297667b52f9aa255d7cf6df6593a198d54`.
`write-set-check --issue 30 --json` reports clean and the grant spent. No
project-root Cargo.toml was added.

The human policy checkpoint was accepted on 2026-10-08 through the sanctioned
`accept-policy` command, with reviewer `codex` and version
`swisstable-verus-reliance-policy@1.0`. It stamped only the `Policy version:`
marker; the acceptance record reports previous hash
`sha256:36f20f198ab1de91a2dabed8242ce1a2c1a5edc4f841803f62b6e5bd24e2eea9`
and accepted hash
`sha256:e9ec56e11ac44d799f2f763bf166869b029ca3e284f75c15d6004b4928bb0c1b`.

Fresh live verification of the nested crate completed with `CARGO_TARGET_DIR`
under `/tmp`; `Cargo.toml`, `Cargo.lock`, and `src/lib.rs` hashes were unchanged
by the run. `cargo verus verify --locked` and `cargo verus build --locked` each
reported `1690 verified, 0 errors` for vstd and `149 verified, 0 errors` for
the crate. `cargo test --locked` exited 0 and discovered 0 runtime tests. The
crate `Cargo.lock` hash remained
`aced43d91cbfc6b486e85741265b9d10269832209ba9b23f022bca39e7154f9a`; no
project-root Cargo.toml was added.

After acceptance, `doctor`, `check --json`, and `write-set-check --issue 30
--json` all exited 0; status is current with gate integrity pinned and no open
findings. The write-set check reports no violations; it separately lists seven
staged spec drafts as audit-only/unvouched. Those drafts were not part of this
configuration or verification run. `PORT-GAPS.md` and
`findings/limitations.jsonl` document the scope cuts, verifier limits, and
runtime/oracle parity had not yet been implemented at that #30 closeout. Issue #32 added runtime
differential checks for a bounded map-operation subset; the coverage limits
and evidence are recorded below and in
[analysis/ligature/stage8b/issue32.md](analysis/ligature/stage8b/issue32.md).

Chainlink #30 is closed after the human policy checkpoint and these passing
gates. Local escalation #124 is also closed as fixed by the installed 1.3.3
bundle.

### Chainlink #31 Stage 8A checkpoint and closeout (2026-10-10)

The Stage 8A evidence was first run on 2026-10-09 and rerun for closeout on
2026-10-10. The current C_static report is the installed extractor's
discovered lower bound: 277 callsites discovered, 46 resolved, and 231 unresolved. Its
G1a/G1b callsite validation passes, while R1/G16 exits 1 with five missing
cross-concept interactions and 462 human risk decisions. Bridge and witness
commands found no promoted inputs or canonical results; their zero-input
outputs are not passes. The full command record is
[`analysis/ligature/stage8a/issue31.md`](analysis/ligature/stage8a/issue31.md).
Its linked review inventory itemizes all 462 pending R1/G16 decisions.
The R1/G16 blocker is documented as `swisstable-ligature-015` in
`PORT-GAPS.md` and `findings/limitations.jsonl`.
The operator confirmed this pilot is Verus-only by intent: Kani and support for
multiple verifiers through the same Ligature binary belong to a later phase.
This scope decision leaves the recorded R1/G16 findings and individual risk
decisions unresolved; it does not add a Kani cluster or change the descriptor.

### Chainlink #32 Stage 8B bounded differential oracle (2026-10-10)

The oracle builds against pinned Abseil 20260817.0 at commit
2065f4ded0558c6f89fee67c8e5228feb4eb960e. It runs 14 deterministic cases:
two translated upstream tests (FlatHashMap.EraseIf and FlatHashMap.Reserve),
four boundary cases (one explicitly excluded for key zero), and eight
SplitMix64-v1 sequences with seed 20261010. The driver and Rust tests compare
each action result, size, and sorted contents; they do not compare capacity,
allocation, pointer/reference stability, traversal order, hash placement, or
performance.

[oracle/test-map.csv](oracle/test-map.csv) inventories 409 source-declared tests from the eleven
SwissTable-relevant upstream test files. Two are mapped to comparable nextest
cases; the rest are explicitly unmapped because their test behavior is outside
this specialized u64 map API (including generic/node storage, allocator and
lifetime behavior, iteration/sanitizer behavior, internal control-byte/SIMD
details, or unrelated inlined-vector behavior). Typed-test template
instantiations are represented once at their source declaration and are not
claimed as separate mapped runtime cases. The 14-case comparison passed; this
establishes parity only for the mapped observable subset. Full commands,
deterministic regeneration checks, JUnit location, and scope limits are in
[analysis/ligature/stage8b/issue32.md](analysis/ligature/stage8b/issue32.md).
No mismatch occurred, so the rdb
divergence workflow was not invoked. The oracle work adds no Kani or
mixed-verifier scope and leaves the descriptor and production Rust modules
unchanged.

### Historical 1.2.2 protected-write state in this pilot

- Issue #30: operator-approved supervisor identity `opencode-swisstable-t1`
  and exact `PORT-GAPS.md` allowed root are recorded. One-shot grant
  `GW-c2008009a9d2` was consumed by
  `scaffold-crate --issue 30 --crate swisstable-verus-core`; the write-set
  check was clean at that checkpoint. The generated manifest was intentionally
  minimal; that is historical, not the current manifest state documented
  above. `scaffold-crate` is create-only; it is not a manifest editor, and a
  second grant alone would not authorize a hand edit under
  `PROTECTED-WRITES.md`.
- The port's proof-only imports now use `#[cfg(verus_only)]`. In a disposable
  copy with Verus's pinned Cargo template, the crate passes Cargo-Verus
  verification (150/0), `cargo build`, and `cargo test` (0 tests discovered).
  The live direct-Verus runner also passed 150/0 at that checkpoint. The
  current live manifest/profile state and the 1.3.1 configuration refusal are
  recorded at the top of this README. Issue #30 remains open.
- Stage 7 / issue #29: `generate-work-package` now generates the canonical
  manifest from a structured plan, issue, toolchain, target, and features,
  under a matching protected-write grant. The existing manifest was
  hand-authored under 1.2.1; do not regenerate it blindly.
- After a sanctioned write, run `write-set-check --issue N --json` and the
  command-specific validator. Full tier and migration severity rules are in
  [`../PROTECTED-WRITES.md`](../PROTECTED-WRITES.md) and
  [`../WORKER-CONTRACT.md`](../WORKER-CONTRACT.md).

The remaining command transcripts below are mostly historical 1.2.1/1.2.2
measurements unless explicitly marked as re-run on the 1.3.1 pilot candidate.
In particular, an old `doctor` exit 0 does not describe the current
policy-placeholder state.

## Upstream pin and parity baseline (chainlink #25)

Upstream: `abseil/abseil-cpp`, cloned to `upstream/abseil-cpp/`.

- commit `2065f4ded0558c6f89fee67c8e5228feb4eb960e`
- tag `20260817.0` (LTS release, not master HEAD) — `git describe --tags --always`
  reports `20260817.0` and the tag points at this commit
- commit date `2026-08-18T08:53:30-04:00`, subject
  `Apply LTS transformations for 20260817 LTS branch (#2129)`
- `project(absl LANGUAGES CXX VERSION 20260817)`, `ABSL_SOVERSION 2608.0.0`

The machine-readable form of the pin, including the exact build configuration,
is `upstream/upstream-pin.json`. As in P1, the pin does **not** live in
`project-descriptor.json`: `port_source` is `additionalProperties: false` with
only `repository` / `language` / `oracle_build_command` (chainlink #72), so
`commit` has nowhere to go and the pin lives in pilot-owned files only. The
root was ligature-initialised by #27; see below.

Build and test, inside the pilot Nix shell, with
`analysis/upstream/build-upstream.sh`. It mirrors upstream
`ci/linux_gcc-latest_libstdcxx_cmake.sh` and pins GoogleTest to the 1.17.0
release the pinned checkout itself records in `ci/cmake_common.sh`:

```
cmake -G Ninja -S upstream/abseil-cpp -B /tmp/opencode/swisstable-verus-abseil-build \
  -DABSL_GOOGLETEST_DOWNLOAD_URL=https://github.com/google/googletest/releases/download/v1.17.0/googletest-1.17.0.tar.gz \
  -DABSL_BUILD_TESTING=ON -DBUILD_SHARED_LIBS=OFF -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_STANDARD=17
cmake --build /tmp/opencode/swisstable-verus-abseil-build -j 24
TZDIR=upstream/abseil-cpp/absl/time/internal/cctz/testdata/zoneinfo \
  ctest --test-dir /tmp/opencode/swisstable-verus-abseil-build -j 24 --output-on-failure
```

Result: `100% tests passed, 0 tests failed out of 242`, three times: twice over
one build tree, and once over a from-scratch build into a second, empty build
directory, to confirm `analysis/upstream/build-upstream.sh` is self-contained.
`ctest --output-junit` independently reports
`tests="242" failures="0" disabled="0" skipped="0"`.

The parity baseline is `upstream/test-baseline.txt` — 242 CTest tests, all
`pass`, which is 9357 gtest cases across 1146 gtest suites. It is generated by
`analysis/upstream/make-test-baseline.py` from
`analysis/upstream/ctest-results.xml`; the raw transcript is
`analysis/upstream/build-and-test.log`.

The SwissTable-relevant tests in that baseline, all passing, are the ones the
port has to stay consistent with: `absl_raw_hash_set_test`,
`absl_raw_hash_set_allocator_test`, `absl_raw_hash_set_resize_impl_test`,
`absl_flat_hash_set_test`, `absl_flat_hash_map_test`, `absl_node_hash_set_test`,
`absl_node_hash_map_test`, `absl_hashtable_control_bytes_test`,
`absl_hashtablez_sampler_test`, `absl_inlined_vector_test`,
`absl_inlined_vector_exception_safety_test`.

Note on the toolchain: the devShell has no `ninja`, so the build used the one on
`PATH` (`~/.local/bin/ninja`), and CMake selected `clang++ 21.1.7` rather than
the shell's `g++ 14.3.0`. Both are recorded in `tools/versions.lock` and
flagged on epic #2.

## codesight-mcp analysis of the subset (chainlink #26)

`analysis/codesight/` holds the whole analysis: 142 recorded tool calls (each
with its raw stdout and a `.exit` sidecar), the derived censuses, 13 controlled
tree-sitter probes, and `analysis/codesight/README.md`, which is the thing to
read. `analysis/codesight/run-all.sh` regenerates every artefact;
`analysis/codesight/summarize-results.py` tabulates them.

Headline, for anyone about to use this index for the port:

- The index is deterministic and reproducible (`index-determinism.sh`).
- `.h` is parsed as **C**, not C++: all 183 indexed headers, all 490 `.cc`
  files correctly `cpp`. Class scope is therefore lost in every header, which
  both hides the subset's defining symbols and produces confidently wrong call
  edges — `raw_hash_set.h::assert_is_full` is reported as calling
  `absl/container/internal/btree.h`'s `generation`.
- 226 of the 900 on-disk C/C++ sources (202 `.h`, 24 `.inc`) are silently absent
  while `index-folder` reports `"success": true`, including
  `absl/container/internal/raw_hash_map.h`.
- Consequence for the six subset areas: group probing's scalar half has a real
  graph; the SIMD half, the class-level erase path and the entire rehash
  template layer have no resolvable defining symbol at all.
- Usable for: `.cc`-level callers/callees/impact inside `raw_hash_set.cc`, and
  forward imports of `raw_hash_set.cc` / `raw_hash_set.h`.
- Not usable for: type hierarchy, reverse imports, call chains across subset
  areas, or any edge whose endpoint is a bare `.h` name.

The disagreement axis this issue asked for — codesight-mcp vs
`ligature extract-c-static` — could not be measured: `extract-c-static` needs a
`project-descriptor.json`, this root had none yet (init is #27), and the command
dies with an unhandled `FileNotFoundError` where `status`/`check`/`doctor` all
degrade gracefully. Escalated as **epic #1 #107**; transcript at
`analysis/ligature/extract-c-static-transcript.txt`. #27 has since supplied the
descriptor, so this axis is now unblocked and is owned by #108.

13 findings are in `findings/limitations.jsonl`, generated by
`analysis/codesight/write-findings.py`; the severities that matter for planning
are `swisstable-mcp-001` and `swisstable-mcp-003` (both `blocker`),
`swisstable-mcp-002` and `swisstable-mcp-004` (both `scope-cut`), and
`swisstable-ligature-001` (`blocker`).

## ligature init + project descriptor (chainlink #27)

`python3 tools/ligature/ligature.pyz init --mode port` against ligature 1.2.0
(sha256 `9c921eeb1bbb858c0041e49f07cf5d06988eb798ba60b9207f7576cba430637c`,
`sha256sum -c SHA256SUMS` -> `ligature.pyz: OK`). The complete evidence file is
`analysis/ligature/init-check.txt`: pre-init and post-init `status`,
`status --json`, `doctor` and `check --json`, the filled descriptor, the
re-run of `port_source.oracle_build_command`, and eight probes of the schema
and the policy read-back. Reproduced post-init:

```
$ python3 tools/ligature/ligature.pyz status
descriptor: present-valid (project-descriptor.json)
installation manifest: current
gate integrity: pinned -- 4 gate path(s) match the installed manifest
open findings: 0
exit=0

$ python3 tools/ligature/ligature.pyz check --json
findings: 0    exit_code=0    conditions=[]
next action: [refresh-c-static] no C_static reports at ci/results/c_static/
  run: ligature extract-c-static --target <target-triple>

$ python3 tools/ligature/ligature.pyz write-set-check --json
write_set.state = "clean", violations = [], exit=0

$ python3 tools/ligature/ligature.pyz doctor
  user-owned  project-descriptor.json  schema: valid
  adjudicator pin: pinned -- running executable matches the recorded adjudicator
exit=0
```

The two intent fields this issue exists to fix, both set before any Rust code
existed (`rust/` held only `.gitkeep`), and read back by the tool itself:

```
$ python3 tools/ligature/ligature.pyz status --json | jq .descriptor
{
  "closure_kind": "deductive",
  "mode": "port",
  "path": "project-descriptor.json",
  "schema_version": "1.0",
  "state": "present-valid",
  "verifier_policy": {
    "clusters": {},
    "default": "verus",
    "supporting": []
  }
}
exit=0
```

Decisions, each with its evidence, are in the `### DECISIONS, AND WHY` section
of `analysis/ligature/init-check.txt`. The three that a later issue could
mistake for an accident:

- **`closure_kind: "deductive"`** is the top-level descriptor field the issue
  asked for. P1's side record for this (`analysis/ligature/closure-intent.json`
  in `date-creusot/`) is obsolete; no side record exists or is needed here.
- **`verifier_policy` remains Verus-only for this port.** #35 found no
  unsafe/raw-pointer layer in the Rust crate: the current storage is initialized
  parallel Vecs, so there is no unsafe component to route to Kani. The physical
  lifetime, layout and pointer-stability difference remains the transfer gap in
  `PORT-GAPS.md`. #36 records the current SIMD implementation as a scope cut;
  do not add Kani support unless a future implementation introduces a
  Kani-owned component.
- **`crates[0].contracts_crate` is `verus_contracts`**, not the init
  template's Creusot-flavoured `contracts`. Revisit when #30 creates the crate,
  if the real facade name differs.

`write_set.protected_roots` uses crate-scoped globs — `rust/*/Cargo.toml`,
`rust/*/build.rs` — not the init template's `**/Cargo.toml` / `**/build.rs`,
which overlap the allowed `rust/*/src/` roots and are what P1 hit at Stage 7's
G13 (#105). Nothing at P0 rejects the `**` forms: probe P7 in the evidence file
shows a `**/Cargo.toml` descriptor is `present-valid` and write-set-clean here,
so the overlap only surfaces three stages later.

Three findings were added to `findings/limitations.jsonl` by
`analysis/ligature/write-findings-27.py` (idempotent; the 13 pre-existing lines
are byte-identical): `swisstable-ligature-002` (`doctor` ignores the global
`--descriptor` flag — a false clean verdict on an invalid descriptor; escalated
as **epic #1 #109**), `swisstable-ligature-003` (the `**/Cargo.toml` template
default is accepted at P0) and `swisstable-ligature-004` (an unknown key inside
`verifier_policy` is silently accepted and surfaces only as a phantom entry in
`status --json`'s `clusters` map). All three are `friction`; none blocked this
issue.

## Stages 0-3: the drafted artifact set, and the OPERATOR RUNBOOK (chainlink #28)

Everything in this section is worker-reachable work plus the human checkpoints that
are deliberately **not** taken. Nothing under `specs/`, `rust/*/specs/` or
`specs/_conflicts/` was written by hand: every file there arrived through
`ligature.pyz draft`, and the only thing promoted on the live root is Stage 0
evidence, via `promote-evidence`, which the installed `SKILL.md` calls the one
mechanical promotion path.

The single source of truth for the whole set is
`analysis/ligature/stage0-3/artifacts.py`: every artifact body, every prompt
variable, and every `ligature.pyz draft` command line. Regenerating the proofs is
`bash analysis/ligature/stage0-3/run-proofs.sh`.

### What is on disk now

| kind | count | state on the live root |
|---|---|---|
| Stage 0 evidence `evidence/E-0*.json` | 11 | **promoted** (`promote-evidence`, no `--reviewer`, no `review` block) |
| concept specs `rust/swisstable-verus-core/specs/<snake>.json` | 7 | staged `.draft`; not yet human-reviewed/promoted on the live root. The old “not approvable” tool-gap claim is superseded by 1.2.2. |
| interactions `…/specs/_interactions/*.json` | 15 | staged `.draft` |
| boundary contracts `…/specs/_boundaries/*.json` | 14 | staged `.draft` |
| bridges `…/specs/_bridges/*.json` | 6 | staged `.draft` |
| witnesses `…/specs/_witnesses/*.json` | 2 | staged `.draft`; blocked on the concept specs |
| conflict resolution `specs/_conflicts/EC-1.json` | 1 | staged `.draft` |
| exemptions / protocol-debt | 0 | not needed: every boundary-required edge has a boundary contract, and every edge is `pairwise` |

56 artifacts. `analysis/ligature/stage0-3/drafting.txt` records each one's exact
command line and exit code: **56/56 staged cleanly**, every one at
`OK: generated draft passes G1a/G1b immediate checks`, exit 0.

The subset modelled is the plan's P2 list — open addressing, group probing (scalar),
tombstones, erase, rehash, iteration — as seven concepts: the six mechanism concepts
above plus `SwissTable`, the key-value shell callers use. All `verifier: verus`,
clustered `hashing` / `control-bytes` / `probing` / `table` / `api` / `iteration`.
The SIMD half of group probing is deliberately **not** modelled as a concept.
Issue #36 records a scalar-only scope cut for the current P2 implementation;
`E-010` remains deferred for operator review. This does not claim a general
Verus or Kani limitation for future intrinsic-based code.

### Live-root state you are inheriting (all measured this session)

```
$ python3 tools/ligature/ligature.pyz validate-evidence
OK: all evidence records pass G1a/G1b (11 discovered)          exit 0
$ python3 tools/ligature/ligature.pyz validate
OK (nothing to check: no boundary contracts discovered under .) exit 0
$ python3 tools/ligature/ligature.pyz validate-interaction
OK (nothing to check: no interactions discovered under .)       exit 0
$ python3 tools/ligature/ligature.pyz validate-bridge
FAIL: 6 finding(s)  … 'review' is a required property (on 6 .draft) exit 1
$ python3 tools/ligature/ligature.pyz validate-witness
FAIL: 2 finding(s)  … 'review' is a required property (on 2 .draft) exit 1
$ python3 tools/ligature/ligature.pyz validate-conflict-resolution
FAIL: 1 finding(s)  … 'review' is a required property (on 1 .draft) exit 1
$ python3 tools/ligature/ligature.pyz check --json | jq .result
{ "conditions": ["human_decision_required"], "exit_code": 3 }   exit 3
$ python3 tools/ligature/ligature.pyz write-set-check --json | jq .write_set.state
"clean"                                                          exit 0
$ python3 tools/ligature/ligature.pyz doctor                      exit 0
```

`check --json` at exit 3 with nine findings that all read `'review' is a required
property` on a `.draft` subject is the **expected pre-approval state**, not a
defect: nine human checkpoints are outstanding. `analysis/ligature/stage0-3/draft-collection.txt`
shows why only three validators notice them — `validate` and `validate-interaction`
skip staged drafts (chainlink #97, fixed in 1.2.0) while `validate-bridge`,
`validate-witness`, `validate-exemption` and `validate-conflict-resolution` still
collect them. Filed as **epic #1 #110**.

### Order constraints — measured, not assumed

`analysis/ligature/stage0-3/order-constraints.txt` runs each deliberately wrong order
on a fresh scratch copy. Three constraints are enforced, all fail-closed:

1. **evidence before the conflict resolution.** `EC-1` approved with no evidence
   promoted: `[G1b/error] evidence id 'E-007' does not resolve to any real evidence
   record -- dangling reference`, exit 1.
2. **boundaries before boundary-required interactions** (this is R2). All 14
   boundary-required interactions approved with no boundaries promoted:
   `[R2/error] eligibility is boundary-required but no boundary contract for this
   edge and no reviewed exemption covers interaction_id '…'`, exit 1 each. The one
   `inform` edge (`raw_table_find_to_hash_mix_h2`) approved with no boundary at all,
   as it should.
3. **boundaries before bridges.** All 6 bridges with no boundaries promoted:
   `[G2/error] boundary_id '…' does not resolve to any real boundary contract --
   dangling reference`, exit 1 each.

Bridges and interactions are otherwise independent of each other, so steps 3 and 4
below can be swapped. Everything else in the sequence is a convention, not a
constraint.

### The runbook

Every number this section quotes is **derived and machine-checked**, not remembered.
`analysis/ligature/stage0-3/check-runbook.py` sums `callee_guarantees` across the 14
staged boundary artifacts and reads the post-approval tally out of
`approval-proof.txt` STEP 8, then fails (exit 1) if this document disagrees. That check
exists because the count moved twice while this issue was open — 18 when the set was
first drafted, 20 after the ProbeSeq re-cut and the added `ControlBytes.C008` — and the
prose went stale both times. Run it after any re-derivation:

```
$ python3 analysis/ligature/stage0-3/check-runbook.py
…
derived from the staged boundary artifacts:
  boundaries                14
  callee_guarantees total   20  (histogram {1: 8, 2: 6})
  with one / with two       8 / 6
derived from approval-proof.txt:
  validate reports          INFO: 20 non-blocking finding(s)
  check --json findings     28  {'info G2': 6, 'info G2+': 20, 'medium G1a': 2}
OK: every count the README quotes is the derived one, not a remembered one.
```

Run from `swisstable-verus/`. Set your reviewer name once:

```
R=<your-name>
```

**Step 0 — nothing to do.** The 11 evidence records are already promoted.
`promote-evidence` is mechanical and was run here; there is no evidence checkpoint
to take, by the tool's own design (evidence carries no `review` block).

**Step 1 — approve the 14 boundary contracts.** Expected: `approved: <path> (new) by
<your-name> at <date>`, exit 0, one line each.

```
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/raw_table_erase__to__control_bytes_set_dead.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/raw_table_erase__to__control_bytes_set_empty.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__control_bytes_is_empty_or_deleted.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__group_probe_match_empty_or_deleted.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__group_probe_match_full.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__probe_seq_advance.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__probe_seq_offset.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/raw_table_resize__to__control_bytes_clear_dead.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/raw_table_resize__to__probe_seq_offset.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/swiss_table_erase__to__control_bytes_set_dead.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/swiss_table_erase__to__raw_table_erase.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/swiss_table_insert__to__raw_table_insert.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/swiss_table_reserve__to__raw_table_resize.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_boundaries/table_iterator_advance__to__control_bytes_is_empty_or_deleted.json
```

Then `python3 tools/ligature/ligature.pyz validate` — expect **exit 0** with
`INFO: 20 non-blocking finding(s)`, every one `[G2+/info] <boundary>: '<id>':
applies_to unverifiable -- no spec file under specs_search_root declares concept
'<X>'`. 20 is the exact total of `callee_guarantees` entries across the 14
boundaries (8 with one, 6 with two). Those 20 are the concept-spec gap
(#111), not a boundary problem — **but that claim is now measured, not assumed.**
`analysis/ligature/stage0-3/post-111-g2plus.txt` (proof 5) runs this whole
approve order on a scratch copy and then makes the concept specs resolvable, which
is the state #111 asks for. There:

```
validate -> exit 0
    OK: all boundary contracts pass G1a/G1b/G2+ (14 discovered)
```

So the 20 resolve, and G2+ **actually checks** each `callee_guarantees` entry's
`applies_to` against the boundary's callee method rather than skipping it. That
check is the reason the four boundaries it once failed are now re-cut — see
scrutiny item 1.

One thing to read carefully in the transcript: `validate` prints its 20 info lines
and *then* a summary line reading `OK: all boundary contracts pass G1a/G1b/G2+ (14
discovered)`. That summary does not mean G2+ passed. It means no finding was severe
enough to block; G2+ was degraded to `info` because the concept specs were
unresolvable. The two statements are only reconciled by the fix above, where the
same line appears with **no** info lines under it.

**Step 2 — approve the 15 interactions.** Expected: `approved: …`, exit 0 each. All
15 in one block:

```
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/raw_table_erase_to_control_bytes_set_dead.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/raw_table_erase_to_control_bytes_set_empty.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_control_bytes_is_empty_or_deleted.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_group_probe_match_empty_or_deleted.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_group_probe_match_full.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_hash_mix_h2.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_probe_seq_advance.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_probe_seq_offset.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/raw_table_resize_to_control_bytes_clear_dead.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/raw_table_resize_to_probe_seq_offset.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/swiss_table_erase_to_control_bytes_set_dead.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/swiss_table_erase_to_raw_table_erase.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/swiss_table_insert_to_raw_table_insert.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/swiss_table_reserve_to_raw_table_resize.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_interactions/table_iterator_advance_to_control_bytes_is_empty_or_deleted.json
```

Then `python3 tools/ligature/ligature.pyz validate-interaction` — expect
`OK: all interactions pass G1a/G1b (incl. computed eligibility), G15 protocol
coverage, and R2 coverage (15 discovered)`, exit 0.

**Step 3 — approve the 6 bridges.** Expected: `approved: …`, exit 0 each.

```
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_bridges/BR-CONTROLBYTES-CLEARDEAD-001.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_bridges/BR-CONTROLBYTES-SETDEAD-001.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_bridges/BR-GROUPPROBE-FREE-WINDOW-001.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_bridges/BR-GROUPPROBE-WINDOW-001.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_bridges/BR-PROBESEQ-MASK-001.json
python3 tools/ligature/ligature.pyz approve --reviewer $R rust/swisstable-verus-core/specs/_bridges/BR-RAWINSERT-NONFULL-001.json
```

Then `python3 tools/ligature/ligature.pyz validate-bridge` — expect **exit 0** and
`OK: all bridges pass G1a/G1b (incl. conclusion consistency) and G2 boundary
cross-reference (6 discovered)`. G2 here *is* really checked, because each bridge's
boundary is promoted by step 1: it verifies `boundary_id` resolves and
`callee_requirement` is one of that boundary's `callee_guarantees`.

`check --json` and `status` nevertheless report six `[G2/info] … boundary
cross-reference was not checked -- no boundary context was supplied to this
validator run`, one per bridge. **These are not the concept-spec gap** — they are
`check`'s own re-validation of the promoted bridge without boundary context, and
proof 5 shows they are still there after #111 is fixed. They are `info`, so they
do not change any exit code.

**Step 4 — approve the conflict resolution.** Expected: `approved: …`, exit 0.

```
python3 tools/ligature/ligature.pyz approve --reviewer $R specs/_conflicts/EC-1.json
```

Then `python3 tools/ligature/ligature.pyz validate-conflict-resolution` — exit 0.

**Step 5 — do NOT run these.**

- The 7 concept specs. This was a 1.2.1 limitation. Ligature 1.2.2 closes
  the concept-spec promotion gap; the live drafts still need the normal
  human review/approval path before dependent witness specs can validate.
- The 2 witness specs. `approve` reaches G2 and exits 1 with `no concept spec under
  the search root declares concept 'GroupProbe'` / `'ControlBytes'`. Same root
  cause.
- `accept-promotion`, `record-ruling`, `accept-policy` — not *this* stage. They are
  Stage 4.5 and they are the operator's to take; the exact commands and their measured
  output are in "Stage 4 / 4.5 / 7" below.

**After step 4, the expected end state:**

```
$ python3 tools/ligature/ligature.pyz validate                 exit 0  INFO: 20 non-blocking finding(s) (all G2+ applies_to unverifiable)
$ python3 tools/ligature/ligature.pyz validate-interaction     exit 0  OK … R2 coverage (15 discovered)
$ python3 tools/ligature/ligature.pyz validate-bridge          exit 0  OK … G2 boundary cross-reference (6 discovered)
$ python3 tools/ligature/ligature.pyz validate-evidence        exit 0  OK … (11 discovered)
$ python3 tools/ligature/ligature.pyz validate-conflict-resolution  exit 0  OK … G1a/G1b/G11 (1 discovered)
$ python3 tools/ligature/ligature.pyz validate-witness         exit 1  (the 2 staged witness drafts only)
$ python3 tools/ligature/ligature.pyz check --json             exit 3  conditions ["human_decision_required"],
                                                               28 findings: 2 medium G1a, 6 info G2, 20 info G2+
                                                               (the 2 medium G1a are the witness drafts, below)
$ python3 tools/ligature/ligature.pyz status
artifacts (47): validated=47
obligations: 11 declared, 11 with an unmet required dimension
human decisions pending: 2
$ python3 tools/ligature/ligature.pyz write-set-check --json   exit 0  "clean"
```

Approving writes `ci/results/review_log.jsonl` (the audit `accept-promotion` will
later read back) and, from step 0, `ci/results/evidence_promotions.jsonl`. Neither
appears in `allowed_roots`, and the write set still reads `clean`: both are
recognised canonical pipeline locations. Measured, not assumed.

**And once #111 is fixed**, the same runbook produces this instead — measured, not
predicted (`analysis/ligature/stage0-3/post-111-g2plus.txt`):

```
$ … the 36 approve commands above, in the same order …
validate -> exit 0   OK: all boundary contracts pass G1a/G1b/G2+ (14 discovered)
validate-interaction -> exit 0   OK: … R2 coverage (15 discovered)
validate-bridge -> exit 0   OK: … G2 boundary cross-reference (6 discovered)
validate-witness -> exit 1   (the 2 witness drafts, now approvable in principle)
check --json -> exit 3   exit_code 3, conditions ['human_decision_required']
                         0 high/blocker findings; 6 info G2, 2 medium G1a
```

The 20 `G2+` infos become a real G2+ pass, and nothing blocks. The 2 witness drafts
are then approvable, which removes the last two findings and takes `check --json`
to exit 0.

`check --json` will **still** be exit 3 today, because the two witness drafts remain
staged and `validate-witness` collects them (#110). That is the truthful state: a
human decision really is outstanding, and `check` is correctly reporting it. It
cannot go to 0 until #111 is fixed and the witnesses can be approved. Do not delete
or rename the witness drafts to force a green run — they are the reviewable
artifacts, and `approve` consumes them in place.

### What to scrutinise

Everything in this section is a place where the tool accepted something without
checking it. `artifacts.py` mechanically refuses to emit an artifact whose ids
dangle (see its `check_constraint_ids`), but these are the judgement calls a human
still has to make.

1. **`callee_guarantees` is the field this pipeline exists to populate, and G2+ does
   check it — once it can.** Three things to hold in mind:
   - **It is never checked for emptiness**, and an empty list is schema-valid at
     draft time and satisfies G2 for the boundary. It would mean the boundary
     asserts the caller depends on nothing at all, and nothing in the pipeline
     would object. All 14 boundaries declare one or two entries; check each.
   - **Every entry's `applies_to` must include the boundary's callee method.**
     That is a hard `G2+/error`, not a note — proof 5, measured:
     `'ProbeSeq.C001' applies_to ['from_capacity_and_h1'], which does not include
     this boundary's callee method 'offset'`. Four boundaries failed exactly this
     way in the first attempt at this issue and were re-cut; the transcripts of that
     are in `post-111-g2plus.txt`'s predecessor run and the four are now
     `raw_table_find__to__probe_seq_offset` (reliance moved to `ProbeSeq.C002`, an
     invariant that does apply to `offset`), `…__to__group_probe_match_full` and
     `…_match_empty_or_deleted` (`GroupProbe.C001`'s `applies_to` widened to the two
     mask queries), and `raw_table_erase__to__control_bytes_set_empty` (given its
     own `set_empty` postcondition, `ControlBytes.C008`, instead of borrowing
     `set_dead`'s). The runbook's expected output now assumes the corrected form,
     so if you re-derive any of these, re-run `run-proofs.sh` and check proof 5.
   - **Six of the entries are preconditions listed so a bridge can discharge
     them.** That is deliberate and is the only way to satisfy bridge G2 —
     `stage-3-boundary-drafting.md` says a precondition does **not** belong here,
     `stage-3-bridge-drafting.md` says `callee_requirement` **must** be one of these
     entries. Filed as **epic #1 #112**. Read those entries as "the obligation a
     bridge discharges", not as a claim that the callee guarantees it. The
     constraint's `applies_to` must still name the callee method, which is why the
     preconditions here name the method they are established at rather than a
     neighbouring one.

   | boundary_id | caller -> callee | `callee_guarantees` |
   |---|---|---|
   | `raw_table_erase__to__control_bytes_set_dead` | `RawTable.erase -> ControlBytes.set_dead` | `ControlBytes.C004`, `ControlBytes.C003` *(precondition, bridge)* |
   | `raw_table_erase__to__control_bytes_set_empty` | `RawTable.erase -> ControlBytes.set_empty` | `ControlBytes.C008` |
   | `raw_table_find__to__control_bytes_is_empty_or_deleted` | `RawTable.find -> ControlBytes.is_empty_or_deleted` | `ControlBytes.C001` |
   | `raw_table_find__to__group_probe_match_empty_or_deleted` | `RawTable.find -> GroupProbe.match_empty_or_deleted` | `GroupProbe.C003`, `GroupProbe.C001` *(precondition, bridge)* |
   | `raw_table_find__to__group_probe_match_full` | `RawTable.find -> GroupProbe.match_full` | `GroupProbe.C002`, `GroupProbe.C001` *(precondition, bridge)* |
   | `raw_table_find__to__probe_seq_advance` | `RawTable.find -> ProbeSeq.advance` | `ProbeSeq.C004` |
   | `raw_table_find__to__probe_seq_offset` | `RawTable.find -> ProbeSeq.offset` | `ProbeSeq.C002`, `ProbeSeq.C001` *(precondition, bridge)* |
   | `raw_table_resize__to__control_bytes_clear_dead` | `RawTable.resize -> ControlBytes.clear_dead` | `ControlBytes.C006`, `ControlBytes.C005` *(precondition, bridge)* |
   | `raw_table_resize__to__probe_seq_offset` | `RawTable.resize -> ProbeSeq.offset` | `ProbeSeq.C002` |
   | `swiss_table_erase__to__control_bytes_set_dead` | `SwissTable.erase -> ControlBytes.set_dead` | `ControlBytes.C004` |
   | `swiss_table_erase__to__raw_table_erase` | `SwissTable.erase -> RawTable.erase` | `RawTable.C005` |
   | `swiss_table_insert__to__raw_table_insert` | `SwissTable.insert -> RawTable.insert` | `RawTable.C004`, `RawTable.C003` *(precondition, bridge)* |
   | `swiss_table_reserve__to__raw_table_resize` | `SwissTable.reserve -> RawTable.resize` | `RawTable.C001` |
   | `table_iterator_advance__to__control_bytes_is_empty_or_deleted` | `TableIterator.advance -> ControlBytes.is_empty_or_deleted` | `ControlBytes.C001` |

2. **Every `<Concept>.C<nnn>` is invented by this run, and `artifacts.py` now
   checks two things about it mechanically**, both of which refuse to emit the
   artifact: that the id is declared by that concept's own spec with the kind the
   caller relies on, **and** that the constraint's `applies_to` both names a
   declared query or command of that concept and includes the method that relies
   on it (for a boundary's `callee_guarantees`, for an interaction's
   `reliances[].obligation_id`, and for a bridge's `callee_requirement` against its
   boundary's callee). The second check exists because the first one was not
   enough — four boundaries in the first attempt at this issue passed the id check
   and would still have failed G2+ (proof 5). Neither check can tell you the
   constraint *text* is the right obligation; that is a reading. Read
   `rust/swisstable-verus-core/specs/<concept>.json.draft` alongside the boundary
   table above.

3. **The proxy-obligation risk is concentrated in `ControlBytes.C001`.** It is
   cited by three separate boundaries (`RawTable.find`,
   `TableIterator.advance`, `SwissTable.erase`) as their whole reliance. C001 is a
   four-way disjunction ("empty, or deleted, or sentinel, or a full byte"), which is
   a statement about the *encoding*, not about the behaviour the three callers
   actually depend on. The behaviour each of them needs is the next constraint down —
   `ProbeSeq`-side masking for `find`, the stop condition for the cursor. If you
   want the reliance statements to be sharp, C001 is the one to re-cut before
   approving the three boundaries that lean on it alone. This is the "proxy
   obligation" flag from the issue's own brief; it is not a tool defect.

4. **`evidence_links` on an interaction are never resolved.** Measured: an
   interaction declaring `evidence_links: ["E-999", "E-not-a-record"]` approves at
   exit 0 and passes `validate-interaction` at exit 0. All 15 shipped interactions
   cite only ids that exist (`artifacts.py` checks this), but a green
   `validate-interaction` does not mean the links resolve. `doctor` declares the
   underlying G4/G5 gap itself, so this is a known unimplemented gate, not a defect.

5. **The two witness specs carry placeholder hashes.** `determinism.value_hash` and
   `output.render_hash` are `sha256:0000…0000`. There is no Rust crate and no
   `witness_backend`, so no canonical result exists to hash and no rendering exists
   to hash. G19 recomputes `value_hash` from a fresh regeneration and will reject
   this — correctly. **Do not approve a witness with those hashes in place**; it
   cannot currently be approved anyway (#111), and when it becomes approvable the
   hashes must come from `render-witness` and a real G19 pass first. The
   `fixture`, `renderer`, `expectation` and `concept`/`query` fields are the parts
   worth reviewing now.

6. **Two evidence records remain `lifecycle: deferred` for operator review.**
   `E-010` covers SIMD as a separate implementation. Issue #36 records the
   current P2 source as scalar-only scope; no Kani-owned SIMD implementation or
   cluster was added, and the descriptor remains unchanged. The shared
   `IdentityHash-v1` oracle input is implemented by **#32** and checked by
   **#37**, which also records the C.10 iteration/pointer exclusion. `E-011`'s
   evidence record remains `lifecycle: deferred` pending operator review, so it
   stays out of the accepted set. Neither E-010 nor E-011 defers a constraint
   or an interaction.

7. **`EC-1` resolves a real conflict in favour of the intent over the
   implementation.** `E-007` (iteration is ascending control-array index) and
   `E-008` (the per-table seed is mixed into H1 *to randomise* that order) are both
   true and disagree about what a caller may rely on. `EC-1` selects `E-008`. The
   consequence is binding: no concept constraint may require an iteration order, and
   no oracle case may compare one. `TableIterator.C004` and `SwissTable.C004` are
   written from `E-008`. Chainlink **#37** records the oracle-side exclusion.
   Check this resolution before approving — `EC-1` is the one artifact here whose effect
   outlives Stage 3.

8. **Protocol-debt and exemption records are absent by choice.** Every interaction
   is `protocol_class: pairwise` (no handshake, no multi-step ordering invariant in
   the subset), and every boundary-required edge has a boundary contract, so R2 never
   needs `approve-pair` or `approve-exemption-pair`. If you want a non-pairwise edge
   recorded, it needs a protocol-debt record bootstrapped with `approve-pair`, and
   the atomicity of that pair is the tool's, not something to split.

### Former upstream blockers and live artifact follow-ups

This table records the 1.2.1 findings and their current disposition. A fixed
tool defect does not automatically repair drafts already on disk or replace
the human review required to promote them.

| Finding | 1.2.2 disposition / remaining work |
|---|---|
| Concept-spec promotion (#111) | Tool gap fixed upstream. Seven live drafts remain unreviewed; promote only through the current human-reviewed path. |
| Witness specs, G18/G19/G20, feature ledger/contact sheet | Still depend on concept/witness artifacts being reviewed and promoted. This is live project work, not the former promotion-command defect. |
| Staged-draft collection (#110) | Fixed upstream. Re-run the relevant validator on the live root before treating any old 1.2.1 transcript as current. |
| Stage 3 template contradiction (#112) | Fixed upstream. Existing drafts made from the old templates may need revalidation or re-cutting. |
| Bridge-template/G9 grammar (#113) | Fixed upstream. Existing six bridges were authored under the old template; re-cut/revalidate them. The missing Verus backend declaration remains a separate human descriptor decision before G9 can dispatch. |
| Policy marker (#114) | The accept-policy dead end is fixed by 1.2.2 --version. Policy content, reviewer, and version choice remain human-owned; the current placeholder makes doctor exit 1 and blocks verification/closure. |

Do not use the old hand-written workaround of placing concept specs into a
protected tree. Use the 1.2.2 command path and keep human review checkpoints.

Five findings were appended to `findings/limitations.jsonl` by
`analysis/ligature/write-findings-28.py` (idempotent; the 23 pre-existing lines are
byte-identical): `swisstable-ligature-005` (four validators collect staged drafts,
exit 1 / `check` 3 — escalated as #110), `swisstable-ligature-006` (a concept spec is
draftable but not promotable, and what that costs — escalated as #111, `blocker`),
`swisstable-ligature-007` (the two Stage 3 reliance templates are jointly
unsatisfiable — escalated as #112), `swisstable-ligature-008` (`evidence_links` is
never resolved; `doctor` declares the G4/G5 gap itself) and `swisstable-ligature-009`
(`draft` stages an invalid body and still exits 1). The second pass below added three
more, by `analysis/ligature/write-findings-28b.py` (idempotent; the 60 pre-existing
lines are byte-identical): `swisstable-ligature-012` (G9's second, independent
precondition — the missing `verifier_backends.verus`, `blocker`),
`swisstable-ligature-013` (the exact premise grammar G9 admits, with the generated
harness showing why), and `swisstable-ligature-014` (`check-bridges` writes
`ci/harness/` and `write-set-check` stays clean about it; `--workspace` is a global
flag).

### Second measurement pass, on ligature 1.2.1 (chainlink #28, re-verification)

The root was upgraded from 1.2.0 to **1.2.1** (sha256 `30e504d388d5fb2acf1185fe3bfc17c96ec82483771d8d59a37fb3749009aacd`,
`cd tools/ligature && sha256sum -c SHA256SUMS` -> `ligature.pyz: OK`, `ligature version`
-> `ligature 1.2.1`) while this issue was open, so the three claims above were
re-measured against it on an `rsync` scratch copy
(`/tmp/opencode/s2/v121`, reviewer name `scratch-grammar-probe`, never the live
root). All three still hold, byte-for-byte in the messages: the 14 boundaries, 15
interactions and 6 bridges all approve at exit 0, and `check-bridges` returns the
same 6 `G9/error` lines quoted at README:914-919. **#110, #112 and #113 are not
fixed in 1.2.1.** Transcript: `analysis/ligature/stage0-3/recheck-1.2.1.txt`.

Two things that measurement adds, neither of which is in #113:

**1. Re-cutting the premises is necessary but not sufficient — G9 fails a second
time, for a different reason.** `BR-CONTROLBYTES-SETDEAD-001` re-cut to the only
grammar G9 accepts (`bindings` `{self, slot}`; `premises` `["self.is_full_ctrl(slot)",
"self.is_not_sentinel_ctrl(slot)"]`) clears the grammar error and advances to:

```
wrote <ws>/ci/harness/BR-CONTROLBYTES-SETDEAD-001.verus.rs
  - [G9/error] BR-CONTROLBYTES-SETDEAD-001: harness generated for verus at
    ci/harness/BR-CONTROLBYTES-SETDEAD-001.verus.rs, but the project descriptor
    configures no verifier_backends.verus command -- nothing was checked, so no
    result is recorded (the ceiling here is harness-tested, never bridge-checked)
exit 1
```

`project-descriptor.json` here declares `verifier_policy.default: "verus"` and no
`verifier_backends` at all. So **the instruction at README:930-932 — re-cut the 6
bridges, then require `gate-g9` exit 0 — cannot succeed as written**: the grammar
error and the missing backend are two independent G9 preconditions, and the
descriptor is a user-owned protected file, so no agent working this issue can add
the backend. An operator has to add `verifier_backends.verus.command` *and* the
bridges have to be re-cut. Add that row to the "Blocked on upstream" table above.

**2. The exact language G9 accepts, so a re-cut passes the first time.** Probed on
1.2.1 by rewriting `bridge_logic.premises` in place and re-running `check-bridges`.
Accepted: a bare declared binding (`self`, `slot`); a dotted chain
(`self.ctrl.len()`); a chain ending in calls (`self.foo()`, `self.a.b.c()`); call
arguments that are themselves declared bindings (`self.foo(slot)`); and the empty
string. Rejected, each with its own message: any operator (`=`, `<`, `>`, `&&`,
`||`, `+`, `-`), any literal (`1`, `0xFF`), any quantifier (`forall|i: u64|`),
indexing (`self.ctrl[0]`), a path (`Self::f()`), a free-function call rooted
outside the bindings (`foo(self)` — *"a harness cannot pass a value it was never
given"*; the declared set is `bridge_logic.bindings` keys **plus** every
`required_local_facts[].fact_id`), and a non-snake_case binding key. That last
error names `GROUP_WIDTH`, the only binding name the 6 bridges get wrong.

Note that `check-bridges` is **not read-only**: it writes `ci/harness/<id>.<verifier>.rs`
into the workspace. `write-set-check` still reports `write set: clean` with that
directory present, because `ci/harness/**` is in neither `allowed_roots` nor
`protected_roots` — the WORKER-CONTRACT §0.0 trap again, one directory over. And
`--workspace` is a **global** flag: `check-bridges --workspace /abs` exits 2 with a
usage error, `--workspace /abs check-bridges` is the form that works.

The generated harness shows why the narrow grammar is load-bearing rather than
pedantic — it pastes each premise verbatim into a Verus `requires` clause:

```rust
verus! {
    proof fn bridge_br_controlbytes_setdead_001(self: RawTable, slot: usize)
        requires
        self.is_full_ctrl(slot),
        self.is_not_sentinel_ctrl(slot),
        ensures
        ControlBytes::C003(self, slot),
    { }
}
```

So a premise has to be a boolean-valued term for that harness to compile at all. A
premise written as the template's "premise expression" (`slot < self.capacity()`) is
a perfectly good boolean and is rejected; a premise written as a term
(`self.ctrl(slot)`) is accepted and is not a boolean. The only way to satisfy G9 is
to name a boolean-returning *predicate* over the bindings — which means the real
predicate has to exist as a method on the ported type, so the honest form of a
bridge premise here is `self.some_predicate(arg)`, not an expression. That is the
sharpest statement of #113's consequence and it is what the re-cut should aim at.

## Stage 4 / 4.5 / 7: validation, gates, promotion, and the work-package manifest (chainlink #29)

### Stage 4 and Stage 4.5 on the live root are PENDING the operator batch, not failed

Nothing was approved on the live root. All 45 Stage 0-3 drafts are still `.json.draft`,
`ci/results/` holds only the Stage 0 `evidence_promotions.jsonl`, and there is **no**
`ci/results/review_log.jsonl`, **no** `ci/results/human_rulings.jsonl` and **no**
`specs/_promotions/`. The entire Stage 4 + Stage 4.5 sequence was instead run end to end on
an rsync scratch copy of this root -- `analysis/ligature/stage4-7/stage45-scratch-proof.sh`,
transcript `analysis/ligature/stage4-7/stage45-scratch-proof.txt` -- with the reviewer name
`scratch-approval-proof`, deliberately not a plausible human name, so a ruling logged there
can never be mistaken for the operator's. Everything quoted below is copied from that
transcript, not predicted.

Live root as it stands, full transcript in `analysis/ligature/stage4-7/live-root-stage4.txt`:

```
validate                       exit 0   OK (nothing to check: no boundary contracts discovered under .)
validate-interaction           exit 0   OK (nothing to check: no interactions discovered under .)
validate-bridge                exit 1   6 x [G1a] 'review' is a required property, on the 6 .draft   (#110)
validate-evidence              exit 0   OK: all evidence records pass G1a/G1b (11 discovered)
validate-conflict-resolution   exit 1   1 x [G1a] 'review' is a required property, on EC-1.json.draft (#110)
validate-witness               exit 1   2 x [G1a] 'review' is a required property, on the 2 .draft    (#110)
validate-exemption             exit 0   OK (nothing to check: no exemptions discovered under .)
validate-protocol-debt         exit 0   OK (nothing to check: no protocol-debt records discovered under .)
check                          exit 3   result: exit_code=3 conditions=['human_decision_required']
status                         exit 0   human decisions pending: 9
write-set-check                exit 0   write set: clean
doctor                         exit 0
gate-g9                        exit 1   FAIL: no promoted bridge discovered -- G9 has nothing to check
check-bridges                  exit 0   OK: 0 artifact(s) written; every promoted bridge compiled and was dispatched
gate-r1-g16                    exit 1   error: no C_static reports at ci/results/c_static/
gate-g14                       exit 1   error: no closure directory at specs/_closure
gate-g18 / g19 / g20           exit 0   OK (nothing to check: no witness specs discovered under .)
validate-closure               exit 0   OK (nothing to check: no closure artifacts discovered under .)
select-pilot-cluster           exit 1   Evaluated 0 candidate cluster(s)
```

The three validator exit-1s and `check`'s exit 3 are the **nine outstanding human
approvals**, not defects -- the same state chainlink #28 left the tree in. `gate-g9`'s
exit 1 is the "a gate that passes over zero bridges would claim what it never ran"
refusal, and it is exactly right here.

**The 1.1.1 warning carried on issue #29 about `check-bridges` / `gate-g9` crashing on a
relative `--workspace` is stale.** That was #96, fixed in 1.2.0. Measured on the scratch
copy with all 6 bridges promoted, both commands produce the correct 6 G9 findings with a
relative `--workspace .` *and* with an absolute one, with no `ValueError`. No workaround
is needed.

### Stage 4.5 works -- but two human-authority steps sit in front of it

Measured, in this order, on the scratch copy after all 36 approvable artifacts approved at
exit 0:

1. **`accept-promotion` refuses before it ever reaches the ruling gate**, on the policy
   document as it ships:

   > Historical reproduction against 1.2.1. Version 1.2.2 adds
   > `accept-policy --reviewer HUMAN --version NAME@MAJOR.MINOR`, which
   > stamps the marker only. The current migration still reports the
   > user-owned placeholder; policy substance and the version choice remain
   > human-owned.

   ```
   $ python3 tools/ligature/ligature.pyz accept-promotion swisstable-verus-core --reviewer scratch-approval-proof --artifact docs/reliance-policy.md --artifact evidence/E-001.json ... (48)
   error: 'docs/reliance-policy.md' must have exactly one 'Policy version: <name>@<major>.<minor>' marker line (docs/reliance-policy.template.md's own convention) -- found 0
   EXIT=1
   ```

   Under 1.2.1, `accept-policy` also failed because it required the marker it was meant to
   establish. That tool dead end was filed as **epic #1 #114** / upstream #113 and is fixed
   in 1.2.2. This remains a human step: complete and review `Schema version`, `Owner:`,
   oracle/reliance content and other project-specific text, choose a real policy version, then
   use the new command. Do not let an agent decide policy content or impersonate the reviewer.

2. **With the policy filled, the human-ruling gate is real and fail-closed.** Zero rulings:

   ```
   error: refusing to mint a promotion receipt: no complete human ruling covers this accepted set
     (Stage 4.5 is gated on an explicit `record-ruling` verdict for every artifact):
     - no human ruling log at ci/results/human_rulings.jsonl -- none of the 48 artifact(s) about to
       be promoted has been ruled on: ...; record the ruling first with
       `record-ruling --reviewer <name> --verdict ratified|rejected --artifact <path> [--artifact <path> ...]`
   EXIT=1
   ```

### Steps 6-9 -- the promotion commands, verbatim from the measured transcript

The accepted set was **48 artifacts** in this 1.2.1 scratch transcript:
`docs/reliance-policy.md`, 11 promoted evidence records, `specs/_conflicts/EC-1.json`,
14 boundary contracts, 15 interactions and 6 bridges. That set predates Ligature 1.2.2;
the old statement that concept specs were not approvable (#111) is superseded. Recompute and
review the accepted set before any future promotion. The historical commands below are
reproduced from the old transcript, not a current execution recipe.

**Step 6 -- accept the policy.** A human completes/reviews the content and chooses the
version; 1.2.2 stamps only that marker and records the human checkpoint.

Illustrative syntax only; do not run with placeholder identities or on behalf
of the human reviewer. The reviewer and version must be real, human-selected values.

```
python3 tools/ligature/ligature.pyz accept-policy --reviewer <human-identity> --version <policy-name>@<major>.<minor>
```

Historical 1.2.1 scratch output (the earlier command had no --version option):
```
accepted policy: docs/reliance-policy.md
reviewer: scratch-approval-proof
policy version: swisstable-verus-reliance-policy@0.0
previous hash: sha256:36f20f198ab1de91a2dabed8242ce1a2c1a5edc4f841803f62b6e5bd24e2eea9
accepted hash: sha256:5bf42eba64872c8dd99a8a8f62fcabd850752eaaa73822e784a74a2168d1f5c1
EXIT=0
```

**Step 7 -- record ONE ratified human ruling over all 48 artifacts.** One command settles the
whole set; a ruling is hash-pinned to the exact content it covered, so re-run it if any
artifact changes afterwards.

```
python3 tools/ligature/ligature.pyz record-ruling --reviewer $R --verdict ratified \
  --artifact docs/reliance-policy.md \
  --artifact evidence/E-001.json \
  --artifact evidence/E-002.json \
  --artifact evidence/E-003.json \
  --artifact evidence/E-004.json \
  --artifact evidence/E-005.json \
  --artifact evidence/E-006.json \
  --artifact evidence/E-007.json \
  --artifact evidence/E-008.json \
  --artifact evidence/E-009.json \
  --artifact evidence/E-010.json \
  --artifact evidence/E-011.json \
  --artifact specs/_conflicts/EC-1.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_erase__to__control_bytes_set_dead.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_erase__to__control_bytes_set_empty.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__control_bytes_is_empty_or_deleted.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__group_probe_match_empty_or_deleted.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__group_probe_match_full.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__probe_seq_advance.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__probe_seq_offset.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_resize__to__control_bytes_clear_dead.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_resize__to__probe_seq_offset.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/swiss_table_erase__to__control_bytes_set_dead.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/swiss_table_erase__to__raw_table_erase.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/swiss_table_insert__to__raw_table_insert.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/swiss_table_reserve__to__raw_table_resize.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/table_iterator_advance__to__control_bytes_is_empty_or_deleted.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_erase_to_control_bytes_set_dead.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_erase_to_control_bytes_set_empty.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_control_bytes_is_empty_or_deleted.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_group_probe_match_empty_or_deleted.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_group_probe_match_full.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_hash_mix_h2.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_probe_seq_advance.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_probe_seq_offset.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_resize_to_control_bytes_clear_dead.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_resize_to_probe_seq_offset.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/swiss_table_erase_to_control_bytes_set_dead.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/swiss_table_erase_to_raw_table_erase.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/swiss_table_insert_to_raw_table_insert.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/swiss_table_reserve_to_raw_table_resize.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/table_iterator_advance_to_control_bytes_is_empty_or_deleted.json \
  --artifact rust/swisstable-verus-core/specs/_bridges/BR-CONTROLBYTES-CLEARDEAD-001.json \
  --artifact rust/swisstable-verus-core/specs/_bridges/BR-CONTROLBYTES-SETDEAD-001.json \
  --artifact rust/swisstable-verus-core/specs/_bridges/BR-GROUPPROBE-FREE-WINDOW-001.json \
  --artifact rust/swisstable-verus-core/specs/_bridges/BR-GROUPPROBE-WINDOW-001.json \
  --artifact rust/swisstable-verus-core/specs/_bridges/BR-PROBESEQ-MASK-001.json \
  --artifact rust/swisstable-verus-core/specs/_bridges/BR-RAWINSERT-NONFULL-001.json
```
Expected:
```
recorded ruling: ratified over 48 artifact(s)
reviewer: scratch-approval-proof at 2026-10-02
log: ci/results/human_rulings.jsonl
EXIT=0
```

**Step 8 -- accept the promotion.**

```
python3 tools/ligature/ligature.pyz accept-promotion swisstable-verus-core --reviewer $R \
  --artifact docs/reliance-policy.md \
  --artifact evidence/E-001.json \
  --artifact evidence/E-002.json \
  --artifact evidence/E-003.json \
  --artifact evidence/E-004.json \
  --artifact evidence/E-005.json \
  --artifact evidence/E-006.json \
  --artifact evidence/E-007.json \
  --artifact evidence/E-008.json \
  --artifact evidence/E-009.json \
  --artifact evidence/E-010.json \
  --artifact evidence/E-011.json \
  --artifact specs/_conflicts/EC-1.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_erase__to__control_bytes_set_dead.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_erase__to__control_bytes_set_empty.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__control_bytes_is_empty_or_deleted.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__group_probe_match_empty_or_deleted.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__group_probe_match_full.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__probe_seq_advance.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_find__to__probe_seq_offset.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_resize__to__control_bytes_clear_dead.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/raw_table_resize__to__probe_seq_offset.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/swiss_table_erase__to__control_bytes_set_dead.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/swiss_table_erase__to__raw_table_erase.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/swiss_table_insert__to__raw_table_insert.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/swiss_table_reserve__to__raw_table_resize.json \
  --artifact rust/swisstable-verus-core/specs/_boundaries/table_iterator_advance__to__control_bytes_is_empty_or_deleted.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_erase_to_control_bytes_set_dead.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_erase_to_control_bytes_set_empty.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_control_bytes_is_empty_or_deleted.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_group_probe_match_empty_or_deleted.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_group_probe_match_full.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_hash_mix_h2.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_probe_seq_advance.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_find_to_probe_seq_offset.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_resize_to_control_bytes_clear_dead.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/raw_table_resize_to_probe_seq_offset.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/swiss_table_erase_to_control_bytes_set_dead.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/swiss_table_erase_to_raw_table_erase.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/swiss_table_insert_to_raw_table_insert.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/swiss_table_reserve_to_raw_table_resize.json \
  --artifact rust/swisstable-verus-core/specs/_interactions/table_iterator_advance_to_control_bytes_is_empty_or_deleted.json \
  --artifact rust/swisstable-verus-core/specs/_bridges/BR-CONTROLBYTES-CLEARDEAD-001.json \
  --artifact rust/swisstable-verus-core/specs/_bridges/BR-CONTROLBYTES-SETDEAD-001.json \
  --artifact rust/swisstable-verus-core/specs/_bridges/BR-GROUPPROBE-FREE-WINDOW-001.json \
  --artifact rust/swisstable-verus-core/specs/_bridges/BR-GROUPPROBE-WINDOW-001.json \
  --artifact rust/swisstable-verus-core/specs/_bridges/BR-PROBESEQ-MASK-001.json \
  --artifact rust/swisstable-verus-core/specs/_bridges/BR-RAWINSERT-NONFULL-001.json
```
Expected:
```
accepted: specs/_promotions/swisstable-verus-core.json
EXIT=0
```

**Step 9 -- validate the receipt ligature just wrote.**

```
python3 tools/ligature/ligature.pyz validate-promotion specs/_promotions/swisstable-verus-core.json
```
Expected:
```
OK: promotion receipt passes G1a and §7.1 checks
EXIT=0
```

The receipt that produces (fields; `artifact_manifest` elided -- 48 entries):

```
schema: "promotion-receipt/1.0"
promotion_id: "PROM-SWISSTABLE-VERUS-CORE-001"
cluster: "swisstable-verus-core"
reviewer: "scratch-approval-proof"
policy_version: "swisstable-verus-reliance-policy@0.0"
schema_versions: {"evidence": "1.0", "conflict_resolution": "1.0", "boundary": "1.0", "interaction": "1.0"}
accepted_at: "2026-10-02"
artifact_manifest: [ 48 entries ]
   first: {"path": "docs/reliance-policy.md", "hash": "sha256:5bf42eba64872c8dd99a8a8f62fcabd850752eaaa73822e784a74a2168d1f5c1"}
```

**`PROM-SWISSTABLE-VERUS-CORE-001` is derived, not chosen**: `accept-promotion` computes
`promotion_id` from `cluster` alone. That is why it is safe to record in the Stage 7 manifest
before the real receipt exists. `policy_version` above is the *scratch* placeholder version
and will be the operator's own once step 6 is taken for real.

### All 36 approvals succeed; G9 then fails on all 6 bridges

The 36 `approve` commands in steps 1-4 above all exit 0, and the post-approval validators
agree with this runbook's earlier predictions exactly:

```
validate               exit 0   OK: all boundary contracts pass G1a/G1b/G2+ (14 discovered)
                                 + INFO: 20 non-blocking finding(s), all [G2+] applies_to unverifiable (#111)
validate-interaction   exit 0   OK: all interactions pass G1a/G1b (incl. computed eligibility),
                                 G15 protocol coverage, and R2 coverage (15 discovered)
validate-bridge        exit 0   OK: all bridges pass G1a/G1b (incl. conclusion consistency)
                                 and G2 boundary cross-reference (6 discovered)
check                  exit 3   conditions ['human_decision_required'], 28 findings:
                                 2 medium G1a (the 2 witness drafts), 6 info G2, 20 info G2+
status                 exit 0   artifacts (49): promoted=47, validated=2
                                 obligations: 11 declared, 11 with an unmet required dimension
                                 human decisions pending: 2
write-set-check        exit 0   write set: clean
```

**`gate-g9` and `check-bridges` then fail, on all 6 bridges, at exit 1:**

```
  - [G9/error] BR-CONTROLBYTES-CLEARDEAD-001: bridge_logic does not compile for verus: unexpected character '=' at offset 27 in 'self.ctrl(self.capacity()) == SENTINEL' -- the compilable fragment is predicate application only: no operators, literals, quantifiers or negation
  - [G9/error] BR-CONTROLBYTES-SETDEAD-001: ... unexpected character '<' at offset 5 in 'slot < self.capacity()' ...
  - [G9/error] BR-GROUPPROBE-FREE-WINDOW-001: ... binding name 'GROUP_WIDTH' is not snake_case -- it becomes a harness parameter name
  - [G9/error] BR-GROUPPROBE-WINDOW-001: ... binding name 'GROUP_WIDTH' is not snake_case ...
  - [G9/error] BR-PROBESEQ-MASK-001: ... unexpected character '+' at offset 14 in 'capacity_mask + 1 == (1usize << capacity_bits)' ...
  - [G9/error] BR-RAWINSERT-NONFULL-001: ... unexpected character '>' at offset 16 in 'self.capacity() >= GROUP_WIDTH' ...
```

This is **not** a pilot authoring slip. The installed
`.ligature/prompts/stage-3-bridge-drafting.md` says of `premises`, at line 40,
`"premises": ["<premise expression>"]`, and at lines 112-114 calls a premise "at least one
premise expression"; it documents snake_case only for the *different* field
`required_local_facts[].fact_id` and says nothing about `bindings`. Nothing checks either
G9 rule before approval: all 6 staged at `OK: generated draft passes G1a/G1b immediate
checks`, passed `validate-bridge` at exit 0, and were each written `approved: <path> (new)
by scratch-approval-proof at 2026-10-02` at exit 0. Filed as **epic #1 #113**; logged as
`swisstable-ligature-010`. **The 6 bridges must be re-cut -- predicate application only,
snake_case bindings -- before they are promoted for real.** Re-run
`analysis/ligature/stage4-7/stage45-scratch-proof.sh` afterwards and require `gate-g9` exit 0.

### Stage 7: `ci/manifest/WP-SWISSTABLE-VERUS.json`

**Historical: hand-authored under 1.2.1.** Ligature 1.2.2 now supplies
`generate-work-package`; the previous statement that the generator did not
exist is obsolete. The existing manifest was produced by hand before that
verb shipped and remains subject to its recorded validation below. For a
new manifest or an explicitly authorized regeneration, supply the structured
Stage 7 plan and matching issue grant; do not use free-form JSON or rerun the
generator over the live manifest without reviewing its plan and target.

```
$ python3 tools/ligature/ligature.pyz validate-work-package ci/manifest/WP-SWISSTABLE-VERUS.json ; echo $?
INFO: 2 non-blocking finding(s)
  - [10.1/info] ...: provenance.promotion_id 'PROM-SWISSTABLE-VERUS-CORE-001' cannot be
    resolved against a real promotion receipt yet -- chainlink #15 (detached promotion receipt)
    is not implemented
  - [10.1/info] ...: "every owned function's source path is covered by allowed_write_set" is not
    checked -- functions[] are Rust module paths with no schema-computable mapping to a file path
    without searching real crate source, which this workspace doesn't have
OK: work package manifest passes G1a and §10.1 checks
0
```

Both remaining infos are pre-existing "not implemented / not checked" notices about the
schema, not findings about this pilot's content, and they are the same two P1 got.

Every value in it is **derived**, not remembered.
`analysis/ligature/stage4-7/make-work-package-manifest.py` stands in for the missing
generator: it reads the 7 concept specs, the descriptor, the installed scripts and the rustc
host triple, and re-running it reproduces the file byte-for-byte. It refuses to write rather
than guess -- it checks that every constraint's `applies_to` names a real declared method,
that every bridge's `callee_requirement` equals its own
`bridge_logic.conclusion.obligation_id` and is a precondition-kind obligation, and that no
precondition obligation is also in `provided_guarantees`.

Shape, and the three P1 mistakes it avoids:

| field | value | why |
|---|---|---|
| `depends_on` | `[]` | This is the only work package in the workspace. P1's first manifest named `WP-DATE-CREUSOT-CORE`, which resolves to nothing. |
| `required_guarantees` | `[]` | A single-WP crate has no external callee. P1 listed `Weekday.C2/C3` in both `provided_guarantees` and `required_guarantees`; CG6 correctly called that a work package assuming its own output ("mutual satisfaction is not soundness"). |
| `write_policy` | **verbatim** copy of the descriptor's `write_set` (17 allowed / 10 protected) | This pilot's descriptor already carries crate-scoped protected globs (`rust/*/Cargo.toml`, `rust/*/build.rs`), so P1's `date-ligature-034` overlap cannot arise and no narrowing is needed. Both lists are checked equal to the descriptor by `check-runbook-29.py`. |
| `gate_integrity` | `sha256:0b844c7e...946bd` / `sha256:09dc6a92...39854` | The **real** sha256 of `scripts/witness_renderer.py` and `scripts/xml_escape.py`, recomputed by the generator from the installed files. G13 verifies both, requires each to have `protected_write_set` coverage and forbids `allowed_write_set` coverage. |
| `report.emit` | `ci/results/WP-SWISSTABLE-VERUS.json` | P1 pointed `emit` at `ci/results/feature_ledger.json`, where `report feature-ledger` and `record-assurance` then collided on one path with incompatible schemas. One path, one writer. |
| `obligations` | 36 = 30 `provided_guarantees` + 6 `required_preconditions_to_establish` | The 6 precondition obligations are established at the call site and discharged by the bridges (the only shape satisfying bridge G2, see #112), so they are never also "provided". One entry per **bridge** -- `GroupProbe.C001` has two bridges, so 6 bridges and 5 distinct bridged obligations. |
| `gates` | 9 (P1's 7 plus `g2`/`g9`) | This pilot has 6 bridges; P1 had none. |

Two schema facts were **measured by probing** `validate-work-package`, not guessed, and both
are now comments in the generator: `required_claims` has exactly two permitted values,
`callee-precondition-established` and `postcondition-holds` (there is no separate invariant
claim, so an `invariant` obligation is certified as `postcondition-holds`); and
`required_preconditions_to_establish` entries take exactly `bridge_id`,
`callsite_requirement` and `required_assurance`, with `callsite_requirement` having exactly
one permitted value, `all-discovered-resolved`.

Two things the generator found that are worth a human's eye:

- **`HashMix.C001` is a precondition obligation with no bridge.** It is the precondition on
  the one `inform` edge (`RawTable.find -> HashMix.h2`), which has no boundary contract and
  so nothing for a bridge to discharge. That is consistent, not an omission, but it means
  `HashMix.C001` is established by nothing the pipeline tracks.
- **`HashMix.h2` is `witness_required: true` and has no witness spec.** There are 3 such
  queries (`ControlBytes.count_empty`, `GroupProbe.match_full`, `HashMix.h2`) and only 2
  witness drafts. This is currently invisible because #111 keeps `accept-promotion` from
  reaching that check -- once #111 is fixed, `accept-promotion` will refuse outright until
  the third witness exists. Add it to the batch rather than discovering it then.

`provenance.artifact_set_hash` is the sha256 of the **scratch** proof's receipt, because the
schema requires the field and pattern-checks it against `^sha256:[0-9a-f]{64}$`, leaving no
honest way to write "pending". It is a real hash of a real file but it is not the live-root
artifact set; that is stated in the manifest's own `coupling_notes`, and
`provenance.promotion_id` + `provenance.artifact_set_hash` are the two fields to re-read once
the real receipt exists.

`ci/manifest/**` is in `write_set.protected_roots`, so this file is a protected-root write
done under explicit operator direction, exactly as P1's was. `write-set-check` reports the
root `clean` with 0 violations either way -- the known #90 false negative -- so it is not
evidence that the write was sanctioned.

### Keeping this section honest

`analysis/ligature/stage4-7/check-runbook-29.py` re-derives every number and hash quoted
above from the real files and exits 1 if this section disagrees -- the same discipline as
`analysis/ligature/stage0-3/check-runbook.py`, added for the same reason: the counts in this
README moved while the work was being done.

```
$ python3 analysis/ligature/stage4-7/check-runbook-29.py ; echo $?
derived from the staged artifacts:
  boundaries              14
  interactions            15
  bridges                 6
  witnesses               2
  concept specs           7
  evidence (promoted)     11
  conflict resolutions    1
  accepted set size       48
      = docs/reliance-policy.md + 11 evidence + 1 conflict + 14 boundaries + 15 interactions + 6 bridges

OK   accepted set is 48 artifacts (derived 48)
OK   Stage 4.5 is PROVEN in the scratch proof: accept-promotion exit 0 + validate-promotion exit 0
OK   promotion_id is PROM-SWISSTABLE-VERUS-CORE-001 (proof: PROM-SWISSTABLE-VERUS-CORE-001)
OK   the scratch receipt's own sha256 is in the proof transcript
OK   the proof records 24 G9 findings (all 6 bridges fail G9)
OK   the proof transcript records a `status` artifact tally
OK   README's status tally is the transcript's own: 'artifacts (49): promoted=47, validated=2'
OK   promoted=47 = 36 approvable + 11 promoted evidence
OK   total 49 = promoted 47 + validated 2
OK   manifest is WP-SWISSTABLE-VERUS
OK   depends_on is empty (no other work package exists)
OK   required_guarantees is empty (single-WP crate; avoids P1's CG6 cycle)
OK   no other work package manifest exists to depend on ([])
OK   write_policy.allowed_write_set is a verbatim copy of the descriptor's allowed_roots
OK   write_policy.protected_write_set is a verbatim copy of the descriptor's protected_roots
OK   gate_integrity[scripts/witness_renderer.py] carries the REAL installed sha256 (sha256:0b844c7ec904604754e13ba448c5f146cbe4296a7fd617cdfe0085636eb946bd)
OK   scripts/witness_renderer.py is not in allowed_write_set (G13)
OK   gate_integrity[scripts/xml_escape.py] carries the REAL installed sha256 (sha256:09dc6a9258a9bdab7648d3d8d0588bbb4bf2a096457c950e094964aa8d139854)
OK   scripts/xml_escape.py is not in allowed_write_set (G13)
OK   36 obligations = 30 provided + 6 bridge-discharged
OK   no obligation is listed twice in provided_guarantees
OK   no precondition-kind obligation is in provided_guarantees ([])
OK   the only precondition with no bridge is HashMix.C001 (derived ['HashMix.C001'])
OK   one required_preconditions_to_establish entry per bridge: 6 entries, 6 bridges
OK   the 6 entry bridge_ids are exactly the 6 promoted bridge ids, each once
OK   5 distinct bridged obligations (GroupProbe.C001 has two bridges): derived 5
OK   every manifest obligation is declared by a concept spec ([])
OK   README quotes the real accept-promotion command ('accept-promotion swisstable-verus-core --reviewer')
OK   README quotes the real record-ruling command ('record-ruling --reviewer $R --verdict ratified')
OK   README names the scratch reviewer used in the proof ('scratch-approval-proof')
OK   README quotes the real promotion_id ('PROM-SWISSTABLE-VERUS-CORE-001')
OK   README names the Stage 7 manifest ('ci/manifest/WP-SWISSTABLE-VERUS.json')
OK   README records the G9 failure mode ('predicate application only')
OK   README's record-ruling block lists all 48 artifacts (48)
OK   README's accept-promotion block lists all 48 artifacts (48)
OK   the ruling covers exactly the artifacts the promotion accepts
OK   no artifact is listed twice in the ruling
OK   README's quoted check-runbook-29.py output is this run's own output (38 checks)

OK: every count and hash this README quotes is the derived one, not a remembered one.
0
```

The block above is **generated, not retyped**. `check-runbook-29.py`'s last assertion
(`README's quoted check-runbook-29.py output is this run's own output`) re-reads this
fenced block and requires it to equal the script's own live output, line for line --
including the full 64-character `gate_integrity` digests above. Two reviews in a row
caught a quoted number here going stale, the second time in the very block that exists to
prevent exactly that, so the quote is now checked instead of trusted.

If you add, remove or reword any assertion, regenerate it:

```
python3 analysis/ligature/stage4-7/refresh-quoted-block-29.py
```

It is idempotent, and it refuses to write if the checker fails on anything other than the
quote itself.

Four of these guard the *commands above* rather than a prose claim:
`check-runbook-29.py` parses this README's own two fenced command blocks, extracts the
`--artifact` paths, and fails unless each carries all 48 and the ruling covers exactly the
set the promotion accepts. A typo in either block, or an artifact added to one and not
the other, is caught mechanically.

`analysis/ligature/stage0-3/check-runbook.py` (chainlink #28's, unchanged by this issue)
also still exits 0 after this section was added.

## The Rust port and its Verus annotations (chainlink #30)

Seven modules, suppliers first, under `rust/swisstable-verus-core/`:

| module | concept | manifest functions |
|---|---|---|
| `src/hash_mix.rs` | HashMix | `h1`, `h2`, `from_hash` |
| `src/control_bytes.rs` | ControlBytes | `is_empty`, `is_dead`, `is_full`, `is_empty_or_deleted`, `count_empty`, `set_full`, `set_dead`, `set_empty`, `clear_dead` |
| `src/group_probe.rs` | GroupProbe | `match_full`, `match_empty_or_deleted`, `count_empty`, `load` |
| `src/probe_seq.rs` | ProbeSeq | `offset`, `index`, `offset_at`, `from_capacity_and_h1`, `advance` |
| `src/raw_table.rs` | RawTable | `len`, `capacity`, `is_full`, `find`, `insert`, `erase`, `resize` |
| `src/table_iterator.rs` | TableIterator | `is_end`, `offset`, `advance`, `rewind_to_full` |
| `src/swiss_table.rs` | SwissTable | `len`, `contains`, `insert`, `erase`, `reserve` |

`verif/lemmas.rs` holds the manual lemmas — the bit-vector bridge, the control-byte
classification lemmas, and the counting lemma `resize` rests on.
`verif/reachability_probe.rs` is a **standalone** probe (it declares its own lemmas and
imports nothing from the crate, so it verifies on its own) pinning what Verus
0.2026.05.24 can and cannot say about integer bit operations.

### How to run it

```
bash analysis/verus/run-verus.sh          # transcript -> analysis/verus/verus-transcript.txt
bash analysis/verus/run-cargo.sh          # transcript -> analysis/verus/cargo-transcript.txt
```

Both runners overwrite their transcripts on every run. The Verus one is
authoritative for the verified/error counts; the Cargo one covers `cargo build`,
`cargo test` and `cargo verus verify`, which reach the same proofs through a
different front end (`swisstable-verus-010`).

### Correction: the bitwise "blocker" from attempt 1 was wrong

Attempt 1 recorded `swisstable-verus-012` as a **blocker**: *"Verus 0.2026.05.24
supplies no axioms at all for integer `BitAnd`/`BitOr`/`BitXor` or `Shl`/`Shr` on
u64"*. That is false, and it was load-bearing: on the strength of it the port
rewrote three of the reference's own operators, and `revisit_trigger` pointed the
operator at a Verus upgrade that does not exist.

The reviewer reproduced the refutation on the same pinned binary, and so does this
tree. `#[verifier::bit_vector]` proof functions are first-class in that release,
and everything the finding called impossible verifies:

| fact | bridge lemma | verified |
|---|---|---|
| `x & m <= m`, `x & m <= x` | `lemma_and_below`, `lemma_and_below_usize` | yes |
| `x >> 57 < 128` and `x >> 57 == x / 2^57` | `lemma_shr57` | yes |
| `1u64 << bits >= 1`, `<= 2^62` | `lemma_pow2_range` | yes |
| `2^n - 1 <= 0xFFFF_FFFF` for `n <= 31` | `lemma_slots_at_least_group`, `lemma_slots_roundtrip` | yes |
| `(mask \| (1u16 << i)) >> i & 1 == 1` | `lemma_bit_set` | yes |

Plain integer mode already verifies `r == hash >> 57` on its own, so `Shr` on u64
*is* axiomatised — the exact opposite of what attempt 1 asserted. The
`analysis/verus/reachability-probe.txt` reads `12 verified, 4 errors`: the
`errors` are the four negative cases described under `swisstable-verus-016` below,
each of which the probe file itself marks as expected to fail.

Attempt 2 therefore **reverted the substitutions** and restored the reference's
operators, which is where they belong:

* `src/hash_mix.rs` computes `hash >> 57` again, not `hash / 2^57`
  (`swisstable-spec-006` withdrawn).
* `src/probe_seq.rs` wraps with `& capacity_mask` again, not `% capacity_size`
  (`swisstable-spec-004` withdrawn). `capacity_size` survives only as the overflow
  bound that keeps `offset_ + index_` inside `u64`.
* `src/group_probe.rs` returns `uint16_t` masks again, not a 16-element boolean
  vector (`swisstable-spec-005` withdrawn).

Because `lemma_shr57` proves `x >> 57 == x / 2^57` *inside the proof*, the
differential oracle (#32) does not have to carry that equivalence either. The
ledger keeps the whole correction, not just the corrected text:
`swisstable-verus-012` is restated from `blocker` to `friction`,
`swisstable-verus-014` records the process failure, and `swisstable-verus-015`
records the real — much smaller — limitation, which is only that an integer-mode
clause mentioning a bitwise operator needs its fact stated as a lemma first.

### What verifies, and what does not

> **HISTORICAL — attempt 9's state, superseded.** The crate now verifies with
> **0 errors**; see "Current #30 result and the tracked-Map follow-up" at the
> end of this file. Everything below this banner is kept because it records
> *which* defects the port had and *why* they were misdiagnosed, not because any
> of those numbers is current.

Captured by `bash analysis/verus/run-verus.sh`; both transcripts are overwritten on
every run, and `analysis/ligature/write-findings-30.py` reads its counts out of them
rather than carrying literals.

```
crate:  verification results:: 98 verified, 16 errors
        analysis/verus/verus-transcript.txt
probe:  verification results:: 10 verified, 4 errors
        analysis/verus/reachability-probe.txt
```

`python3 analysis/verus/err-summary.py` gives the primary error locations, and
`python3 analysis/verus/errors-by-fn.py` groups them by function:

```
35  src/raw_table.rs
20  src/swiss_table.rs

by function: insert 19  find 12  clear 7  resize 7  contains 5  erase 4  new_seq 1
```

**All 55 primary error locations are in those two modules.** `RawTable::new` and
`SwissTable::new` -- the constructor that gates every mutator of the subset -- are now
error-free, as are `hash_mix`, `control_bytes`, `group_probe`, `probe_seq`,
`table_iterator` and `verif/lemmas`. `hash_mix`,
`control_bytes`, `group_probe`, `probe_seq`, `table_iterator` and `verif/lemmas`
carry no errors -- and that is something the transcript supports rather than a claim.
Attempt 2 asserted the same thing while the transcript showed errors in
`control_bytes.rs`, `probe_seq.rs` and `table_iterator.rs`; it was right to be pulled
up. Those were fixed in attempt 3: `clear_dead` became a map into a fresh `Vec`
(which is what upstream's `Subtract` is), `well_formed` gained the per-byte
classification, and `TableIterator`'s loops stopped carrying a frame quantifier.

Four things changed this time, and all four are recorded:

* `swisstable-verus-018`: **every `requires` clause written against `usize::MAX` was
  unsatisfiable**, because this Verus cannot name `usize::MAX` at all. That is why
  `RawTable::new` -- the entry point for every mutator of the subset -- was failing.
  `ControlBytes::new` and `SwissTable::reserve` -- two sites, not the three an earlier
  revision of this row claimed -- are now stated against the literal `0x7FFF_FFFF`,
  by tightening `lemma_slots_roundtrip` to that bound rather than the `0xFFFF_FFFF` it
  carried, which is what actually discharges `raw_table.rs:138` and with it the whole
  of `RawTable::new`. An earlier claim that `lemma_full_count_zero` and
  `lemma_free_count_zero` were what discharged it is withdrawn (see the third bullet).
  One site still needs `usize::MAX`: `GroupProbe::load`'s loop invariant, where the
  index check
  needs the type's maximum; the split form was tried and does not discharge it, so it
  is documented in place rather than left looking clean.
* **A second false postcondition, of the same class as -019.**
  `RawTable::new` asserted `!has_free_slot()`. That is false: a fresh table's control
  bytes are all `kEmpty`, so it has a free slot. It had been "proved" with
  `lemma_free_count_zero`, whose precondition (`no byte is empty-or-deleted`)
  contradicts the very array it was applied to -- the precondition never discharged,
  which is why the function had errors at all. Now `t.has_free_slot()`, proved from
  the `ControlBytes::new` clause below. `lemma_free_count_zero` is deleted rather than
  left behind.
* `ControlBytes::new` now states that a fresh array is empty *everywhere* (real slots
  and padding), not merely that it is well-formed. Without that, `len_ == 0` was not
  derivable and the `new_seq`/`contains`/`clear` loops had nothing to stand on.
* `swisstable-verus-019`: **`RawTable::resize`'s `self.model()` loop invariant was
  false, not merely unproved.** `clear_dead()` turns every full byte into a tombstone
  while `hashes` still holds that slot's key, so `slot_model`'s
  `!is_full_spec(i) ==> slot_hash(i) == NO_HASH` cannot hold in that window. Replaced
  by `RawTable::reclaiming_model(before, before_hashes)`, which says what does hold.
* RawTable.C001's `2^n - 1` capacity shape is **not statable on the table's `usize`
  capacity at all** (`swisstable-verus-016`), so `model()` carries the half that
  survives (`5 <= capacity_bits <= 31`) while the shape stays proved on the `u64` mask
  in `ProbeSeq::well_formed`, where it verifies.

### `RawTable::insert` was verifying with its body writes missing (`swisstable-verus-022`)

Attempt 10's revert spliced from `let ghost before_hashes` to `(slot, true)`, removing
`set_full`, `hashes[slot] = hash` and `len_ = len_ + 1`. The function still returned
`(slot, true)` and satisfied its postconditions vacuously, so **attempts 10 and 11
reported `insert 18` and 54 locations — a number produced by a table that inserted
nothing.** With the writes restored the transcript reads `insert 19` and 55 locations.
Those two attempts' apparent improvement was an artefact, and any operator reading
their comments back should discount it. Restored at raw_table.rs:535-537.

### The erase path was specified so that it could not be called (`swisstable-verus-020`)

`SwissTable::erase` branched on `capacity() <= GROUP_WIDTH` and pre-wrote the
tombstone via `ctrl_mut().set_dead(slot)` before delegating. That makes
`is_full_spec(slot)` false while `hashes[slot]` still holds the key, which falsifies
`slot_model` and therefore `RawTable::erase`'s own `model()` precondition -- and also
its `stored_hashes().contains(...)` precondition, since `stored_hashes()` filters on
`is_full_spec`. The branch was dead besides: `capacity_bits >= 5` gives
`capacity >= 31 > 16`. A comment on `RawTable::erase` asserted the opposite and was
wrong.

Upstream's `EraseMetaOnlySmall` (raw_hash_set.cc:856) and `EraseMetaOnlyLarge` (:868),
called from raw_hash_set.h:3490/:3493, choose the control byte themselves, and
`RawTable::erase` already had that guard. So the container now just delegates;
the dead branch and the pre-write are gone, `ctrl_mut` is deleted (no sound
postcondition, no other caller), and the false comment is replaced. **erase 11 -> 4,
`swiss_table.rs` 27 -> 20.** The manifest's
`swiss_table_erase__to__control_bytes_set_dead` boundary edge is now unrealised --
upstream has no such call either, so it is filed as `swisstable-spec-008` for the
operator rather than edited.

### `WasNeverFull` branch correction found by #120 (`swisstable-verus-021`, `-030`)

The earlier verified counter and its recursive specification shared a subtle error:
every empty byte overwrote the count, so both retained the last empty position instead
of the leading run of non-empty bytes used by Abseil's `TrailingZeros` and
`LeadingZeros`. That made an isolated full slot look like a tombstone case even though
upstream clears it to `kEmpty`. The counters now stop advancing at the first empty;
the recursive definitions and step lemmas express the same rule. Concrete fixtures
verify `kEmpty` for one isolated full slot and `kDeleted` for a 16-slot occupied run.
Fresh crate verification after this correction is recorded under
`analysis/tracked-map-probe/`.

### The blocker is now filed as a tool limitation, not a strategy (`swisstable-verus-023`)

`-017`'s own commitment was that if the window-predicate pass did not come out clean,
this should be escalated as a Verus limitation on `ext_equal` over a derived
comprehension rather than re-recorded as a strategy. It did not come out clean, so that
is what it now is.

Four approaches have been implemented and measured, and none kept:

| approach | result |
|---|---|
| `assert_sets_equal!` + `group_set_axioms` broadcast | does not close |
| explicit `#[trigger]` on the existential | does not close |
| inline proof block in `insert` via `lemma_stored_in` | `insert` 21 → 27 |
| C004 restated pointwise over `stored_in`, no `Set` in the postcondition | expressible, still unclosed; `insert` 19 → 21, `SwissTable::insert` 20 → 22, total 55 → 57 |

The last is the cleanest form and the instructive failure: membership *is* visible —
`lemma_stored_in` proves `stored_hashes().contains(k) <==> stored_in(k)` and verifies —
but the two-directional extensionality does not follow from it, and the pointwise form
charges its cost to every caller that needs `contains_spec`. All four were reverted; the
crate sits at the better of the two states, not the most recent one.

### What is left, and why (`swisstable-verus-017`, severity `blocker`)

The task's deliverable -- a verifying port -- **does not exist yet.** Two clusters:

* `RawTable::resize`'s remaining loop invariants are not yet discharged.
* The derived-set obligations in `insert`/`erase`/`clear`/`contains` do not close. The blocker is specific and reproducible: the ghost model has to be
  *derived* (`stored_hashes()` is a `Set::new` comprehension existentially
  quantifying the slots, because a spec-valued field cannot be initialised from exec
  code -- `swisstable-verus-011`), so every obligation over it reduces to a set
  extensionality step, and **that step will not fire in this vstd**.
  `assert_sets_equal!` fails even with `vstd::set::group_set_axioms` broadcast, and
  an explicit `#[trigger]` on the existential does not help either. What *does* work is
  `lemma_stored_in`, which proves `stored_hashes().contains(k) <==> stored_in(k)`
  through the named predicate `RawTable::stored_at`; it verifies and is in the tree.
  Proving the extensionality inline in `insert` instead failed for a related reason
  worth recording: it needs `model()` *mid-function*, after the control byte and hash
  are written, and `model()` is false there by construction. So the obstacle is no
  longer seeing through `Set::new`; it is having a predicate available where `model()`
  still holds -- a structuring question about each mutator, not a missing lemma.

Nothing was stubbed. A draft that used `#[verifier::external_body]` was deleted
rather than kept: there is no `assume`, `admit`, `external_body` or `axiom fn`
anywhere in the port.

### Correction: "usize is 32 bits" was not evidenced, and is retracted

Attempt 3 claimed Verus models `usize` as 32 bits, on the strength of
`probe_usize_is_32_bits` -- whose postcondition restated its own body. That is a
tautology: it verifies for any width and proves nothing. **The same defect attempt 3
claimed to have corrected in the round-trip probes, left in place one function
later.** Asserted as the literal `4`, it fails:

```
size_of::<usize>() as u64 == 4                      fails -- size_of is opaque
usize::MAX as u64 == 0xFFFF_FFFF                   fails -- neither 32- nor 64-bit
fn(x: u64) -> usize, r as u64 == x                  fails -- narrowing is opaque
fn(x: u64) -> usize, r as int == x as int          fails -- same, int view
```

So this build says nothing useful about `usize`, and no claim is made about its
width. What *is* proved and load-bearing is the third row: a narrowing cast to
`usize` cannot be related to its source in either view, which is why
`ProbeSeq::offset`/`offset_at` state ProbeSeq.C002 over the `int` view. The
capacity cap is now derived only from `lemma_slots_roundtrip`
(`2^bits - 1 <= 0xFFFF_FFFF`, the smallest bound nameable here), not from a claimed
width.

### Third defect in the staged drafts, found while proving

* `swisstable-spec-003`: drafted `ProbeSeq.C001` has no upper bound on
  `capacity_bits`, and the port needs one. Two consequences, both documented in
  code: `capacity_bits <= 62` is added so `offset_ + index_` cannot overflow, and
  drafted `ProbeSeq.C003`'s `index_ <= capacity_mask + 1` turns out **not to be an
  invariant at all** — upstream's `index_ += Width` is uncapped, so the bound
  became a precondition of `index()`. Separately, `RawTable::new` needs
  `5 <= capacity_bits`, one more than C001 states: the smallest drafted capacity,
  `2^4 - 1 == 15`, is one slot short of a group, and `ControlBytes` needs
  `capacity >= 16`.

### Two more defects in the staged drafts, found while implementing

* `swisstable-spec-001`: staged `ControlBytes.C006` clause 3 ("never turns a deleted
  byte into an empty one") contradicts the reference and the concept's own command
  text for `clear_dead`, and `resize` depends on it being false.
* `swisstable-spec-002`: staged `GroupProbe.C001`/`C004` bound the group window as
  `base + 16 <= capacity`, which no group-aligned base can satisfy for the last
  group of any `2^n - 1` table.

All three are `.draft` and unapproved, so they are for the operator's Stage 4 batch,
not for this issue to fix.

### Remaining decision

`project-descriptor.json` remains untouched. #35 confirmed that the current Rust
source has no unsafe raw-slot layer to route to Kani. The initialized parallel
Vec representation remains the implementation; its physical lifetime and
address differences remain documented in `swisstable-verus-001`. #36 records the
current scalar-only P2 boundary as a SIMD scope cut; no Kani sub-cluster is
present. `E-010` remains deferred for operator review. The port's current
representation is described in `src/raw_table.rs`'s module docs.

## #30 operator ruling and re-scoped verification

**Historical snapshot (2026-10-02, before the ruling):** the following 98/16
transcript and the discussion of options (a)/(b) describe the old, set-level
contract. They are retained as evidence of why that contract was changed, **not**
as the current Verus result or an outstanding request for a decision.

At the 2026-10-02 checkpoint, `bash analysis/verus/run-verus.sh` reported:

```
crate:  verification results:: 98 verified, 16 errors   (55 primary locations)
probe:  verification results:: 10 verified, 4 errors    (4 primary locations)
   35  src/raw_table.rs
   20  src/swiss_table.rs
   --
   55  total
insert 19  find 12  clear 7  resize 7  contains 5  erase 4  new_seq 1
```

This distribution is **complete, not a floor**. The transcripts used to be captured
with `--multiple-errors 20` and end in `error: aborting due to 55 previous errors`, so
the emitted set could not be told apart from a truncated one, and the "the supplier
modules are error-free" claim rested on a run whose budget was smaller than its error
count. `run-verus.sh` now captures at `--multiple-errors 200`
(`VERUS_ERROR_BUDGET` overrides it) and the result is identical to the digit:
98 verified / 16 errors, 55 locations, the same 35/20 split, the same seven-function
breakdown. The abort is Verus's own, not the budget's, so the counts above are the
whole set and the suppliers really are error-free (`swisstable-verus-024`).

Every mutator and every probe loop in the subset still carries unproved obligations. Four
extensionality strategies were implemented and measured (`swisstable-verus-023`); the
fourth is the informative one — the membership *is* provable (`lemma_stored_in`
verifies) but the two-directional set equality over the derived `Set::new` does not
follow from it in this vstd, and the pointwise restatement charges its cost to every
caller.

### The decision

**(a) Accept the two scope cuts** — `swisstable-verus-009` (`SwissTable::insert`
requires `has_free_slot()` and never grows; growth is reached only through an
explicit `reserve` -> `resize` call, so rehash is *reachable* but not *on the insert
path*) and `swisstable-verus-023` (set extensionality over a derived `Set::new` does
not close) — for this pilot. If so, #30 should be re-scoped to a proving pass over an
agreed contract shape: the mutators verified against a per-slot frame condition or a
counting contract, with the set-level obligations explicitly out of scope and recorded
as such.

**(b) Authorise a different model representation for the ghost set** as an explicit
design change, e.g. a bounded or quantified-free encoding, or a ghost collection whose
frame Verus can maintain incrementally. Note that `swisstable-verus-011` already rules
out the obvious alternative — a spec-valued field initialised at construction — because
Verus cannot initialise one from executable code.

That was the decision requested at the time; it was made in chainlink #30's
operator comment of 2026-10-02. The operator chose **(a)**: `-009` (explicit
reserve/resize rather than automatic insert growth) and `-023` (set-level
extensionality) are accepted pilot limitations. Set-level mutator postconditions
are **out of scope**; the proof target is per-slot frames, bidirectional per-slot
survival across rehash, counts, and iteration. No fifth extensionality variant is
authorized. The same ruling requires `erase` to follow upstream's `WasNeverFull`
branch. The port now computes it from the control-byte windows in
`ControlBytes::was_never_full` and branches inside `RawTable::erase`; the older
claim that it depended on `growth_info()` was wrong for the pinned source.

Use `bash analysis/verus/run-verus.sh` and its freshly overwritten
`analysis/verus/verus-transcript.txt` for the **current** counts, not the historical
block above. The standalone reachability probe intentionally includes four
negative cases and is not the crate proof result.

### The Cargo package (authorised under `GW-c2008009a9d2`, one protected-root file)

`rust/swisstable-verus-core/Cargo.toml` was scaffolded by Ligature 1.2.2 and then,
under the operator's 2026-10-03 authorisation, given the three lines the generic
template deliberately omits: `[dependencies] vstd = "=0.0.0-2026-05-24-0157"`,
`[package.metadata.verus] verify = true`, and (in the source) the
`#[cfg(verus_only)]` guards on proof-only imports. Without the metadata key
`cargo verus verify` prints `WARNING: You asked for verification, but cargo did not
find any crates that opted into verification` and degrades to `cargo check`; without
the `vstd` dependency neither `cargo check` nor the driver can resolve `vstd` or the
`verus!` macro. `bash analysis/verus/run-cargo.sh` captures all three Cargo entry
points to `analysis/verus/cargo-transcript.txt`; it touches `src/lib.rs` first,
because a *second* `cargo verus verify` is a cached no-op that prints no
`verification results` line at all and would otherwise record a green run that
verified nothing. The section 6.5 document is at `PORT-GAPS.md`.

## Current #30 result and #120 tracked-Map probe

#30 closed on 2026-10-08 after Ligature 1.3.3 was current, the reliance-policy
checkpoint was accepted with reviewer `codex` and version
`swisstable-verus-reliance-policy@1.0`, and the sanctioned crate profile and technical
gates passed. The closure record is Chainlink comment #264. The closure did not claim
C++/Rust oracle parity; `cargo test` discovered zero runtime tests.

The follow-up #120 probe reproduced tracked-Map P1 and P2 independently with the pinned
Verus binary: each reports `verification results:: 4 verified, 0 errors`. In an
analysis-only clone, the executable table owns `Tracked<LiveIndex>` and the tracked
struct stores `Map<u64, usize>` from each live hash to its physical slot. Insert,
erase, clear, and resize preserve the direct two-way map/slot relation. The erase
method's verified postconditions cover both `WasNeverFull` branches and preserve the
map model after removing the key. Concrete window fixtures verify the `kEmpty` and
`kDeleted` cases. The bounded resize proof keeps the existing frame/counting and
source/destination placement obligations; the `SwissTable::reserve` smoke confirms a
key's value is at its final tracked-map slot after resizing. The vstd
`Map::tracked_borrow_mut` operation is not used; `Tracked::borrow_mut()` only accesses
the wrapped tracked struct. No source/destination obligation was dropped. An optional
assertion that this key's numeric slot changed was not discharged; the accepted claim is
value preservation at the final map-selected slot, not a particular index delta. The
failed assertion and transcript are retained in the evidence folder.

The erase probes exposed the counter bug described above. It is fixed in the pilot's
`control_bytes.rs`; the fresh production run reports `verification results:: 149
verified, 0 errors`. The full tracked-map analysis clone, including resize and value
remapping, reports `verification results:: 154 verified, 0 errors`. Reproduction
sources and full transcripts are in [analysis/tracked-map-probe](analysis/tracked-map-probe/).

The representation is **not adopted in production**. The current per-slot/frame and
counting contracts remain unchanged. Pinned vstd `Map::tracked_empty`,
`tracked_insert`, and `tracked_remove` are axiom functions, and P2/integration also
broadcast vstd map/set axiom groups; their TCB cost is recorded in
[the TCB note](analysis/tracked-map-probe/tcb.md). The experiment proves a bounded
representation slice, not the former `Set::new` extensionality clauses.

**Operator decision (2026-10-08):** keep the 2026-10-02 ruling. The tracked Map is
not adopted in production; the accepted per-slot/frame and counting contracts remain.
Reconsider only after an explicit future decision to reverse the ruling. #34 remains
focused on its separate Vec-backed control-byte representation question.
