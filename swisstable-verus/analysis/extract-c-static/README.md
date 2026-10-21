# codesight-mcp vs ligature extract-c-static (chainlink #108)

Deferred from #26, run after #27 initialised this root. Binary: this pilot's
`tools/ligature/ligature.pyz`, `sha256sum -c SHA256SUMS` -> `ligature.pyz: OK`,
`ligature 1.2.0`. Target triple `x86_64-unknown-linux-gnu`.

## The headline, and the one thing this directory does not claim

**`extract-c-static` scans Rust only; codesight-mcp indexes C++ only. There is
no input on which both tools answer the same question**, so a single
"agreement/disagreement about the C++ call sites" number does not exist and
none is given here. `swisstable-verus/rust/` still holds only `.gitkeep` --
the crate the #27 descriptor declares is a later issue, and its `Cargo.toml`
is a `protected_root`. What *is* measurable is two axes, kept apart:

* **Axis 1, real:** codesight-mcp's 101 recorded caller/callee artefacts
  against the pinned C++ source, with 63 hand-verified true call edges.
* **Axis 2, extractor capability:** `extract-c-static` over a hand-written
  Rust transcription of the same subset. This measures what shape of call the
  extractor can see. It does not measure the abseil call graph.

`subset-port/` is a transcription, not a port. It is here so ligature has
something to scan, and every edge in it is cited back to a C++ line in
`edge-truth.tsv`, so the fixture is auditable rather than load-bearing.

## Reproducing

```
cd swisstable-verus/analysis/extract-c-static
./codesight-edges.py > codesight-edges.txt   # the codesight side, read from #26's artefacts
./classify-not-found.py                      # which not-found symbols exist at the pinned tag
./run-probes.sh                              # 24-shape ligature probe matrix
./run-subset-port.sh                         # extract-c-static over subset-port/
./compare.py > comparison-report.txt         # the three-way table
```

All three shell scripts work on `rsync` copies under `/tmp/opencode/`, so no
pipeline stage writes inside the pilot. `results/`, `subset-port-result.json`
and `comparison-report.txt` are the recorded outputs.

## Axis 1: codesight-mcp vs the pinned C++

`upstream/abseil-cpp` at `2065f4ded0558c6f89fee67c8e5228feb4eb960e`, tag
`20260817.0`. Ground truth is `edge-truth.tsv`: 63 edges, every one cited.

| | true edges recovered | `Symbol not found` | never probed |
|---|---|---|---|
| open addressing | 2 / 6 | 2 | 2 |
| group probing | 13 / 17 | 0 | 4 |
| tombstones | 6 / 19 | 2 | 11 |
| rehash | 4 / 9 | 0 | 5 |
| iteration | 3 / 12 | 1 | 8 |
| **total** | **28 / 63** | **5** | **30** |

"Never probed" is the quiet failure: no recorded artefact asks about those 30
edges, so there is neither an error nor a zero-count answer to tell them apart
from "no such relationship". The rehash hub
`DropDeletesWithoutResizeAndPrepareInsert` (`raw_hash_set.cc:593`) is not
resolvable at all, which silences the six edges through it.

Three recorded edges are hand-verified **false** (`comparison-report.txt`, and
`swisstable-mcp-014`):

| codesight-mcp says | pinned source says |
|---|---|
| `assert_is_full -> btree.h::generation` (L1094) | `raw_hash_set.h:2445` calls `AssertIsFull` (h:1586); `generation()` is an *argument*, evaluated at the call site |
| `find_first_non_full -> cord_rep_btree.h::index` (L300) | `raw_hash_set.cc:207-210` calls `find_first_non_full_from_h1`, `H1`, `capacity_impl`; nothing named `index` |
| `Incr -> next` (`chunked_queue.h` L148) | `chunked_queue::Incr` does not call `probe_seq::next` |

The second is new; #26 recorded the other two. All three are exit 0 with no
warning, and the false peer sits in the same list as correct ones, so exit code
does not separate them.

### A correction to #26

A `Symbol not found` at exit 1 is only evidence of a tree-sitter gap if the
symbol exists in the pinned source. At `2065f4de` (tag `20260817.0`) much of
what #26 probed is gone: the LTS branch renamed the resize layer
(`GrowToNextCapacity` cc:1615, `DropDeletesWithoutResizeAndPrepareInsert`
cc:593), the erase layer (`erase_meta_only` h:3482) and the SIMD group API
(`Match` hcb:291, with no `MatchFull`/`MatchEmptyOrDeleted`).

`classify-not-found.py` derives the split over all 48 `Symbol not found`
artefacts, which ask for **32 distinct symbols**:

```
$ ./classify-not-found.py
48 `Symbol not found` artefacts, 32 distinct symbols
  absent         13 symbols (19 artefacts)
  out-of-subset   1 symbols ( 2 artefacts)
  present-weak    1 symbols ( 1 artefacts)
  present        17 symbols (26 artefacts)
```

| bucket | symbols | meaning |
|---|---|---|
| `not-found-absent.tsv` | 13 | zero `git grep -F` hits under `absl/` -- codesight is **correct** |
| `not-found-out-of-subset.tsv` | 1 | whole-word hit only outside the subset (`Resize` -> `inlined_vector.h:621`) |
| `not-found-present-weak.tsv` | 1 | substring only, in a Bazel target name (`resize_impl`) |
| `not-found-present.tsv` | 17 | whole-word **definition** in a subset file -- real index gaps |

Per area, real gaps vs total not-found: erase **4/8**, group probing **8/16**,
tombstones **4/6**, iteration **1/1**, rehash **9/17**. So #26's rehash "17
gaps" is 9 real gaps plus 5 absent and 3 borderline names
(`swisstable-mcp-018`).

Bare substring matching would have got this wrong in both directions, which is
why the script scopes to the five subset files and uses `git grep -w`:
`grep -F Resize` matches `inlined_vector.h:621` and `grep -F Match` matches
`log_severity_test.cc:86`. The `hit_kind` column is a stated heuristic, and
each `present` row lists every kind found with its hit count so the evidence
line can be checked rather than trusted.

The superseding hand-written `absent-in-source.tsv` was **deleted**: its header
claimed to list absent symbols while most of its rows said "PRESENT ... Real
index gap", which contradicted the derived tables. The four `not-found-*.tsv`
tables replace it and are regenerated by the script.

## Axis 2: ligature extract-c-static over the transcription

`43 discovered, 25 resolved, 18 unresolved`; `unattributed_call_sites 45`,
`out_of_scope_call_sites 16`, exit 0. Against the 63 true edges: **13
resolved, 12 recorded as unresolved, 35 not recorded at all, 3 with no fixture
row.**

The blind spot is the *shape* of the call, and it is derived, not asserted:

```
ligature verdict vs the shape of the call (free function on either side?):
  resolved        13 edges,   0 touch a free function,  13 do not
  unresolved      12 edges,   2 touch a free function,  10 do not
  not recorded    35 edges,  35 touch a free function,   0 do not
```

`probes/` isolates each cause in its own single-file crate:

| probe | isolates | result |
|---|---|---|
| 01 | `self.m()` baseline | resolved |
| 02 | `T::m(self)` / `Self::m(self)` | both resolved |
| 03 | `let me = T; me.leaf()` | `possible-dispatch`, callee dropped |
| 04 | callee defined nowhere in the crate | **0 discovered, 0 resolved, 0 unresolved, exit 0** |
| 05 | whole impl inside `verus!{}` | resolved (`macro_invocations: 1`) |
| 06 | free functions | 0 callsites; 2 dropped calls counted only in `unattributed` |
| 07 | trait method default body | 0 callsites; 1 in `unattributed` |
| 08 | trait-impl method body | resolved |
| 09 | local type from another module, via binding | `possible-dispatch` |
| 10 | `core::cmp::min` plus `self.m()` | external call `out_of_scope`, `self.m()` resolved |
| 11 | `T::new().leaf()` | `T::new` resolved, `.leaf()` on the result dropped |
| 12 | call inside a closure | body call resolved, `f(0)` `unresolved-indirect-call` |
| 13 | self-recursion | resolved |
| 14 | `self.is_deleted(hash)` inside `verus!{}` | resolved |
| 15 | `impl<T: Policy>` over a policy type | both `self.` calls resolved; `self.policy.key()` out of scope |
| 16 | `proof fn` chains inside `verus!{}` | all 3 resolved |
| 17 | isolate the `unattributed` counter | 1 call, `unattributed 0` |
| 18 | `open spec fn` / `broadcast proof fn` | 1 resolved, `unattributed 2` |
| 19 | **no calls at all** | `0/0/0` and still `unattributed_call_sites: 2` |
| 20 | minimal macro body, no spec/proof fn | all counters 0 |
| 21 | spec fn + proof fn, no calls | all counters 0 |
| 22 | field reads only, no calls | all counters 0 |
| 23 | `ensures (c as int < 256)` | `unattributed_call_sites: 1` |
| 24 | `ensures (forall\|c: u8\| true)` | `unattributed_call_sites: 1` |

Good news for a Verus pilot: `verus!{}` macro bodies **are** scanned, and
`proof fn` / `spec fn` / `broadcast proof fn` chains resolve.

Bad news for this subset: abseil writes the hot path as calls on non-`self`
receivers -- `seq.next()`, `g.MaskEmptyOrDeleted()`, `policy.hash_fn()` at
`raw_hash_set.cc:184`, `hashtable_control_bytes.h:318` and
`raw_hash_set.cc:623` -- and probe 03/09/12 plus probe 04 say exactly that
those become `possible-dispatch` with the callee dropped, or vanish entirely
with no record at all (`swisstable-mcp-016`).

`unattributed_call_sites` is not auditable: probe 19 has zero calls and still
reports 2, while probes 23 and 24 show a spec-clause expression each
contributing 1, and probes 06/07 show dropped calls landing in the same
counter. Two populations, one number, no per-site record
(`swisstable-mcp-017`).

## What the two axes disagree about

| question | codesight-mcp | extract-c-static |
|---|---|---|
| language covered | C++ (`upstream/abseil-cpp`) | Rust only, by its own `coverage_scope` |
| `seq.next()` on a non-`self` receiver | resolves it (bare `.h` name) | drops the callee, records `possible-dispatch` |
| a symbol that is absent | exit 1, `Symbol not found` | probe 04: 0/0/0, exit 0, no record |
| free functions | resolves them (the C++ subset is mostly free functions) | 0 callsites; only an unattributed counter moves |
| false edges | 3 verified, mixed into correct lists | none observed in the 25 resolved |

Neither tool is a substitute for reading the source: codesight-mcp under-reports
by 35 edges and adds 3 that are not there, and `extract-c-static` is blind to
the call shape this subset is written in. For the port, the C++ side must come
from the pinned source and the C_static report must be read with
`probes/`-level scepticism.

## Findings

7 lines appended to `swisstable-verus/findings/limitations.jsonl` by
`write-findings.py`, all `tool: "mcp"` per the task:

| id | severity | one line |
|---|---|---|
| `swisstable-mcp-013` | scope-cut | 28 of 63 true C++ edges recovered; 30 never probed |
| `swisstable-mcp-014` | blocker | third verified false edge: `cord_rep_btree.h::index` |
| `swisstable-mcp-015` | scope-cut | the two tools cover disjoint languages -- no combined number exists |
| `swisstable-mcp-016` | scope-cut | all 35 unrecorded edges touch a free function; non-`self` receivers drop the callee |
| `swisstable-mcp-017` | friction | `unattributed_call_sites` cannot be reconciled with the callsite list |
| `swisstable-mcp-018` | friction | 13 of 32 requested symbols are absent at the pinned tag, so #26 read some correct negatives as index gaps |
| `swisstable-mcp-019` | friction | `check` recommends `refresh-c-static` before the crate exists |

`swisstable-ligature-001` (#26, epic #1 #107) is now historical: the crash was
the missing descriptor, #27 supplied it, and `extract-c-static` runs. It is
left in place rather than rewritten.

## Scope

Nothing outside `swisstable-verus/` was written. No pipeline stage was run
beyond `check`, which is read-only; `project-descriptor.json` was not touched;
`ci/results/` inside the pilot was not written (every `extract-c-static` run
happened on an `rsync` copy under `/tmp/opencode/`). The pinned upstream
checkout was not modified. `flake.nix` and `flake.lock` at the workspace root
were not touched (md5 identical before and after). No escalation was filed:
the ligature behaviours found here are all graceful messages, not crashes.
