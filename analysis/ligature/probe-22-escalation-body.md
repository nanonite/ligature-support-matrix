Exact command run (all on an `rsync` scratch copy of `date-creusot/` at `/tmp/p22`, never the live root; the pinned binary was verified with `sha256sum -c SHA256SUMS` -> `ligature.pyz: OK` before anything else ran):

```
$ cd date-creusot && python3 analysis/ligature/probe-22-legs.py
```

Exit codes: `gate-g14` **0** for the three legs below (all three print the `VERIFIED` line).

## What this is not

This does **not** re-file #85. #85's claim is that CG3 is *never checked*; that was true in 1.0.0 and its 1.1.1 re-verification comment records `VERDICT: FIXED`. This report is about the 1.1.1 replacement: the condition is now **labelled** `VERIFIED from artifact data`, and that label is unsound. A reviewer closing #85 on the strength of the `FIXED` verdict should read this first — the verdict does not survive the legs below.

## The derivation, reduced to what it actually reads

19 single-mutation legs, each reset to a pristine snapshot first, reduce the entire condition to a two-part cluster-level proxy:

> `VERIFIED` **iff** (a) every work package **named in the closure profile's `work_packages` list** has at least one achieved-assurance record, **and** (b) no achieved record in that closure — obligation *or* bridge — has `evidence.kind == "kani-bounded-model-check"`.

Nothing else is read. The `VERIFIED` line says so itself:

```
- [G14/info] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: ... is VERIFIED
  from artifact data, not taken on declaration: every work package in the closure has a recorded
  achievement and none of them is a Kani result (['creusot-deductive-check']) -- with no
  per-monomorphization assurance anywhere in the closure, no generic callee it rests on is
  Kani-owned (CG3, plan.md §3)
```

The conclusion "no generic callee it rests on is Kani-owned" is the whole load-bearing content of the condition, and it is derived from "no record in the closure carries the Kani kind string."

## 1. Blind to `depends_on` — `gate-g14` exit 0, `VERIFIED`, on a closure whose Kani dependency it never reads

A Creusot work package that **declares** a dependency on a Kani-owned work package whose only function is a generic, with a coupling note naming the Kani-owned generic callee:

```
$ python3 tools/ligature/ligature.pyz gate-g14
cluster 'date-creusot-core' closes: closure_kind=deductive, 1 work package(s), 0 obligation(s) in the transitive closure, 0 cycle(s) discharged
  - [G14/info] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: generic_callees_type_universal_or_creusot_owned is VERIFIED from artifact data, not taken on declaration: every work package in the closure has a recorded achievement and none of them is a Kani result (['creusot-deductive-check']) -- with no per-monomorphization assurance anywhere in the closure, no generic callee it rests on is Kani-owned (CG3, plan.md §3)
OK: 1 cluster(s) close under their declared profile, 0 released under an accepted degradation record
EXIT=0

$ python3 tools/ligature/ligature.pyz gate-g14 2>&1 | grep -c WP-KANI-OTHER
0
```

The mutated manifest declares:

```json
"depends_on": ["WP-DATE-CREUSOT-CORE", "WP-KANI-OTHER"]
"coupling_notes": [..., "date::year_month_day::to_days calls date::util::generic_helper, whose only assurance is a Kani bounded model check over the i64 monomorphization."]
```

`WP-KANI-OTHER` is a schema-valid manifest (`validate-work-package` raises only the three pre-existing G13 findings the real `WP-DATE-CREUSOT.json` also raises — placeholder `gate_integrity` hashes, write-set overlap — so it is not being rejected, it is simply never read). The closure profile is unchanged and still names only `WP-DATE-CREUSOT`, which is what a single-verifier deductive cluster requires.

**Control, same scratch, one field different** — add `WP-KANI-OTHER` to the closure profile's `work_packages` and it *is* caught:

```
  - [G14/error] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: ... is declared as true, but this closure's artifacts cannot verify it: the closure's own achieved records include ['kani-bounded-model-check'] results, and Kani verifies generics per monomorphization -- whether every generic callee is type-universal or creusot-owned needs type information no artifact in this pipeline carries (CG3). That is a capability gap, not a checked condition (plan.md §3): an unverifiable declaration is never a free pass, and releasing this cluster needs a degradation record naming this condition with a tracking issue
EXIT=1
```

So CG3 is a **closure-membership** test, not a project-level one: a Kani-owned generic callee is "ruled out" simply by not being in the list. Reaching one through a declared `depends_on` is exactly the case the condition exists to police, and no gate reaches it.

## 2. Verifies the wrong disjunct — a Verus-owned cluster is reported as satisfying `..._or_CREUSOT_owned`

The condition is `generic_callees_type_universal_or_creusot_owned`. The derivation establishes only the **negative** of "Kani-owned". Relabel all five achieved records `creusot-deductive-check` -> `verus-deductive-check`:

```
$ python3 tools/ligature/ligature.pyz gate-g14
  - [G14/info] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: ... is VERIFIED from artifact data, ... none of them is a Kani result (['verus-deductive-check']) -- ... no generic callee it rests on is Kani-owned (CG3, plan.md §3)
  - [G14/error] Weekday.C1: WP-DATE-CREUSOT's own provided guarantee is not met by what it achieved: evidence.kind 'verus-deductive-check' is not among required_profile.accepted_evidence_kinds ['creusot-deductive-check']
  ... x5
  - [G17/error] date-creusot-core: conditions.owning_verifier is declared as 'creusot' but the computed closure says 'verus'
EXIT=1
```

CG3 still calls the condition `VERIFIED`. Verus is neither Kani-owned nor Creusot-owned, so neither disjunct is established; the label should have been the gap phrasing.

## 3. Emits `VERIFIED` while stating a premise it has just falsified

Delete 1 of the 5 achieved-assurance records (`Weekday.C1`):

```
$ python3 tools/ligature/ligature.pyz gate-g14
cluster 'date-creusot-core' closes: ...
  - [G14/info] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: ... is VERIFIED from artifact data, not taken on declaration: every work package in the closure has a recorded achievement and none of them is a Kani result (['creusot-deductive-check']) ...
  - [G14/error] Weekday.C1: WP-DATE-CREUSOT provides this obligation but recorded no achieved assurance for it -- record one from this work package's proof certificates with `ligature record-assurance WP-DATE-CREUSOT --proof Weekday.C1=<path>`
$ python3 tools/ligature/ligature.pyz status
cluster date-creusot-core: blocked (closure_kind=deductive) limitations=['generic_callees_type_universal_or_creusot_owned']
```

"every work package in the closure has a recorded achievement" is asserted as a verified premise at the same moment the gate blocks the cluster precisely because that obligation has none. `status` calls the cluster `blocked` and still lists the condition under `limitations`. Premise (a) is work-package-level (>=1 record per WP), not obligation-level, so a single missing record never moves the verdict off `VERIFIED`.

## 4. The `type_universal` disjunct is not merely unchecked — it is unrepresentable

There is no field in any artifact that can declare a generic callee, its type-universality, or its monomorphizations. Both natural homes reject the key outright:

```
$ python3 tools/ligature/ligature.pyz gate-g14     # generic_callees added to ci/results/feature_ledger.json
  - [G14/error] WP-DATE-CREUSOT: assurance report ci/results/feature_ledger.json is not schema-valid: Additional properties are not allowed ('generic_callees' was unexpected)

$ python3 tools/ligature/ligature.pyz gate-g14     # generic_callees added to ci/manifest/WP-DATE-CREUSOT.json
  - [G14/error] .../ci/manifest/WP-DATE-CREUSOT.json: manifest is not schema-valid (Additional properties are not allowed ('generic_callees' was unexpected))
```

```console
$ grep -rn -i "generic" specs/ ci/ project-descriptor.json analysis/ligature/closure-intent.json
specs/_closure/date-creusot-core.json:11:    "generic_callees_type_universal_or_creusot_owned": true,
```

The only occurrence of the string "generic" in the whole artifact set is the condition key itself. So the first disjunct of the condition cannot be evaluated by anything, at any severity, and the relief the gate's own message recommends —

> "releasing this cluster needs a degradation record naming this condition with a tracking issue"

— still has no authoring path (already reported separately as a missing schema/authoring route).

## 5. Minor: `evidence.kind` is the only field consulted, but the enum pins it

Relabelling the records to a non-Kani kind does **not** work around CG3, because `accepted_evidence_kinds` is a closed three-value enum:

```
  - [G14/error] .../ci/manifest/WP-DATE-CREUSOT.json: manifest is not schema-valid ('exhaustive-model-check' is not one of ['kani-bounded-model-check', 'creusot-deductive-check', 'verus-deductive-check'])
```

Worth recording as the positive half of the finding: the Kani-ness test is enum-pinned, so it cannot be defeated by renaming. But it is a test on a *string*, and `evidence.verifier` / `evidence.harness` / `config.toolchain` are never consulted (consistent with the separate #99).

## Contradiction within one gate

The gap phrasing and the `VERIFIED` phrasing are emitted by the same command, on the same condition, and disagree about whether it is a checked condition:

> "**That is a capability gap, not a checked condition (plan.md §3)**: an unverifiable declaration is never a free pass, and releasing this cluster needs a degradation record naming this condition with a tracking issue"

vs.

> "**is VERIFIED from artifact data**, not taken on declaration"

A reviewer who reads the `G14/info` `VERIFIED` line has no signal that the same file's other branch calls this a capability gap, and `status` compounds it by listing the condition under `limitations=` even while reporting `cluster ... closes`.

## Summary

| leg | mutation | `gate-g14` | CG3 |
|---|---|---|---|
| A0 | none (live state) | 0 | `VERIFIED` |
| B1 | delete all 5 records | 1 | declared — no record at all |
| B2 | delete 1 of 5 records | 1 | **`VERIFIED`** (premise false) |
| B3 | `conditions.CG3 = false` | 1 | declared (G17 recomputation) |
| B4 | `conditions.CG3` key removed | 1 | profile schema-invalid |
| B5 | `conditions.CG3 = "yes"` | 1 | profile schema-invalid |
| B6 | all records -> kani kind | 1 | declared (kani in closure) |
| B7 | all records -> verus kind | 1 | **`VERIFIED`** (wrong disjunct) |
| B8 | Kani-owned bounded cluster | 1 | declared (kani in closure) |
| B9 | 1 of 5 records kani | 1 | declared (kani in closure) |
| B10 | `generic_callees` in ledger | 1 | declared (schema rejects the field) |
| B11 | `generic_callees` in manifest | 1 | declared (schema rejects the field) |
| B12 | manifest accepts creusot+kani | 0 | `VERIFIED` |
| C1 | Kani generic WP not in closure list | 0 | **`VERIFIED`** |
| C2 | same WP named in closure list | 1 | declared (kani in closure) |
| C3 | `verifier=kani`, other `kind` | 1 | manifest not schema-valid (enum) |
| C4 | kani kind spelled without "kani" | 1 | manifest not schema-valid (enum) |
| C5 | Kani WP declared in `depends_on` | 0 | **`VERIFIED`** |
| C6 | kani record in `bridge_records` | 1 | declared (kani in closure) |

## Requested fix

Either (a) restore the 1.0 gap phrasing unconditionally for this condition until the artifact model can carry a generic callee's type-universality, and drop the `VERIFIED` label; or (b) keep a checked verdict but make the derivation sound: walk `depends_on` and the whole project's work-package manifests rather than only the closure profile's `work_packages` list, require a *deductive* verifier (not merely a non-Kani one) for the `creusot_owned` disjunct, evaluate premise (a) per obligation rather than per work package, and only label `VERIFIED` when the cluster is not simultaneously blocked for missing assurance. Any relief path the message advertises should be authorable.

Pilot: `date-creusot`
Pinned binary sha256: `3edfd03cd4e6dee30139c48e7921abcf338cb279ff2eb4e4d0bba9a44725deb4` (from `date-creusot/tools/ligature/SHA256SUMS`), `ligature 1.1.1`, content hash `sha256:172a87a8be8406d625b57b1aa96dc8cb76756e615983d8da70aa298892964558`
Stage: probe (chainlink #22), gate-g14
Chainlink finding: `date-creusot-056`
Full 19-leg harness and transcript: `date-creusot/analysis/ligature/probe-22-legs.py`; report `date-creusot/analysis/ligature/probe-22-cg3-generic-callees.md`
