# Probe #23 — Kani evidence inside a deductive cluster: what G17 does, and what a degradation record actually buys

Chainlink **#23** `[p1 probe] Kani evidence inside a deductive cluster -> G17 + degradation record behaviour`
· pilot root `date-creusot/` · attempt 1/20 · 2026-09-30.

Reproduce everything here with:

```
analysis/ligature/probe-23-legs.py                 # 29 legs A0/D0-D21/E2-E7
analysis/ligature/probe-23-release-evidence.py    # the release state + the record schema, field by field
```

with transcripts committed next to them. Both scripts operate on an `rsync` scratch
copy under `/tmp/opencode/p23/` and **reset it to a pristine snapshot before every
single leg**. The live root was never written to (verified: 751/751 files md5-identical
at the end of the session). No `draft` / `approve` / `promote-evidence` /
`record-assurance` / `record-ruling` / `accept-promotion` / `init` was ever invoked —
in particular the operator's standing "do not record-ruling anything" instruction was
honoured, and section 5 below is built entirely from `--help` and gate output.

Binary, verified first per WORKER-CONTRACT §1:

```
$ cd date-creusot/tools/ligature && sha256sum -c SHA256SUMS
ligature.pyz: OK
$ python3 tools/ligature/ligature.pyz version
ligature 1.1.1
  content hash: sha256:172a87a8be8406d625b57b1aa96dc8cb76756e615983d8da70aa298892964558
```

sha256 `3edfd03cd4e6dee30139c48e7921abcf338cb279ff2eb4e4d0bba9a44725deb4`.

---

## The answer, in four sentences

**Kani evidence inside a cluster declared `deductive` can never be released under a
degradation record.** A schema-valid record downgrades the CG3 finding from
`[G14/error]` to `[G14/degraded]` and nothing else; G17's two recompute findings
(`closure_kind`, `conditions.owning_verifier`) survive it untouched and keep the
cluster `BLOCKED` at exit 1. **The release exists, but it is not a deductive release:**
you must first re-declare the profile `closure_kind: "bounded"` /
`conditions.owning_verifier: "kani"` — i.e. accept a strictly weaker claim — and only
then does `gate-g14` exit 0 and print `does NOT close: degraded under an accepted
degradation record` / `1 released under an accepted degradation record`. **The record's
authoring path is hand-writing one file**, `specs/_closure/<cluster>.degradation.json`
— there is still no `draft`/`approve` template for it — and `validate-closure` is the
validator, which is new in 1.1.1 and largely retires `date-ligature-040`. **And
"accepted" means only schema-valid:** no `review` block, `affected_edges`, `ceiling` or
`tracking_issue` in that record is ever resolved against anything, which is the one
finding here that is a real escalation.

---

## 1. The authoring path for a degradation record

There is **no authoring path in the tool** — none of the nine `draft` templates in
`.ligature/prompts/` covers a closure profile or a degradation record, and no
`approve`/`promote-*` verb does either. The record is therefore **hand-written**, which
`write_set` permits: `specs/_closure/**` is in `allowed_roots` and not in
`protected_roots`. Discovery is by filename under the canonical closure directory —
`gate-g14` prints the absolute path of anything it reads, and probing ten candidate
paths shows only `specs/_closure/**` is scanned:

| candidate path | read? |
|---|---|
| `specs/_closure/<cluster>.degradation.json` | **yes** — degradation-record schema |
| `specs/_closure/<anything-else>.json` | yes — but validated against the *closure-profile* schema (legs D13, D14) |
| `specs/_closure/sub/dir/<cluster>.json` | yes, then rejected: `[G1b/error] closure artifact is not directly under the canonical directory` |
| `specs/_degradation/`, `specs/_degradations/`, `ci/degradation/`, `docs/degradation/`, `degradations/` | **no** — silently ignored |

The only accepted filename is exactly `<cluster>.degradation.json`; `G1b` binds the
record's own `cluster` field to the filename stem:

```
$ python3 tools/ligature/ligature.pyz validate-closure                    # cluster: "date-creusot-core-core"
- [G1b/error] specs/_closure/date-creusot-core.degradation.json: degradation record declares cluster 'date-creusot-core-core', but its filename says 'date-creusot-core'
```

### The required fields, and every constraint, each one a real error message

`validate-closure` validates the record against a bundled schema the pilot root does
**not** ship (`docs/degradation-record-schema.json`, named in
`tools/ligature/PROVENANCE.json` and referenced from
`.ligature/schemas/project-state.schema.json`, absent from `docs/`). Every row below is
a real message from `validate-closure`, exit 1:

| field | required | constraint | the error that proves it |
|---|---|---|---|
| `schema_version` | yes | string | `'schema_version' is a required property` |
| `cluster` | yes | must equal the filename stem | `G1b`: `degradation record declares cluster 'x', but its filename says 'y'` |
| `failed_conditions` | yes | array, **minItems 1**, items from a **closed 7-value enum** | `[] is too short`; `'not_a_condition' is not one of ['single_verifier_system', 'owning_verifier', 'protocol_class_all_pairwise', 'unresolved_indirect_calls_at_or_above_medium', 'generic_callees_type_universal_or_creusot_owned', 'transitive_assumptions_within_policy', 'scc_wellfoundedness_discharged']` |
| `affected_edges` | yes | array of strings, **minItems 1** | `'[] is too short'`; `1 is not of type 'string'` |
| `ceiling` | yes | enum `['documented','tested','harness-tested','assumed','per-instantiation','human-risk-acceptance']` | `'none' is not one of [...]` |
| `tracking_issue` | yes | string matching **`^[a-z]+:[A-Za-z0-9_.-]+$`** — shape only | `'plain text' does not match '^[a-z]+:[A-Za-z0-9_.-]+$'` |
| `review` | yes | `{reviewer: non-empty string, reviewed_at: YYYY-MM-DD}` | `'' is too short`; `'yesterday' is not a 'date'` |
| — | — | `additionalProperties: false` | `Additional properties are not allowed ('surprise' was unexpected)` |

The working record, verbatim:

```json
{
  "schema_version": "1.0",
  "cluster": "date-creusot-core",
  "failed_conditions": ["generic_callees_type_universal_or_creusot_owned"],
  "affected_edges": ["date::year_month_day::to_days"],
  "ceiling": "per-instantiation",
  "tracking_issue": "chainlink:23",
  "review": {"reviewer": "chainlink-worker", "reviewed_at": "2026-09-30"}
}
```

> **`date-ligature-040` is now partly obsolete.** It recorded that "the degradation-record
> schema has no authoring path … the schemas are only discoverable by iterative probing of
> `validate-closure` error messages". Under 1.1.1 the record is a first-class,
> fully-validated artifact of `validate-closure` (G1a schema + G1b filename binding + G17
> profile/record agreement, both directions), and the exact schema is recoverable from
> those error messages in one pass. What is still true is the authoring half: no
> `draft`/`approve` covers it, so it must be hand-written.

---

## 2. Kani evidence inside a cluster declared `deductive` (the issue's own case)

Building block `kani_evidence()`: the work package's `accepted_evidence_kinds` becomes
`["kani-bounded-model-check"]` and all five achieved records carry
`evidence.kind = "kani-bounded-model-check"` — a genuinely Kani-owned closure, with no
"impossible" schema errors anywhere.

**Leg D0 — no degradation record.** `gate-g14` exit 1:

```
cluster 'date-creusot-core' is BLOCKED: closure not established
  - [G17/error] date-creusot-core: conditions.owning_verifier is declared as 'creusot' but the computed closure says 'kani' -- conditions are recomputed, never stored-and-trusted
  - [G17/error] date-creusot-core: closure_kind is 'deductive' but the transitive closure contains ['kani-bounded-model-check'] -- a bounded result anywhere in the closure makes the cluster's guarantee bounded (plan.md §4)
  - [G14/error] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: ... releasing this cluster needs a degradation record naming this condition with a tracking issue
FAIL: 1 cluster(s) blocked, 0 not blocked
EXIT=1
```

Note `validate-closure` exits **0** here: G17's profile/record consistency check sees a
profile that declares nothing as not-holding, so it has nothing to object to. Only
`gate-g14` blocks. (`date-ligature-039`'s description already called this pair out.)

**Leg D1 — add the schema-valid CG3 record.** The record is honoured; it changes the
CG3 line and *only* the CG3 line:

```
  - [G17/error] date-creusot-core: conditions.owning_verifier is declared as 'creusot' but the computed closure says 'kani' -- conditions are recomputed, never stored-and-trusted
  - [G17/error] date-creusot-core: closure_kind is 'deductive' but the transitive closure contains ['kani-bounded-model-check'] -- a bounded result anywhere in the closure makes the cluster's guarantee bounded (plan.md §4)
  - [G14/degraded] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: ... releasing this cluster needs a degradation record naming this condition with a tracking issue -- accepted as degradation under ceiling 'per-instantiation' (chainlink:23)
FAIL: 1 cluster(s) blocked, 0 not blocked
EXIT=1
```

`G14/error` → `G14/degraded`; the cluster stays `BLOCKED`. **A degradation record can
never excuse a `G17/error`**, which is the structural reason the issue's premise fails:
a record names a *condition*, and G17 does not raise findings about conditions — it
raises findings about a *declaration that contradicts the recomputation*.

Legs **E2** and **D21** generalise this away from Kani: `unresolved_indirect_calls_at_or_above_medium: 3`
with a fully valid matching record, and `single_verifier_system: false` with a fully
valid matching record, are both still `BLOCKED` with the recompute error intact.

---

## 3. The release route, and exactly how G14 reports it

**Leg D2** — Kani evidence, the profile corrected to what the artifacts actually say
(`closure_kind: "bounded"`, `conditions.owning_verifier: "kani"`), plus the record:

```
$ python3 tools/ligature/ligature.pyz validate-closure   ; echo "EXIT=$?"
OK: all closure artifacts pass G1a/G1b and G17 profile/record consistency (2 discovered)
EXIT=0

$ python3 tools/ligature/ligature.pyz gate-g14            ; echo "EXIT=$?"
cluster 'date-creusot-core' does NOT close: degraded under an accepted degradation record (declared closure_kind=bounded)
  - [G14/degraded] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: ... -- accepted as degradation under ceiling 'per-instantiation' (chainlink:23)
closure is a per-cluster property with a kind; this gate never asserts a pipeline-wide guarantee (plan.md §4)
OK: 0 cluster(s) close under their declared profile, 1 released under an accepted degradation record
EXIT=0

$ python3 tools/ligature/ligature.pyz status | grep 'cluster date-creusot-core'
cluster date-creusot-core: degraded (closure_kind=bounded) limitations=['generic_callees_type_universal_or_creusot_owned']

$ python3 tools/ligature/ligature.pyz gate g14            ; echo "EXIT=$?"     # the umbrella verb agrees
OK: 0 cluster(s) close under their declared profile, 1 released under an accepted degradation record
EXIT=0
```

Deterministic across three consecutive runs. The three report shapes, verbatim:

- **per-cluster line:** `does NOT close: degraded under an accepted degradation record (declared closure_kind=bounded)`
- **summary line:** `OK: 0 cluster(s) close under their declared profile, 1 released under an accepted degradation record`
- **`status`:** `state: degraded`, `limitations: [generic_callees_type_universal_or_creusot_owned]`

`status --json` carries it as `"clusters": [{"closure_kind": "bounded", "state":
"degraded", "limitations": [...], "cluster": "date-creusot-core"}]` — schema-valid
against `.ligature/schemas/project-state.schema.json`.

`check --json` treats the release as clean. The `result` block is byte-identical to the
baseline (`{"conditions": ["blocking_findings", "human_decision_required"],
"exit_code": 1}` — the pre-existing 5 high `r1-g16` findings and 5 pending human
decisions, nothing new), and the CG3 finding is carried at severity `medium` rather
than the baseline's `info`:

```
{"authority": "mechanized-gate", "dedup_key": "c0bfd6a5...", "gate_id": "g14",
 "provenance": "scripts/gate_g14.py:gate_workspace", "severity": "medium",
 "subject": "date-creusot-core", "reason": "[generic_callees_...] ... accepted as degradation under ceiling 'per-instantiation' (chainlink:23)"}
```

**Control (leg D3)** — the same corrected profile with **no** record: `gate-g14` exit 1,
`is BLOCKED`, the CG3 error unexcused. So the record is load-bearing for the release,
not decorative.

### The cost of the release, stated plainly

The release is **not** "a deductive cluster, released with a documented degradation".
It is "a **bounded** cluster, released under a recorded degradation". The operator has
to change the top-level `closure_kind` from `deductive` to `bounded` and
`conditions.owning_verifier` from `creusot` to `kani` to get there. Nothing in the
tool's output says so: the CG3 message's own remedy — *"releasing this cluster needs a
degradation record naming this condition with a tracking issue"* — is **insufficient on
its own** (leg D1) and silent about the re-declaration that is actually required.

---

## 4. What a record can and cannot excuse — full table

29 legs, all on pristine resets. `released` = `gate-g14` exit 0 with
`released under an accepted degradation record`.

| leg | state | `validate-closure` | `gate-g14` | `status` |
|---|---|---|---|---|
| A0 | live Creusot state, no record | 0 | 0, CG3 `VERIFIED` | `closes` |
| D0 | Kani-in-`deductive`, no record | **0** | 1, BLOCKED (G17×2 + CG3 err) | `blocked` |
| D1 | + CG3 record, still `deductive` | 0 | 1, BLOCKED (G17×2 + CG3 **degraded**) | `blocked` |
| **D2** | **Kani + `bounded`/`kani` + CG3 record** | **0** | **0, released** | **`degraded`** |
| D3 | control: Kani + `bounded`, **no** record | 0 | 1, BLOCKED (CG3 err) | `blocked` |
| D4 | record names `transitive_assumptions_within_policy` instead | **1**, stale excuse | 1, BLOCKED | `blocked` |
| D5 | `failed_conditions: []` | 1, `[] is too short` | 1, record ignored, BLOCKED | `blocked` |
| D6 | `failed_conditions: ["no_such_condition"]` | 1, not in the enum | 1, record ignored, BLOCKED | `blocked` |
| D7 | `tracking_issue: ""` | 1, regex | 1, record ignored, BLOCKED | `blocked` |
| D8 | `cluster: "some-other-cluster"` | 1, G1b filename binding | 1, record ignored, BLOCKED | `blocked` |
| D9 | `ceiling: "human-risk-acceptance"` | 0 | 0, **released** | `degraded` |
| D10 | `ceiling: "documented"` | 0 | 0, **released** | `degraded` |
| D11 | `affected_edges` are invented strings | 0 | 0, **released** | `degraded` |
| D12 | two records for one cluster | 1, G1b on the second | 0 for the cluster, **exit 1** | `degraded` |
| D13 | record content at `degradation-<cluster>.json` | 1, 4 findings (profile schema) | 1, BLOCKED | **two `cluster` rows**, one `closure_kind=unknown` |
| D14 | record content at `zzz.json` | 1, 4 findings | 1, BLOCKED | **two `cluster` rows** |
| D15 | CG3 record on the healthy Creusot cluster | 0 | 1, stale tracking record | `blocked` |
| D16 | count mismatch + schema-INVALID record | 1, 8 findings | 1, BLOCKED | `blocked`, `limitations=['n','o','t',…]` |
| D17 | control: same mismatch, **no** record | 1 | 1, BLOCKED | `blocked` |
| D18 | schema-INVALID record on the healthy cluster | 1, 7 findings | 1 (record ignored) | `closes`, `limitations=['n','o',…]` |
| D19 | Kani-in-`deductive` + INVALID record | 1, 7 findings | 1, BLOCKED | `blocked`, `limitations=['n','o',…]` |
| D20 | Kani-in-`bounded` + INVALID record | 1, 7 findings | 1, BLOCKED | `blocked`, `limitations=['n','o',…]` |
| D21 | bool condition `false` + matching record | 0 | 1, BLOCKED (recompute) | `blocked` |
| E2 | count mismatch + **fully valid** matching record | 0 | 1, BLOCKED (recompute) | `blocked` |
| E3 | mismatch + record invalid in one field | 1 | 1, BLOCKED (recompute intact) | `blocked`, `limitations=['x']` |
| E4 | mismatch + one unexpected key | 1 | 1, BLOCKED | `blocked` |
| E5 | mismatch + record with no `cluster` | 1, 7 findings | 1, BLOCKED | `blocked`, `limitations=['x']` |
| E6 | `tracking_issue: "chainlink:999999"` | 0 | 0, **released** | `degraded` |
| E7 | `reviewer: ""`, `reviewed_at: "yesterday"` | 1, 3 findings | 1, record ignored, BLOCKED | `blocked` |

Two further legs outside the table, both **BLOCKED**, both showing that *any* Kani
evidence in the closure trips the same two unexcusable G17 findings:

- **Kani only in `bridge_records`** (cluster still `deductive`, record present): G17
  `closure_kind`, G17 `single_verifier_system`, CG1 `[G14/error]`, CG3
  `[G14/degraded]`. Exit 1.
- Same, with the record also naming `single_verifier_system`: CG1 is downgraded to
  `[G14/degraded]` — and `validate-closure` simultaneously exits 1 calling the *same
  record* a stale excuse (see §5).

### The rule, as measured

**A record excuses exactly one class of finding: a `[G14/…]` finding *keyed by a
condition name* whose condition the closure profile declares as holding.** It never
excuses a `G17/error` (a declaration that contradicts the recomputation) and never
excuses a `G14/error` about an obligation's provided guarantee.

### What the record's own fields are worth

| field | enforced? |
|---|---|
| `cluster`, `schema_version`, `failed_conditions`, `review`'s *shape* | yes, hard |
| `failed_conditions` ↔ profile agreement | yes, **both directions** (D4 stale excuse, D15 stale tracking record) |
| `ceiling` | **enum only.** `documented` — "we wrote it down" — releases the cluster identically to `human-risk-acceptance`. No check that the ceiling is adequate for the condition, and the ceiling appears in no machine-readable output except the human-readable finding text. |
| `affected_edges` | **never resolved.** `["not-a-real-call-edge", "also-invented"]` releases the cluster (D11). No cross-reference to any interaction id, callsite id or function name exists. |
| `tracking_issue` | **regex only.** `chainlink:999999` releases the cluster (E6). Existence is never checked. |
| `review` | **free text.** `{"reviewer": "nobody-reviewed-this", "reviewed_at": "1999-01-01"}` releases the cluster (see below). Not cross-checked against `ci/results/review_log.jsonl` and not gated on `ci/results/human_rulings.jsonl`. |

---

## 5. Headline (§2) — new ligature escalation: **"accepted" is not acceptance

Leg G1 (`/tmp/opencode/p23/work6/`) is one record whose every unverifiable field is
deliberately false, on a cluster whose profile now genuinely matches its artifacts:

```json
{"schema_version": "1.0", "cluster": "date-creusot-core",
 "failed_conditions": ["generic_callees_type_universal_or_creusot_owned"],
 "affected_edges": ["invented-edge-that-does-not-exist"],
 "ceiling": "documented",
 "tracking_issue": "chainlink:999999",
 "review": {"reviewer": "nobody-reviewed-this", "reviewed_at": "1999-01-01"}}
```

```
$ python3 tools/ligature/ligature.pyz validate-closure   ; echo "EXIT=$?"
OK: all closure artifacts pass G1a/G1b and G17 profile/record consistency (2 discovered)
EXIT=0
$ python3 tools/ligature/ligature.pyz gate-g14            ; echo "EXIT=$?"
cluster 'date-creusot-core' does NOT close: degraded under an accepted degradation record (declared closure_kind=bounded)
  - [G14/degraded] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: ... -- accepted as degradation under ceiling 'documented' (chainlink:999999)
OK: 0 cluster(s) close under their declared profile, 1 released under an accepted degradation record
EXIT=0
```

A fabricated reviewer, an invented edge, a tracking issue that does not exist and the
weakest possible ceiling, and the cluster is released under a record the tool calls
**accepted**. That is materially weaker than the sibling mechanism one command away.
`accept-promotion`'s own help says it runs two guards before writing anything:

> "Two guards run before anything is written (chainlink #82): a review-provenance check
> (every accepted artifact's own `review` block must match an entry in the approval audit
> log `ci/results/review_log.jsonl`) and the human-ruling gate (every manifest entry must
> carry a `ratified` human ruling over that exact version in `ci/results/human_rulings.jsonl`)."

and `WORKER-CONTRACT.md` §0.0 records that correction as load-bearing: *"The
human-ruling checkpoints that older docs describe as social constraints are now
enforced."* **`gate-g14`'s release route has neither guard.** `ci/results/` on this
pilot contains no `human_rulings.jsonl` at all, and the release succeeds without one;
`record-ruling --help` describes its `--artifact` as *"the same paths
`accept-promotion` takes"*, i.e. the promotion artifact set — not closure artifacts.
(Per the operator's standing instruction I did **not** run `record-ruling`, so this is
established from `--help`, the file listing, and the exit-0 release itself.)

Filed as epic #1 **#101**. Needs a human read before anything is relayed to the ligature
owner.

### Second escalation — epic #1 **#102**: two commands disagree about the same record

**(a) `gate-g14` honours a record that `validate-closure` rejects.** A record naming
`single_verifier_system` (any CG condition other than CG3) on a profile that declares
it `true`:

```
$ python3 tools/ligature/ligature.pyz validate-closure   ; echo "EXIT=$?"
FAIL: 1 finding(s)
  - [G17/error] specs/_closure/date-creusot-core.degradation.json: failed_conditions names 'single_verifier_system', but cluster 'date-creusot-core''s closure profile declares that condition as holding -- a stale excuse keeps a closed gap reading as degraded
EXIT=1
$ python3 tools/ligature/ligature.pyz gate-g14            ; echo "EXIT=$?"
  - [G14/degraded] [single_verifier_system] date-creusot-core: the transitive closure spans more than one verifier system (['creusot-deductive-check', 'kani-bounded-model-check']) -- cross-verifier composition has no soundness theorem (CG1) -- accepted as degradation under ceiling 'per-instantiation' (chainlink:23)
```

Same file, same run, opposite admissibility. Only CG3 is exempt (chainlink #86's
documented exception), so the exempt set is one condition out of seven and is not
derivable from anything the tool states.

**(b) `status` ingests a record both gates refused.** Legs D16, D18, D19, D20, E3, E5 —
in every one of them `gate-g14` says of the file:

```
- [G14/error] /…/specs/_closure/date-creusot-core.degradation.json: ignored as invalid and excluded from closure computation -- run `pipeline.py validate-closure` for the detailed finding(s) that invalidated it
```

and `status` in the same state reads that file's `failed_conditions` into the
machine-readable project state anyway. When the field is a string (which is one of the
ways to make the record invalid) it is iterated **character by character**:

```
$ python3 tools/ligature/ligature.pyz status | grep 'cluster date-creusot-core'
cluster date-creusot-core: closes (closure_kind=deductive) limitations=['n', 'o', 't', '-', 'a', 'n', '-', 'a', 'r', 'r', 'a', 'y']
```

An artifact the gates refuse can put arbitrary text into `project-state`'s
`limitations`. No wrong release results — `gate-g14` still exits 1 on the invalid record
itself — so this is a reporting contradiction, not a soundness hole.

---

## 6. What held up

Worth crediting, because it is most of the mechanism:

- **The filename binding and the closed condition enum are real.** `failed_conditions`
  cannot be used to smuggle in a made-up condition name (D6), and `cluster` must match
  the filename (D8). Together they make the record's *identity* unforgeable-by-accident.
- **The record is refused when stale, in both directions.** `validate-closure` catches a
  record claiming a condition the profile declares as holding — *"a stale excuse keeps a
  closed gap reading as degraded"* (D4) — and `gate-g14` independently catches the CG3
  special case — *"a stale tracking record keeps a closed gap reading as degraded;
  remove it and shut the tracking issue (chainlink:23)"* (D15). That second message is
  the best in the whole mechanism: it tells the operator to **shut the tracking issue**,
  i.e. the record carries a lifecycle the tool enforces at one end.
- **G17 is genuinely fail-closed on recomputation.** A wrong `closure_kind`, a wrong
  `owning_verifier`, a wrong boolean and a wrong count are all caught with the same
  "conditions are recomputed, never stored-and-trusted" wording, and **no** degradation
  record excuses any of them (D1, E2, D21). That is the right behaviour and it is what
  makes the issue's premise false.
- **An invalid record is always fatal**, never silently ignored: `validate-closure` exit 1
  with the field-level reason, `gate-g14` exit 1 naming the file. The worst a malformed
  record does is produce an unreadable `status` line.

---

## 7. Findings logged — one entry, per `findings-schema.md`

`date-creusot-057` — *the degradation record is the only release route for a Kani-owned
closure, it is hand-authored, it can only ever excuse a condition-keyed G14 finding, and
the `review`/`ceiling`/`affected_edges`/`tracking_issue` it carries to justify the
release are all self-asserted* — severity **blocker**, tool `ligature`, chain `new`,
pyz `3edfd03c…`, tool_version `1.1.1`. Appended by
`analysis/ligature/probe-23-add-finding.py`, which verifies append-only-ness (first 88
lines byte-identical, 88 → 89, 89 unique ids, all 17 schema fields present, enum
membership asserted) and whose `repro_cmd` was **run verbatim in this session**.

---

## 8. Scope constraints (§3) — confirmed

- **Only `date-creusot/` touched.** Four new files, all `analysis/**`:
  `probe-23-legs.py`, `probe-23-legs-transcript.txt`, `probe-23-release-evidence.py`,
  `probe-23-release-evidence.txt`, `probe-23-add-finding.py`, this report — plus one
  appended line in `findings/limitations.jsonl`. Every one is an `allowed_roots`
  pattern (`analysis/**`, `findings/**`); `write-set-check` on the live root is exit 0,
  `write set: clean`, re-run at the end with all the new files present.
- `md5sum -c` against a manifest taken before any probe: **751/751 files OK, zero
  changes** — `project-descriptor.json`, `ci/manifest/WP-DATE-CREUSOT.json`,
  `ci/results/feature_ledger.json`, `specs/_closure/date-creusot-core.json`, `README.md`,
  and all 10 operator `.draft` files untouched. No `init`, no
  `draft`/`approve`/`promote-evidence`/`record-assurance`/`record-ruling`/
  `accept-promotion`. `flake.nix`/`flake.lock` md5 unchanged at the workspace root
  (`8a3fdb4742c8aa8488ea889413611fa3`, `f4bf5566bd4b89f6a6db076eb937f83d`).
- Live `gate-g14` 0 / `validate-closure` 0 / `doctor` 0 / `write-set-check` 0 /
  `status` 0 re-run at the end. `check --json` exit 1 left exactly as found — the known
  10-unapproved-draft state. Nothing was approved, promoted, or ruled on.
- No other pilot root touched (`swisstable-verus`, `crypto-mixed`, `oracle-example`,
  `tools` = 0 files changed). No `git init`/`commit`/`stash`; `upstream/` never synced.
- **Black-box rule honoured:** `--help`, command output and files the tool generated or
  that it names as its own input. `ligature.pyz` never unzipped or read; the ligature
  source checkout never opened. The `scripts/gate_g14.py:gate_workspace` provenance
  strings quoted above are the binary's own output.
- One honest negative: an early exploratory run of mine printed
  `FAIL: 0 cluster(s) blocked, 1 not blocked` for a state I later showed could not be the
  state I thought it was — a `cp -a pristine work` reset inside my own command sequence
  had discarded an earlier edit. Two verbatim replays plus 40 consecutive runs are
  deterministic (`1 cluster(s) blocked`), so I did not report it and it is not a finding.