# codesight-mcp analysis of the P2 SwissTable subset (chainlink #26)

Repository: `local/upstream-757424f7156f` (auto-generated; read back from
`index-folder`'s own `"repo"` field, never guessed)
Source: `upstream/abseil-cpp` at commit `2065f4ded0558c6f89fee67c8e5228feb4eb960e`,
tag `20260817.0`
Index storage: `analysis/codesight/index`
Allowed roots: this pilot's `upstream/` and `rust/` only, the two values in
`swisstable-verus/.mcp.json`
Tool: `tools/codesight-mcp/.venv/bin/codesight-mcp`, codesight-mcp 0.6.0
(git `816d523a1126b210afffa8a422760bbfce42f5f6`), tree-sitter 0.26.0,
tree-sitter-c 0.24.2, tree-sitter-cpp 0.23.4

Subset in scope: open addressing, group probing (scalar then optional SIMD),
tombstones, erase, rehash, iteration.

## Reproducing this directory

```
cd swisstable-verus/analysis/codesight
./run-all.sh            # the 142 recorded calls -> *.json plus *.json.exit
./summarize-results.py  # one row per artefact: op, exit code, result count
./index-coverage.py ../../.. > index-coverage.txt   # index census vs the on-disk tree
./subset-census.py ../../.. > census-report.txt      # per-file extracted-vs-missing census
./outline-coverage.py index get-file-outline-*.json > outline-coverage.txt
./index-determinism.sh  # is the index build reproducible?
./tree-sitter-probes.sh # controlled 13-file tree-sitter probes, in /tmp
```

`run-codesight.sh` is the single entry point for every recorded call: it exports
this pilot's `CODE_INDEX_PATH` and `CODESIGHT_ALLOWED_ROOTS`, keeps the tool's
`[codesight] <op>` header verbatim on line 1 so the JSON body starts on line 2,
and writes the process exit status to a sidecar `<artefact>.exit` next to each
artefact. `index-coverage.py`, `subset-census.py`, `outline-coverage.py`,
`dump-symbols.py` and `summarize.py` read the artefacts back; none of them calls
the tool, so the recorded numbers can be re-derived without a re-index.

`tree-sitter-probes.sh` and `index-determinism.sh` deliberately run outside the
pilot (scratch trees under `/tmp/opencode/`), so neither the pinned upstream
checkout nor the pilot's own index is touched.

## Index

`index-folder-upstream.json` — 685 files, 10735 symbols, `"success": true`,
languages `{cpp: 490, c: 184, cmake: 2, python: 6, yaml: 2, json: 1}`,
`--use-ai-summaries false`.
`verify-index.json` — `"passed": true` on all five checks (exists, version 2,
freshness, 10735 symbols, content integrity 5/5).
`get-status.json`, `list-repos.json` — one repository, version 2, age 0 days.

## Artefact inventory

142 recorded calls, 88 exit 0 and 54 exit 1, every one with a `.exit` sidecar:

| op | calls |
|---|---|
| `get-callers` | 63 |
| `get-callees` | 38 |
| `get-file-outline` | 11 |
| `get-imports` | 9 |
| `get-type-hierarchy` | 7 |
| `get-call-chain` | 4 |
| `get-diagram` | 3 |
| `get-impact` | 2 |
| `index-folder`, `verify`, `list-repos`, `get-status`, `get-file-tree` | 5 |

By subset area, the graph operations that resolved a symbol and the ones that
answered `Symbol not found` at exit 1:

| area | resolved | not found | total |
|---|---|---|---|
| group probing | 13 | 16 | 29 |
| iteration | 17 | 5 | 22 |
| rehash | 10 | 17 | 27 |
| tombstones | 9 | 6 | 15 |
| erase | 2 | 8 | 10 |
| open addressing | 7 | 0 | 7 |

58 resolved, 52 `Symbol not found`. 82 caller/callee edges were returned in
total, 48 of them with an endpoint outside `raw_hash_set.cc`.

## What the index actually holds for the subset

`subset-census.py` output is in `census-report.txt`, the per-definition table in
`subset-census.tsv`.

| file | bytes | symbols in index | distinct names |
|---|---|---|---|
| `absl/container/internal/raw_hash_set.cc` | 105132 | 70 | 67 |
| `absl/container/internal/raw_hash_set.h` | 170433 | 121 | 91 |
| `absl/container/internal/hashtable_control_bytes.h` | 20282 | 1 | 1 (`class`) |
| `absl/container/internal/node_slot_policy.h` | 2943 | 1 | 1 (`element`) |
| `absl/container/internal/raw_hash_set_resize_impl.h` | 2690 | 1 | 1 (`(module)`) |
| `absl/container/internal/raw_hash_map.h` | 18219 | — | **file absent from the index** |

Language detection is the root cause and it is exact: `index-coverage.py` reports
`language=c` for all 183 indexed `.h` files and `language=cpp` for all 490 `.cc`
files, with zero `.cc` files misdetected. Both grammars are installed, so this
is the tool's extension-to-language table, not a missing dependency. The C
grammar keeps no class scope, which is why `hashtable_control_bytes.h` — the
tombstone class — collapses to a single symbol whose name is the literal string
`class`, and `node_slot_policy.h` to `element`.

226 of the 900 on-disk C/C++ sources (202 `.h` and all 24 `.inc`) are silently
absent from the index while `index-folder` reports success.

### Contingency over the 318 definitions the scan finds but the index misses

```
 163  raw_hash_set.h               in a class/struct body
  34  raw_hash_set.h               in a class/struct body, template
  31  hashtable_control_bytes.h    in a class/struct body
  27  raw_hash_set.cc              __restrict in the parameter list
  18  raw_hash_set.h               top level
  17  raw_hash_set.h               top level, template
   5  hashtable_control_bytes.h    top level
   4  raw_hash_set.cc              top level
   4  raw_hash_set.cc              in a class/struct body
   3  node_slot_policy.h           in a class/struct body, template
   3  raw_hash_set.cc              __restrict, macro-prefixed
   3  raw_hash_set.cc              __restrict, template
   2  raw_hash_set.cc              in a class/struct body, __restrict
   1  hashtable_control_bytes.h    top level, template
   1  node_slot_policy.h           in a class/struct body
   1  raw_hash_set.cc              macro-prefixed
   1  raw_hash_set.cc              template
```

35 of the misses in `raw_hash_set.cc` carry `__restrict`, and all 43 `__restrict`
uses in that file are written `const PolicyFunctions& __restrict policy`. The
controlled probe in `tree-sitter-probes/p10-restrict.cc` pins this down:
`PlainParam(Policy&)` and `RestrictPointer(Policy* __restrict)` are extracted;
the three definitions with `const Policy& __restrict` are not. So it is
restrict-on-reference specifically, not restrict at all, and not templates —
`tree-sitter-probes/p2-function-template.cc` has all three of its function
templates extracted.

### Controlled tree-sitter probes

`tree-sitter-probes/` holds the reply to a 13-file scratch tree, indexed as
`local/src-ccaa3d8f3415`; 9 of the 13 files were indexed. Each probe isolates one
cause:

| probe | isolates | result |
|---|---|---|
| `p1-plain-functions.cc` | baseline free functions in a `.cc` | all 3 extracted |
| `p2-function-template.cc` | `template <class T>` | all 3 extracted — templates are fine |
| `p3-class.h` | class members in a `.h` | only the inline-bodied member `MethodC`; the class and its declarations are gone |
| `p4-class-template.h` | a class template in a `.h` | **file absent from the index** |
| `p5-includes-plain.h` | 4 unconditional includes in a `.h` | 0 imports reported |
| `p6-includes-simd.h` | `#ifdef`-guarded SIMD includes | 0 imports reported |
| `p7-simd-class.cc` | SIMD wrapper class + guarded include | 1 of 2 includes; the class's declarations are gone, the class survives |
| `p8-macro-body.cc` | macro before the return type | both macro-prefixed definitions dropped, the plain one kept |
| `p9-nested-scope.h` | two structs sharing member names in a `.h` | **file absent from the index** |
| `p10-restrict.cc` | `__restrict` on reference vs pointer | 3 of 6 dropped, exactly the restrict-on-reference ones |
| `p11-restrict-in-header.h` | same, in a `.h` | **file absent from the index** |
| `p12-template-struct-only.h` | template struct + includes, no top-level function | **file absent from the index** |
| `p13-namespace-macro-header.h` | one top-level function + includes | 1 symbol, 0 imports |

The `.h`-drop set (`p4`, `p9`, `p11`, `p12`) is content-dependent and
reproducible in ten-line files, but no probe isolates the trigger, and the tool
gives no diagnostic. What *is* established and quantified for the real tree is the
drop itself: 226 sources, `success: true`, no warning.

### Index determinism

`index-determinism.sh` builds the same scratch tree twice from scratch into two
index directories and diffs the symbol tables
(`tree-sitter-probes/determinism-run{1,2}-symbols.txt`): identical. So the
artefacts in this directory are reproducible and the gaps above are properties
of the input, not build noise.

## Results per subset area

### Open addressing

Resolvable and connected: `get-callers-open-addressing-H1.json` returns exactly
one caller, `raw_hash_set.cc::find_first_non_full` (L207), at depth 1.
`get-callers-open-addressing-RehashProbabilityConstant.json` returns 4 callers
including `ShouldRehashForBugDetection` (L94) and `CommonFieldsGenerationInfoEnabled::should_rehash_for_bug_detection_on_insert` (L158).
`get-callees-open-addressing-{H1,H2,RehashProbabilityConstant}.json` all report
0 callees, which is correct: these are arithmetic leaf functions.

`get-call-chain-open-addressing-H1-to-probe_till.json` returns `path_count 0`.
The real chain runs `H1` → `probe_seq::offset` → `probe_seq::next`, and neither
`probe_h1` (raw_hash_set.h L1800) nor `probe` (L1803, L1806) is in the index.

### Group probing — scalar then optional SIMD

The best-verified area: it is the only one whose recorded edges are all
`.cc`-to-`.cc` and all check out against the source.
`probe_till_first_non_full_group` (raw_hash_set.cc L175) has 3 callers and 3
callees, and `get-impact-group-probing-probe_till_first_non_full_group.json`
reports `impacted_count 3`, `affected_file_count 3`:

```
find_first_non_full ──▶ find_first_non_full_from_h1 ──▶ probe_till_first_non_full_group
find_first_non_full ──▶ find_first_non_full_group
```

`BlockControlBytes` (L585) has 1 caller and 2 callees — it is where blocked
elements become `kSentinel`, i.e. the tombstone side of the boundary.

The SIMD half is entirely absent. `Group`, `GroupImpl`, `NonIterableBitMask`,
`probe_seq`, `Simd`, `Match`, `MatchFull`, `MatchEmptyOrDeleted` all answer
`Symbol not found` at exit 1 — 16 `get-callers`/`get-callees` artefacts in this
area are negative results, and they are negative because the symbols do not
exist in the index, not because the relationships are absent. In the source the
SIMD groups live in `hashtable_control_bytes.h` as `GroupSse2Impl` (L286) and
`GroupAArch64Impl` (L369), in a file whose entire symbol table is one entry named
`class`.

### Tombstones

`EraseMetaOnlySmall` (L856) — 0 callers, 4 callees.
`EraseMetaOnlyLarge` (L868) — 0 callers, 2 callees.
`ConvertDeletedToEmptyAndFullToDeleted` (L434) — 2 callers, 1 callee.
`GrowthInfoAccessor::OverwriteFullAsEmpty` (L421) — 0 callers, 1 callee.

`get-type-hierarchy-tombstones-ctrl-class.json` returns exit 0 with
`parent_count 0, child_count 0` for the one symbol the control-byte header does
have, and the six control-byte helpers the subset actually needs —
`IsDeleted`, `IsEmpty`, `MakeDeleted`, `MakeEmpty`, `H1`, `H2` — are six
`Symbol not found` exits at 1. The tombstone predicate set is exactly what a
Verus port has to model, and it is what the index drops.

`get-call-chain-tombstones-probe-to-EraseMetaOnlyLarge.json`: `path_count 0`.

### Erase

Thinnest area. `erase_meta_only`, `erase_meta_only_small`, `erase_meta_only_large`
in the header, and `EraseImpl`, `EraseSingleElement`, `EraseWithoutRehash`,
`EraseWithRehash`, `ClearBackingArray` in the `.cc` are all `Symbol not found` at
exit 1 (8 artefacts). Only `DecrementSmallSize` (0 callers) and `DestroySlots`
(2 callers) resolve, and neither is on the erase path the port needs.

### Rehash

Same shape, worse. `Resize`, `ResizeImpl`, `ResizeWithoutDeletingOrCreatingNewSlots`,
`NormalizeCapacity`, `GrowToNextCapacity`, `RehashOrGrowToNextCapacityAndPrepareInsert`,
`DropDeletesWithoutResizeAndPrepareInsert` — all absent. The whole template layer
of the resize algorithm is missing, because every one of them takes
`const PolicyFunctions& __restrict policy`.

What does resolve is informative:
`get-callers-rehash-h-NextCapacity.json` returns 11 callers (the capacity
arithmetic is the most-called thing in the header), `PreviousCapacity` 2,
`Resize1To3NewOffset` 0 callers / 2 callees, `ResetGrowthLeft` 0/0,
`GrowthInfoAccessor::InitGrowthLeftNoDeleted` 0/1,
`GrowIntoSingleGroupShuffleControlBytes` 0/0.

`raw_hash_set_resize_impl.h` — the file that exists precisely so the resize
algorithm can be unit-tested, and the file the upstream
`absl_raw_hash_set_resize_impl_test` target exercises — is in the index as one
symbol named `(module)`. Its three `using` aliases (`ProbedItem4Bytes`,
`ProbedItem8Bytes`, `ProbedItem16Bytes`) and the whole `ProbedItemImpl` template
are gone. All three of its own
`get-callers-rehash-resize-impl-*.json` probes answer `Symbol not found`.

### Iteration

The most heavily connected area, and the one carrying the false edges.
`begin` (raw_hash_set.h L2753) has 5 callees: `end`, `skip_empty_or_deleted`,
`slot_array`, `NumControlBytes`, `IsSmallCapacity`.
`skip_empty_or_deleted` (L2451) has 1 caller. `next` has 9 callers and `offset`
has 8.

`get-call-chain-iteration-begin-to-skip_empty.json` returns one one-hop path.

## Two kinds of wrong answer, and they need to be told apart

**Absent.** The `Symbol not found` exits, and the 226 dropped sources. Absence is
recoverable: the source is right there.

**Confidently wrong.** Because the `.h` parse keeps no class scope, every member
becomes a bare file-level name and calls resolve by unqualified name across the
whole repository. Two examples, both checked against the pinned source:

1. `get-callees-iteration-assert_is_full.json` reports that
   `raw_hash_set.h::assert_is_full` (L2445, body
   `AssertIsFull(ctrl_, slot_, generation(), generation_ptr(), operation);`)
   has exactly one callee: `generation` at
   `absl/container/internal/btree.h` L1094, which is
   `btree_iterator_generation_info_disabled::generation`. The real callee,
   `AssertIsFull`, is at `raw_hash_set.h` L1586 and is not in the index at all.
2. `get-callers-iteration-next.json` reports `Incr` (L148), `IncrBy` (L156) and
   `block_end` (L532) from `absl/container/internal/chunked_queue.h`, plus
   `main` from `raw_hash_set_probe_benchmark.cc`, as callers of
   `raw_hash_set.h::next` — which is `probe_seq::next()`. None of them call it.

Both are exit 0 with no warning. The practical rule this directory follows is
that no edge whose endpoints are bare `.h` names is used as evidence; the
recorded edges that *are* used all have both endpoints in `.cc` files or are
`.h` free functions with unique names in the file.

`get-diagram-call-graph-group-probing.json` (7 nodes, 6 edges) and
`get-diagram-imports-internal.json` (58 nodes, 10 edges over
`absl/container/internal`) are included because they are the ops a reader is most
likely to reach for next, and both inherit the same caveat.

## Other operations

`get-imports` forward works on the two big files — `raw_hash_set.cc` 22 imports,
`raw_hash_set.h` 41 — and resolves `hashtable_control_bytes.h`,
`container_memory.h`, `hashtablez_sampler.h`, `raw_hash_set_resize_impl.h` and
`hash.h` to real files. Reverse (`--direction importers`) returns
`result_count 0` for all five subset files. `hashtable_control_bytes.h` has 11
`#include` directives and reports 0 forward, as does `node_slot_policy.h`; only
`raw_hash_set_resize_impl.h` (3 directives) reports 3.

`get-type-hierarchy` accepted three subset types and returned empty for all three
with exit 0; it does not distinguish "no hierarchy" from "no hierarchy data".

## Cross-check against `ligature extract-c-static`

Not done, and not doable at this stage: `extract-c-static` needs a
`project-descriptor.json`, `swisstable-verus/` has none yet (init is #27), and the
command dies with an unhandled `FileNotFoundError` traceback at exit 1 instead of
saying so — while `status`, `check` and `doctor` all handle the identical
condition gracefully. Escalated as **epic #1 #107**. The full transcript is at
`analysis/ligature/extract-c-static-transcript.txt`.

What *is* measurable now is codesight-mcp against the source, and that is what the
census and the probes above do: 226 of 900 sources missing, 197 class members
missing from `raw_hash_set.h` alone, 31 from `hashtable_control_bytes.h`, and 35
`__restrict`-bearing definitions missing from `raw_hash_set.cc`. Those are the
numbers the cross-check should be re-run against once #107 and #27 are done.

## Findings

13 lines appended to `swisstable-verus/findings/limitations.jsonl`
(`analysis/codesight/write-findings.py` is the generator):

| id | severity | one line |
|---|---|---|
| `swisstable-mcp-001` | blocker | `.h` is mapped to the C grammar, not C++; every header loses class scope |
| `swisstable-mcp-002` | scope-cut | 226 of 900 sources silently dropped, `success: true` |
| `swisstable-mcp-003` | blocker | lost scope produces confident false call edges (`assert_is_full` → `btree.h`) |
| `swisstable-mcp-004` | scope-cut | the subset's defining symbols (SIMD group, erase, rehash templates) are absent |
| `swisstable-mcp-005` | friction | `get-file-outline` shows only parentless symbols; 199 members hidden |
| `swisstable-mcp-006` | friction | `__restrict` on a reference parameter suppresses extraction |
| `swisstable-mcp-007` | friction | reverse import lookup returns 0 everywhere |
| `swisstable-mcp-008` | friction | includes unreported for most `.h`; `#ifdef`-guarded includes dropped even in `.cc` |
| `swisstable-mcp-009` | friction | `get-type-hierarchy` returns silent empty for every subset type |
| `swisstable-mcp-010` | friction | no cross-area call chain found; 3 of 4 recorded chains empty |
| `swisstable-mcp-011` | friction | `index-folder`'s `files` array is a 20-entry preview, not a census |
| `swisstable-mcp-012` | friction | positive control: the index build is deterministic |
| `swisstable-ligature-001` | blocker | `extract-c-static` crashes on a missing descriptor → epic #1 #107 |

## Scope note

Nothing outside `swisstable-verus/` was written. No ligature pipeline stage was
run: no `init`, no `draft`, no `approve`, nothing past where the issue graph puts
this work, and `project-descriptor.json` still does not exist in this root. The
pinned upstream checkout was not modified — the controlled probes run in scratch
trees under `/tmp/opencode/`. `flake.nix` and `flake.lock` at the workspace root
were not touched.