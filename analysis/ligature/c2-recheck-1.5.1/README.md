# C.2 re-check: `_`-prefixed directory scan convention drift (chainlink #56)

Date: 2026-11-17
Owning root: `date-creusot/` (the C-series pilot; the issue itself is
workspace-wide)
Upstream report: **epic #1 #198**
Findings: `date-creusot-070` (scan/mislocation drift), `date-creusot-071`
(`draft` template/destination mismatch)
Binary: `date-creusot/tools/ligature/ligature.pyz`
Bundle SHA-256: `d704c5a5875d200214310c1fca7854a14a105c1b74cebaa5bc03f6a870bcc030`
Version: `ligature 1.5.1`; content hash
`sha256:def6b87957ff4e26737e18a469a7df447fdadb5df3eac5180db881c42baccfcb`

## Result

**STILL PRESENT under Ligature 1.5.1, as a friction-level convention drift.**
It is no longer a silent "the tool does not scan `_` directories" problem:
the canonical layout works, and `_`-prefixed misplacements are now reported.
The drift is that the convention is enforced inconsistently:

1. Only `_`-prefixed locations are candidate-scanned for concept specs, and
   the diagnostic says the file is *outside* `specs_search_root` when it is
   physically inside it. The same spec moved to a plain nested directory
   (`specs/nested/`) produces no concept-spec diagnostic at all.
2. A known artifact directory (`_boundaries/`, `_interactions/`, ...) decides
   the artifact kind, so a concept JSON there is validated as that kind and
   fails on unrelated schema fields. A boundary/interaction JSON moved flat
   under `specs/` is silently ignored. Nesting *inside* a known `_kind` dir
   is caught by G1b, so the rule is enforced in one direction only.
3. `draft` accepts any known artifact directory for any template and then
   validates the rendered JSON against the **destination** kind. The caller
   gets schema errors from the wrong kind instead of a
   template/destination mismatch error.
4. Any `.json` in `specs/_closure` is ingested by `status` as a closure
   profile. An invalid stray produces a second cluster row with
   `closure_kind: "unknown"` and `state: "closes"`, while `validate-closure`
   and `gate-g14` both reject the same file (the #102 status/gate
   disagreement family, still present for this scan).

The bundled convention these cases are measured against is in the binary's
own `ligature contract` §4 table and in
`.ligature/prompts/stage-3-concept-to-code.md`: concept specs are **flat**
under `<crate_dir>/specs/<snake_case(concept)>.json`, and every other kind
lives in its own `_kind/` directory. The same contract's "Concept-spec
search roots (#149)" says a "mislocated concept spec is reported with the
exact root and a repair step".

## Reproduction

[`repro.sh`](repro.sh) copies the pilot with `rsync` into a throwaway root
under `/tmp/opencode`, mutates only that copy, and records every command's
stdout/stderr under [`raw/`](raw/). No live pilot or pilot `specs/_closure`
is written.

```text
$ bash date-creusot/analysis/ligature/c2-recheck-1.5.1/repro.sh
```

Baseline (real pilot, 1.5.1):

```text
$ python3 tools/ligature/ligature.pyz validate ; echo $?
OK: all boundary contracts pass G1a/G1b/G2+ (9 discovered)
0
$ python3 tools/ligature/ligature.pyz status
artifacts (38): promoted=34, validated=4
cluster date-creusot-core: closes (closure_kind=deductive)
$ python3 tools/ligature/ligature.pyz check --json ; echo $?
1        # the two pre-existing out-of-set write-set findings: .gitignore, PORT-GAPS.md
```

### 1. `_concepts/` is scanned; `nested/` is invisible

```text
$ mv rust/date-creusot-core/specs/weekday.json rust/date-creusot-core/specs/_concepts/weekday.json
$ python3 tools/ligature/ligature.pyz validate ; echo $?
FAIL: 4 finding(s)
  - [G2+/error] .../specs/_boundaries/...: 'Weekday.C001': applies_to unverifiable --
    concept spec candidate(s) for 'Weekday' are outside declared specs_search_root
    '<scratch>/rust': <scratch>/rust/date-creusot-core/specs/_concepts/weekday.json;
    move the canonical concept spec under the declared root or update
    crates[].specs_search_root. The outside candidate is not used as a fallback
1
```

The named candidate is `.../rust/date-creusot-core/specs/_concepts/weekday.json`,
i.e. directly inside the declared root `.../rust`. What it is outside of is
the *flat* concept directory `<crate_dir>/specs/`.

The same move into `specs/nested/` is silent:

```text
$ mv rust/date-creusot-core/specs/weekday.json rust/date-creusot-core/specs/nested/weekday.json
$ python3 tools/ligature/ligature.pyz validate ; echo $?
OK: all boundary contracts pass G1a/G1b/G2+ (9 discovered)
0
$ python3 tools/ligature/ligature.pyz status | grep -c 'G2+'
0
```

`status` reports `cluster date-creusot-core: blocked` and one indirect `g14`
finding naming the promotion receipt's pinned old path
(`artifact_manifest path 'rust/date-creusot-core/specs/weekday.json' does not
exist`); no finding names the new `specs/nested/weekday.json` as a
mislocated concept candidate. Raw outputs:
[`raw/concept-in-underscore-*`](raw/) and
[`raw/concept-in-plain-subdir-*`](raw/).

Cross-pilot control on `crypto-mixed` reproduces the `_concepts` message at
the other declared root:

```text
$ mv crates/crypto-mixed-core/specs/cha_cha20.json crates/crypto-mixed-core/specs/_concepts/cha_cha20.json
$ python3 tools/ligature/ligature.pyz validate ; echo $?
FAIL: 7 finding(s)
  - [G2+/error] ...: 'ChaCha20.C004': applies_to unverifiable -- concept spec
    candidate(s) for 'ChaCha20' are outside declared specs_search_root
    '<scratch>/crates': <scratch>/crates/crypto-mixed-core/specs/_concepts/cha_cha20.json ...
1
```

### 2. A known `_kind` directory overrides the payload kind

```text
$ cp .../specs/weekday.json .../specs/_boundaries/probe_concept.json
$ python3 tools/ligature/ligature.pyz status --json | ...
{"artifact_id":"probe_concept","kind":"boundary","lifecycle":"invalid",
 "path":"rust/date-creusot-core/specs/_boundaries/probe_concept.json"}
$ python3 tools/ligature/ligature.pyz validate ; echo $?
FAIL: 5 finding(s)
  - [G1a/error] .../specs/_boundaries/probe_concept.json: 'boundary_id' is a required property
  - [G1a/error] ...: 'caller' is a required property
  - [G1a/error] ...: 'callee' is a required property
  - [G1a/error] ...: 'callee_guarantees' is a required property
  - [G1a/error] ...: Additional properties are not allowed
    ('adversary_table','cluster','commands','concept','constraints',
     'english_description','kind','queries','source_references','verifier' were unexpected)
1
```

The inverse placement is silent: a boundary or interaction JSON copied flat
under `specs/` leaves `status` at 38 artifacts, `validate` at "9 discovered",
and `check` at its baseline. Nesting *inside* a known directory is caught:

```text
$ .../specs/_boundaries/nested/probe_boundary_nested.json
[G1b/error] ...: not flat -- must live directly inside a _boundaries/ directory
[G1b/error] ...: filename stem ... does not match ...
```

crypto-mixed reproduces the kind override (`_boundaries/cha_cha20.json` ->
`kind: boundary, lifecycle: invalid`, `validate` exit 1 on `boundary_id`).

### 3. `draft` accepts any known artifact directory for any template

The target check runs before the template's variables, so the first error
line is a reliable discriminator: "undefined variable" means the target was
accepted; the target-refusal message means it was not.

| template | target | target check | after a full render |
|---|---|---|---|
| `concept-to-code` | `specs/probe_concept.json` | accepted | concept-kind validation |
| `concept-to-code` | `specs/_boundaries/probe_concept.json` | **accepted** | **5 boundary-schema errors** |
| `concept-to-code` | `specs/_interactions/probe_concept.json` | **accepted** | interaction-kind validation |
| `concept-to-code` | `specs/_concepts/probe_concept.json` | refused: "not a supported pipeline artifact destination" | — |
| `boundary-drafting` | `specs/_boundaries/probe_boundary.json` | accepted | boundary-kind validation |
| `boundary-drafting` | `specs/probe_boundary_flat.json` | **accepted** | **9 concept-schema errors** |
| `boundary-drafting` | `specs/_interactions/probe_boundary.json` | **accepted** | interaction-kind validation |
| `boundary-drafting` | `specs/_bridges/probe_boundary.json` | **accepted** | bridge-kind validation |

Exact full-render results:

```text
$ ligature draft 3 concept-to-code rust/date-creusot-core/specs/_boundaries/probe_concept.json --var ...
FAIL: generated draft has 5 immediate validation finding(s) -- fix before approve()
  - [G1a/error] .../_boundaries/probe_concept.json: 'boundary_id' is a required property
  ...
$ ligature draft 3 boundary-drafting rust/date-creusot-core/specs/probe_boundary_flat.json --var ...
FAIL: generated draft has 9 immediate validation finding(s) -- fix before approve()
  - [G1a/error] .../specs/probe_boundary_flat.json: 'concept' is a required property
  - [G1a/error] ...: 'cluster' is a required property
  ...
```

Raw transcript: [`raw/draft-concept-into-boundaries.out`](raw/draft-concept-into-boundaries.out),
[`raw/draft-boundary-flat.out`](raw/draft-boundary-flat.out), and the
target-only rows in the run log.

### 4. `status` closes a cluster that the closure validators reject

```text
$ cp .../specs/weekday.json specs/_closure/probe_concept.json
$ python3 tools/ligature/ligature.pyz status
artifacts (39): invalid=1, promoted=34, validated=4
cluster date-creusot-core: closes (closure_kind=deductive)
cluster date-creusot-core: closes (closure_kind=unknown)
$ python3 tools/ligature/ligature.pyz status --json | jq '.clusters'
[{"closure_kind":"deductive","cluster":"date-creusot-core","state":"closes"},
 {"closure_kind":"unknown","cluster":"date-creusot-core","state":"closes"}]
$ python3 tools/ligature/ligature.pyz validate-closure ; echo $?
FAIL: 4 finding(s)
  - [G1a/error] specs/_closure/probe_concept.json: 'closure_kind' is a required property
  - [G1a/error] specs/_closure/probe_concept.json: 'work_packages' is a required property
  - [G1a/error] specs/_closure/probe_concept.json: 'conditions' is a required property
  - [G1a/error] specs/_closure/probe_concept.json: Additional properties are not allowed ...
1
$ python3 tools/ligature/ligature.pyz gate-g14 ; echo $?
  - [G14/error] specs/_closure/probe_concept.json: ignored as invalid and excluded from closure computation
FAIL: 1 cluster(s) blocked, 0 not blocked
1
```

The same probe on crypto-mixed yields a `crypto-kani` row with
`closure_kind: "unknown", state: "degraded"` beside the real
`bounded/degraded` row.

## Why this is a finding and not a clean pass

The canonical layout (flat concept specs; one `_kind` directory per other
artifact kind) works, so this is not a blocker on the normal path. It is
still a real convention drift: the same misplaced spec is reported in three
different ways depending only on the directory name, the diagnostic names
the wrong boundary (the file *is* under `specs_search_root`), `draft` can be
pointed at a target it cannot validate correctly, and `status` can print a
closing cluster for a file both closure gates reject. Upstream report:
**epic #1 #198**.

## Scope checks

- No Ligature source or `ligature.pyz` contents were inspected; only
  `--help`, `contract`, command output and files the tool names as its own
  inputs. Black-box rule respected.
- Every mutation was made in a copy under `/tmp/opencode`, outside the
  pilot trees. No `specs/_closure` file was created inside a pilot.
- No protected write, grant, approval, promotion or ruling was made.
- The live pilots were not mutated by the probes. The only new files in
  `date-creusot/` are this evidence directory and two appended
  `findings/limitations.jsonl` lines.
- Cross-pilot check used crypto-mixed `status`/`validate` only; its Kani
  evidence was not rerun.

Machine-readable summary: [`summary.json`](summary.json). Raw command
outputs: [`raw/`](raw/).
