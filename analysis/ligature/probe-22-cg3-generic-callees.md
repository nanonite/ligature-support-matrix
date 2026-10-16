# Probe 22 — CG3 `generic_callees_type_universal_or_creusot_owned` under ligature 1.1.1

**Chainlink issue:** #22 (parent #9, `p1-date-creusot` / `probe`)
**Pilot root:** `date-creusot/`
**Binary:** `ligature 1.1.1`, sha256 `3edfd03cd4e6dee30139c48e7921abcf338cb279ff2eb4e4d0bba9a44725deb4`,
content hash `sha256:172a87a8be8406d625b57b1aa96dc8cb76756e615983d8da70aa298892964558`
**Date:** 2026-09-30
**Escalation filed:** epic #1 **#100**
**Finding logged:** `date-creusot-056` (severity `blocker`)

---

## 1. The question, and the short answer

plan.md §3 asked me to *confirm that CG3 is reported as declared-not-verified*. It is not, on this
pilot's state, under 1.1.1. `gate-g14` exits 0 and reports the condition **VERIFIED from artifact
data**. That part of the plan is stale and should be corrected in the plan itself.

The operator direction then asked the more useful question: *what does CG3 actually check, what makes
it flip, and would a Kani-owned or non-type-universal generic callee be caught.* Answer: CG3 reduces
to a two-part cluster-level proxy over the closure profile's `work_packages` list and nothing else.
A Kani-owned generic callee is caught **only if a work package holding its assurance record is named
in that list** — a dependency, which is how a Creusot proof actually rests on a Kani-owned generic, is
never walked. A generic callee that is not type-universal is not caught at all, and cannot even be
*declared*, because no artifact field exists to declare it.

---

## 2. Method

Black-box rule honoured throughout. `sha256sum -c SHA256SUMS` was run before anything else; after that
only `--help`, command output and files the binary generated were used. The `.pyz` was never unzipped
or read, and the ligature source checkout was never opened.

Every mutation ran on an `rsync` scratch copy under `/tmp/opencode/p22/`, **each leg reset to a
pristine snapshot immediately before the leg**, so no leg can be contaminated by its predecessor. The
live pilot root was only ever read.

- Harness: `analysis/ligature/probe-22-legs.py` — 19 legs, each a single mutation, reporting the CG3
  line(s) plus the real exit code of `gate-g14`, `validate-closure` and `status`.
- Finding appender: `analysis/ligature/probe-22-add-finding.py` — asserts the 17 schema fields, enum
  membership and integer `exit_code` *before* writing, then asserts append-only afterwards.
- Escalation body: `analysis/ligature/probe-22-escalation-body.md` — filed as #100 verbatim.

Not run: `init`, `draft`, `approve`, `promote-evidence`, `record-assurance`, `record-ruling`,
`accept-promotion`. The known 10-unapproved-draft `check --json` exit 1 was left exactly as found.

---

## 3. What CG3 actually checks

The `VERIFIED` line states its own derivation, and it is honest about being coarse:

```
- [G14/info] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: generic_callees_type_universal_or_creusot_owned is VERIFIED from artifact data, not taken on declaration: every work package in the closure has a recorded achievement and none of them is a Kani result (['creusot-deductive-check']) -- with no per-monomorphization assurance anywhere in the closure, no generic callee it rests on is Kani-owned (CG3, plan.md §3)
```

Nineteen legs reduce that to:

> **`VERIFIED`** **iff** (a) every work package **named in the closure profile's `work_packages`
> list** has at least one achieved-assurance record, **and** (b) no achieved record in that closure —
> obligation *or* bridge — has `evidence.kind == "kani-bounded-model-check"`.

Nothing else is consulted. In particular CG3 never reads `depends_on`, never reads anything outside the
closure profile's `work_packages` list, and never reads `evidence.verifier`, `evidence.harness` or
`config.toolchain`.

The full verdict table:

| leg | mutation | `gate-g14` | CG3 verdict |
|------|----------|-----------:|-------------|
| A0 | none (live state) | 0 | `VERIFIED` |
| B1 | delete **all 5** achieved records | 1 | declared — *no record at all* |
| B2 | delete **1 of 5** records (`Weekday.C1`) | 1 | **`VERIFIED`** — premise false |
| B3 | `conditions.CG3 = false` | 1 | declared — G17 recomputation |
| B4 | `conditions.CG3` key removed | 1 | closure profile schema-invalid |
| B5 | `conditions.CG3 = "yes"` | 1 | closure profile schema-invalid |
| B6 | all 5 records → `kani-bounded-model-check` | 1 | declared — *kani in closure* |
| B7 | all 5 records → `verus-deductive-check` | 1 | **`VERIFIED`** — wrong disjunct |
| B8 | Kani-owned **bounded** cluster | 1 | declared — *kani in closure* |
| B9 | 1 of 5 records kani | 1 | declared — *kani in closure* |
| B10 | `generic_callees` in the ledger | 1 | declared — schema rejects the field |
| B11 | `generic_callees` in the manifest | 1 | declared — schema rejects the field |
| B12 | manifest accepts creusot+kani, record is creusot | 0 | `VERIFIED` |
| C1 | Kani generic-callee WP **not** in `work_packages` | 0 | **`VERIFIED`** |
| C2 | same WP **is** in `work_packages` (control) | 1 | declared — *kani in closure* |
| C3 | `verifier=kani`, `harness=kani`, other `kind` | 1 | manifest schema-invalid (enum) |
| C4 | kani cluster, kind `'bounded-model-checking'` | 1 | manifest schema-invalid (enum) |
| C5 | Kani WP declared in `depends_on` | 0 | **`VERIFIED`** |
| C6 | kani record in `bridge_records` | 1 | declared — *kani in closure* |

There are exactly **three** "declared-not-verified" phrasings reachable, and the pilot's own state
reaches none of them:

1. *"no achieved assurance record at all for WP-DATE-CREUSOT — until every work package in the closure
   has recorded evidence, a Kani result nobody wrote down cannot be ruled out"* (B1)
2. *"the closure's own achieved records include [...] results, and Kani verifies generics per
   monomorphization — whether every generic callee is type-universal or creusot-owned needs type
   information no artifact in this pipeline carries"* (B6, B8, B9, C2, C6)
3. *"the closure itself contains no work package at all"* (B11, C3, C4)

### What makes it flip, stated as a rule

| to `VERIFIED` | away from `VERIFIED` |
|---|---|
| every named WP has ≥1 achieved record | a named WP has zero achieved records (phrasing 1) |
| no achieved record has the Kani kind | any achieved record has `kani-bounded-model-check` (phrasing 2) |
| | a named WP's manifest is invalid, so the closure holds no WP (phrasing 3) |

Note the asymmetry in the first row: premise (a) is **per work package**, so four of five records
suffice. That is defect 3 below.

---

## 4. Would a Kani-owned generic callee be caught?

**Partly — and the part that is missing is the part that matters.**

### Caught: by closure membership

`kani-bounded-model-check` anywhere in the closure flips the verdict to declared-not-verified (B6,
B8, B9, C2) and, correctly, to `G14/error` severity. B9 is a useful middle case — 1 of 5 records
relabelled — and CG3 catches it, though it names no obligation or callee, only the fact that "a Kani
result" exists somewhere. Bridges are scanned too (C6).

### Not caught: by dependency (C5) — the sharpest result

A Creusot work package that **declares** it depends on a Kani-owned work package whose only function
is a generic, with a coupling note naming the Kani-owned generic callee:

```json
"depends_on": ["WP-DATE-CREUSOT-CORE", "WP-KANI-OTHER"],
"coupling_notes": [..., "date::year_month_day::to_days calls date::util::generic_helper, whose only assurance is a Kani bounded model check over the i64 monomorphization."]
```

`WP-KANI-OTHER` is a legitimate manifest. `validate-work-package` on it reports only the three
**pre-existing** G13 findings the real `WP-DATE-CREUSOT.json` also reports (placeholder `gate_integrity`
hashes, write-set overlap — `date-ligature-033`/`-034`), so it is not being rejected. It is never read:

```
$ python3 tools/ligature/ligature.pyz gate-g14
cluster 'date-creusot-core' closes: closure_kind=deductive, 1 work package(s), 0 obligation(s) in the transitive closure, 0 cycle(s) discharged
  - [G14/info] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: generic_callees_type_universal_or_creusot_owned is VERIFIED from artifact data, not taken on declaration: every work package in the closure has a recorded achievement and none of them is a Kani result (['creusot-deductive-check']) -- with no per-monomorphization assurance anywhere in the closure, no generic callee it rests on is Kani-owned (CG3, plan.md §3)
OK: 1 cluster(s) close under their declared profile, 0 released under an accepted degradation record
EXIT=0

$ python3 tools/ligature/ligature.pyz gate-g14 2>&1 | grep -c WP-KANI-OTHER
0
```

The gate certifies as *verified* that no generic callee it rests on is Kani-owned, while an artifact in
the same project states the opposite, and the work package's id appears zero times in the output.

**The control isolates the cause.** C2 is the same scratch with exactly one field changed — that work
package added to the closure profile's `work_packages`:

```
  - [G14/error] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: generic_callees_type_universal_or_creusot_owned is declared as true, but this closure's artifacts cannot verify it: the closure's own achieved records include ['kani-bounded-model-check'] results, and Kani verifies generics per monomorphization -- whether every generic callee is type-universal or creusot-owned needs type information no artifact in this pipeline carries (CG3). That is a capability gap, not a checked condition (plan.md §3): an unverifiable declaration is never a free pass, and releasing this cluster needs a degradation record naming this condition with a tracking issue
EXIT=1
```

So CG3 is a **closure-membership test, not a project-level one**: a Kani-owned generic callee is
"ruled out" by not being in a hand-authored list. That list cannot be the right boundary, because a
single-verifier deductive cluster *must* name only the Creusot work packages — so the dependency edge
is precisely the edge that has to carry the generic-callee obligation, and it carries nothing.

C1 is the same defect without the dependency edge: a valid Kani-owned generic-callee work package
sitting in `ci/manifest/` is likewise invisible, and `gate-g14` exits 0.

### The one defence that held up

CG3 cannot be defeated by renaming the evidence kind. `accepted_evidence_kinds` is a closed
three-value enum:

```
  - [G14/error] .../ci/manifest/WP-DATE-CREUSOT.json: manifest is not schema-valid ('exhaustive-model-check' is not one of ['kani-bounded-model-check', 'creusot-deductive-check', 'verus-deductive-check'])
```

C3 and C4 both die there. That is worth crediting: the Kani-ness test is enum-pinned, not a substring
match. It remains a test on a *string in the ledger*, and `evidence.verifier`, `evidence.harness` and
`config.toolchain` are never consulted — consistent with the separate #99.

---

## 5. Would a not-type-universal generic callee be caught?

**No, and it cannot be expressed.** Two independent reasons.

### 5a. The condition's own positive disjunct is never established

The condition is `generic_callees_type_universal_or_creusot_owned`. The derivation establishes only
the **negative** of "Kani-owned". Relabelling all five records `creusot-deductive-check` →
`verus-deductive-check` (B7):

```
  - [G14/info] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: generic_callees_type_universal_or_creusot_owned is VERIFIED from artifact data, not taken on declaration: every work package in the closure has a recorded achievement and none of them is a Kani result (['verus-deductive-check']) -- with no per-monomorphization assurance anywhere in the closure, no generic callee it rests on is Kani-owned (CG3, plan.md §3)
  - [G14/error] Weekday.C1: WP-DATE-CREUSOT's own provided guarantee is not met by what it achieved: evidence.kind 'verus-deductive-check' is not among required_profile.accepted_evidence_kinds ['creusot-deductive-check']
  ... ×5
  - [G17/error] date-creusot-core: conditions.owning_verifier is declared as 'creusot' but the computed closure says 'verus'
EXIT=1
```

CG3 still labels the condition `VERIFIED`. Verus is neither Kani-owned nor Creusot-owned, so neither
disjunct is established, and the honest label is the gap phrasing. (The cluster is blocked anyway, by
CG1/G17 — but the CG3 line is the one asserting a verification that did not happen.)

### 5b. No artifact field can carry the information

The natural declaration,

```json
{"callee": "date::util::generic_helper", "type_universal": false, "monomorphizations_proved": ["i64"]}
```

is rejected by **both** candidate homes:

```
  - [G14/error] WP-DATE-CREUSOT: assurance report ci/results/feature_ledger.json is not schema-valid: Additional properties are not allowed ('generic_callees' was unexpected)

  - [G14/error] .../ci/manifest/WP-DATE-CREUSOT.json: manifest is not schema-valid (Additional properties are not allowed ('generic_callees' was unexpected))
```

And the string "generic" occurs exactly once in the whole artifact set — the condition key itself:

```console
$ grep -rn -i "generic" specs/ ci/ project-descriptor.json analysis/ligature/closure-intent.json
specs/_closure/date-creusot-core.json:11:    "generic_callees_type_universal_or_creusot_owned": true,
```

So `type_universal` is not "unchecked" in the sense of a missing check — there is no way to state it,
so nothing can ever evaluate it, at any severity. This is the same shape as the known concept-spec gap
(WORKER-CONTRACT §0.0: `crates[].specs_search_root` resolves to nothing because concept specs cannot be
promoted), and it is why `G2+ applies_to` is `unverifiable` for all five obligations in `status`.

The relief route the gate's own message advertises is not actually available:

> "releasing this cluster needs a degradation record naming this condition with a tracking issue"

Degradation records have no authoring path — already `date-ligature-040`, confirmed still true in
1.1.1 (no `draft` template covers one, per the nine-template registry in WORKER-CONTRACT §0.0). So
neither the verified route nor the declared route is honestly reachable for a project that has a
non-type-universal generic callee.

---

## 6. Third defect: `VERIFIED` printed over a falsified premise (B2)

Delete one of five achieved-assurance records and the gate blocks the cluster for exactly that gap in
the same run that prints `VERIFIED`:

```
  - [G14/info] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: generic_callees_type_universal_or_creusot_owned is VERIFIED from artifact data, not taken on declaration: every work package in the closure has a recorded achievement and none of them is a Kani result (['creusot-deductive-check']) -- ...
  - [G14/error] Weekday.C1: WP-DATE-CREUSOT provides this obligation but recorded no achieved assurance for it -- record one from this work package's proof certificates with `ligature record-assurance WP-DATE-CREUSOT --proof Weekday.C1=<path>`
```

```console
$ python3 tools/ligature/ligature.pyz status
cluster date-creusot-core: blocked (closure_kind=deductive) limitations=['generic_callees_type_universal_or_creusot_owned']
```

"every work package in the closure has a recorded achievement" is asserted as a verified premise at the
moment the gate blocks the cluster because that obligation has none. Premise (a) counts records per
work package, so one surviving record satisfies it. This matters because a reviewer reading the
`G14/info` line has no way to tell the premise is stale.

---

## 7. The gate contradicts itself

Two phrasings of one condition, from one command, disagree about whether it is a checked condition:

> *"**That is a capability gap, not a checked condition (plan.md §3)**: an unverifiable declaration is
> never a free pass, and releasing this cluster needs a degradation record naming this condition with a
> tracking issue"*

> *"**is VERIFIED from artifact data**, not taken on declaration"*

`status` compounds the ambiguity: it reports `cluster date-creusot-core: closes` while listing
`generic_callees_type_universal_or_creusot_owned` under `limitations=`. A limitation entry is not an
error, but for a condition whose only "limitation" is that the gate believes it verified, the word
carries the opposite of its usual meaning.

---

## 8. Assessment against the probe question

| question | answer |
|---|---|
| Is CG3 reported as declared-not-verified, as plan.md §3 expects? | **No.** It is `VERIFIED` on this pilot's state. The declared phrasing still exists in 1.1.1 but only in three other states. plan.md §3 should be corrected. |
| What does CG3 actually check? | A two-part cluster-level proxy: ≥1 achieved record per closure-named WP, and absence of the `kani-bounded-model-check` kind. `depends_on`, `verifier`, `harness`, `toolchain` are not read. |
| What makes it flip? | Table in §3. Per-WP record presence and the Kani kind, nothing else. |
| Would a **Kani-owned** generic callee be caught? | **Only if a work package holding its assurance record is named in the closure profile's `work_packages` list.** A Kani-owned generic callee reached through a declared `depends_on` — the shape that matters — is missed, at exit 0, with `VERIFIED` printed (C5). |
| Would a **not type-universal** generic callee be caught? | **No, and it cannot be declared.** Neither disjunct is established (B7); no field exists to express type-universality (B10/B11); the advertised relief has no authoring path. |

**Severity: blocker.** This is a release gate. A `G14/info` `VERIFIED` on a condition the gate
elsewhere calls a capability gap, reachable in a state that a real project reaches easily, is worse for a
reviewer than the honest 1.0 wording was. 1.0 said "not checked, reported every run so it never reads as
one" — accurate, if unhelpful. 1.1.1 says "verified", which is wrong in three reproducible ways.

**Relation to epic #1 #85.** #85 claimed CG3 is *never checked*; that was true in 1.0.0 and is fixed in
the narrow sense that the gate now recomputes something. Its re-verification comment (chainlink #94,
2026-09-30 07:42) records `VERDICT: FIXED`; that verdict does not survive C5, B7 or B2. I commented on
#85 with this evidence so it is not closed on that verdict, and scoped the new escalation to the
unsound `VERIFIED` label rather than re-filing #85. #96/#97/#98/#99 re-confirmed, not re-filed.

**Practical consequence for this pilot.** Read the CG3 line as *"the closure is single-verifier and
Creusot-owned"* — which the CG1/G17 findings already say — and **not** as a statement about generics.
The generic-callee question is unverified, and the Kani-dependency case is unreached by any gate.
Manual control until the artifact model can carry a generic callee's type-universality: read the work
package manifests' `depends_on` lists and `coupling_notes`, and check by hand that no Creusot-verified
function calls a generic whose only assurance is a Kani bounded model check.

---

## 9. Files

All under `date-creusot/analysis/ligature/` (`allowed_roots: analysis/**`):

- `probe-22-legs.py` — the 19-leg harness
- `probe-22-add-finding.py` — append-only findings appender with schema assertions
- `probe-22-escalation-body.md` — the #100 body, filed verbatim
- `probe-22-cg3-generic-callees.md` — this report

Plus one appended line in `date-creusot/findings/limitations.jsonl` (`date-creusot-056`).
Full transcript: `date-creusot/analysis/ligature/probe-22-legs-transcript.txt`.
