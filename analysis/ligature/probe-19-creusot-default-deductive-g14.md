# Probe #19 — Creusot as default verifier + deductive closure through G14, and Creusot evidence as *achieved* assurance

Chainlink **#19** `[p1 probe] creusot default + deductive accepted through G14; Creusot evidence recognized`
· pilot root `date-creusot/` · attempt 1/20 · 2026-09-30.

Reproduce everything here with:

```
analysis/ligature/probe-19-legs-gate-g14.py          # legs 0, A-I  (falsification)
analysis/ligature/probe-19-verifier-policy-sweep.py  # verifier_policy.default sweep
analysis/ligature/probe-19-legs-assurance-fields.py  # legs N1-N8   (field-by-field)
analysis/ligature/probe-19-add-finding.py            # the one limitations.jsonl line
analysis/ligature/probe-19-escalation-98-body.md     # epic #1 #98
```

All three probe scripts operate on an `rsync` scratch copy under `/tmp/opencode/p19/`
and **reset it to a pristine snapshot before every single leg**. Nothing intrusive ran
on the live root.

Binary, verified first per WORKER-CONTRACT §1:

```
$ cd date-creusot/tools/ligature && sha256sum -c SHA256SUMS
ligature.pyz: OK
$ python3 tools/ligature/ligature.pyz version | head -1
ligature 1.1.1
```

sha256 `3edfd03cd4e6dee30139c48e7921abcf338cb279ff2eb4e4d0bba9a44725deb4`.

---

## The answer, in two sentences

**Yes** — a `deductive` closure for cluster `date-creusot-core` whose obligations are
all discharged by `creusot-deductive-check` evidence is accepted by `gate-g14`, exit 0,
and `closure_kind` is **computed from the artifacts**, not read from the declaration.
**Yes, but with a boundary worth naming** — the gate recomputes everything *in* the
assurance report and none of the *proof certificate the report points at*: the Creusot
evidence is genuinely grounded when produced and taken on trust when consumed, so
"recognized as achieved assurance" is true of the record and unproven of the certificate.
That boundary is `date-creusot-055` (blocker).

---

## Half 1 — is it accepted end-to-end through G14?

### Declared

| where | value |
|---|---|
| `project-descriptor.json` → `verifier_policy.default` | `creusot` |
| `specs/_closure/date-creusot-core.json` → `closure_kind` | `deductive` |
| `specs/_closure/date-creusot-core.json` → `conditions.owning_verifier` | `creusot` |
| `ci/manifest/WP-DATE-CREUSOT.json` → all 5 `provided_guarantees.accepted_evidence_kinds` | `["creusot-deductive-check"]`, `harness: creusot`, `trusted_assumptions: []` |
| `analysis/ligature/closure-intent.json`, README | `deductive` |

### Computed (live root, this session)

```
$ python3 tools/ligature/ligature.pyz validate-closure
OK: all closure artifacts pass G1a/G1b and G17 profile/record consistency (1 discovered)
EXIT=0

$ python3 tools/ligature/ligature.pyz gate-g14
cluster 'date-creusot-core' closes: closure_kind=deductive, 1 work package(s), 0 obligation(s) in the transitive closure, 0 cycle(s) discharged
  - [G14/info] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: generic_callees_type_universal_or_creusot_owned is VERIFIED from artifact data, not taken on declaration: every work package in the closure has a recorded achievement and none of them is a Kani result (['creusot-deductive-check']) -- with no per-monomorphization assurance anywhere in the closure, no generic callee it rests on is Kani-owned (CG3, plan.md §3)
closure is a per-cluster property with a kind; this gate never asserts a pipeline-wide guarantee (plan.md §4)
OK: 1 cluster(s) close under their declared profile, 0 released under an accepted degradation record
EXIT=0
```

`status` agrees, and `gate-g14` is not reading the declaration back:

```
$ python3 tools/ligature/ligature.pyz status
artifacts (28): promoted=23, validated=5
obligations: 5 declared, 0 with an unmet required dimension
cluster date-creusot-core: closes (closure_kind=deductive) limitations=['generic_callees_type_universal_or_creusot_owned']
```

**Leg I** proves the computation is real rather than a read-back. Flip only
`conditions.owning_verifier` to `kani`, leaving the recorded Creusot assurance in place:

```
$ python3 tools/ligature/ligature.pyz validate-closure
  - [G17/error] specs/_closure/date-creusot-core.json: closure_kind is 'deductive' while conditions.owning_verifier is 'kani' -- a bounded model checker's result holds only within its unwind/harness bounds and enumerated monomorphizations, so a Kani-owned cluster closes 'bounded' (plan.md §4) or carries a degradation record
EXIT=1
$ python3 tools/ligature/ligature.pyz gate-g14
  - [G14/error] .../specs/_closure/date-creusot-core.json: ignored as invalid and excluded from closure computation
FAIL: no closure profile discovered -- there is no cluster to close, and an empty closure is not a release
EXIT=1
```

And **leg C** proves `closure_kind` itself is derived from the evidence kind: relabel
the five records `creusot-deductive-check` → `kani-bounded-model-check` and the gate
refuses to call the cluster deductive.

```
  - [G17/error] date-creusot-core: conditions.owning_verifier is declared as 'creusot' but the computed closure says 'kani' -- conditions are recomputed, never stored-and-trusted
  - [G17/error] date-creusot-core: closure_kind is 'deductive' but the transitive closure contains ['kani-bounded-model-check'] -- a bounded result anywhere in the closure makes the cluster's guarantee bounded (plan.md §4)
EXIT=1
```

### Where "end-to-end" is qualified

The chain up to G14 is **not** all green, and none of the red is new. Each item below
is an already-recorded finding, not something this probe discovered:

| step | exit | why | already recorded as |
|---|---|---|---|
| `validate` (G1a/G1b/G2+) | 0 | 4 boundaries; 6 `info` on `applies_to unverifiable` | `date-ligature-022` |
| `validate-interaction` (G1a/G1b/G15/R2) | **1** | 5 staged `.draft` files missing `review` | `date-ligature-100` (#97) |
| `validate-work-package` (G13) | **1** | placeholder `gate_integrity` hashes for `scripts/witness_renderer.py` + `xml_escape.py`; `allowed_write_set`/`protected_write_set` overlap | `date-ligature-033`, `date-ligature-034` |
| `gate r1-g16` | **1** | 5 realized calls absent from `I`, awaiting a human risk ruling | `date-creusot-042`/`-043` |
| `validate-closure`, `gate-g14` | **0** | — | — |
| `gate g18`/`g19`/`g20` | 0 | **vacuously** — "no witness specs discovered"; bridges and witnesses have no producer in 1.1.1 | `date-ligature-095`/`-097` |
| `check --json` | **1** | the known pending operator state: 10 unapproved drafts + 5 pending human rulings | #95 runbook, #96/#97 filed |

So: **G14 itself accepts the deductive Creusot closure, and its own inputs are sound.**
The reds are all upstream and all already triaged. `check --json` exiting 1 was left
exactly as found — no `approve`, `promote-evidence`, `record-ruling` or
`accept-promotion` was run, and all 10 operator `.draft` files still carry their
06:47 mtimes.

### The load-bearing surprise: `verifier_policy.default` is inert

Every read-only command was run three times on the same scratch, with only
`verifier_policy.default` set to `creusot` / `kani` / `verus`
(`probe-19-verifier-policy-sweep.py`):

```
command                                         creusot   kani  verus  output
validate                                              0      0      0  IDENTICAL
validate-interaction                                  1      1      1  IDENTICAL
validate-evidence                                     0      0      0  IDENTICAL
validate-work-package ci/manifest/WP-DATE-CREUSOT.json 1      1      1  IDENTICAL
validate-closure                                      0      0      0  IDENTICAL
gate-g14                                              0      0      0  IDENTICAL
gate g18 / g19 / g20                                  0      0      0  IDENTICAL
gate r1-g16                                           1      1      1  IDENTICAL
doctor / write-set-check / status                     0      0      0  IDENTICAL
check --json                                          1      1      1  IDENTICAL
```

**Not one byte of output changes.** With `default: kani`, `gate-g14` still closes the
cluster as `closure_kind=deductive` on `creusot-deductive-check` evidence and still
prints `VERIFIED from artifact data`. The descriptor field is decoration. This
generalises `date-ligature-024`, which had shown the same for interaction validation
only — it holds for **every** command in the binary.

What actually carries "Creusot" into the closure is two other places, and both are
enforced: `conditions.owning_verifier: creusot` in the closure profile (leg I), and
`accepted_evidence_kinds: ["creusot-deductive-check"]` per obligation in the work-package
manifest (leg C). So the answer to *"is Creusot as the default verifier accepted
through G14"* is: the *default* is not, because it is never read — but the closure
profile and the per-obligation evidence kind are, and they are checked rather than
assumed.

---

## Half 2 — is Creusot evidence recognized as *achieved* assurance, not assumed?

### Where the achieved side lives

`record-assurance` is the only producer. It writes the whole ledger, and `gate-g14`
reads nothing else:

```
ci/results/feature_ledger.json  ->  {"obligation_records": [ {obligation_id, record}, x5 ],
                                      "work_package": "WP-DATE-CREUSOT"}
```

Each `record` carries `claim.kind/result`, `evidence.harness/kind/verifier/scope.proof_targets`,
`config.features/target/toolchain`, `support.status` and `trust.assumptions`. All five
live records read `kind: creusot-deductive-check`, `verifier: creusot`, `harness: creusot`,
`claim.result: pass`, `support.status: supported`, `trust.assumptions: []`, and their five
`scope.proof_targets` all point at real `why3find` `proof.json` files under
`rust/date-creusot-core/verif/date_creusot_core_rlib/` — confirmed present.

### The producer is genuinely grounded — confirmed, not assumed

```
$ python3 tools/ligature/ligature.pyz record-assurance WP-DATE-CREUSOT --proof ...
recorded assurance: ci/results/feature_ledger.json (work package WP-DATE-CREUSOT)
  Weekday.C1: creusot-deductive-check supported -- 1 proved goal(s) <- .../weekday/weekday_from_days/proof.json
  Weekday.C2: creusot-deductive-check supported -- 1 proved goal(s) <- .../weekday/impl_Weekday/c_encoding/proof.json
  Weekday.C3: creusot-deductive-check supported -- 1 proved goal(s) <- .../weekday/impl_Weekday/iso_encoding/proof.json
  YearMonthDay.C2: creusot-deductive-check supported -- 50 proved goal(s) <- .../year_month_day/impl_YearMonthDay/from_days/proof.json
  YearMonthDayLast.C1: creusot-deductive-check supported -- 2 proved goal(s) <- .../year_month_day_last/impl_YearMonthDayLast/day/proof.json
EXIT=0
```

It counts real proved goals (55 across the five), and it is fail-closed three ways:

| input | exit | message |
|---|---|---|
| nonexistent `proof.json` | 2 | `evidence path does not exist: .../NOPE/proof.json` |
| real `proof.json` outside the concept's directory | 2 | `must sit under a directory named for its concept ('weekday') -- ... does not, so it cannot be shown to be about this obligation` |
| real `proof.json` with `"proofs": {}` | 2 | `carries no 'proofs' -- this is not a why3find proof certificate` |

And the live ledger is **byte-identical to a fresh regeneration**:

```
pristine ledger md5:     463583d9eda1ed0292800703bf2835cf
regenerated ledger md5:  463583d9eda1ed0292800703bf2835cf
live root ledger md5:    463583d9eda1ed0292800703bf2835cf
```

### The gate recomputes most of the record

Field-by-field falsification (`probe-19-legs-assurance-fields.py` and legs A–H). Each
leg resets the scratch to pristine and mutates exactly one thing.

**RECOMPUTED** — every one of these flips `gate-g14` 0 → 1 with a specific finding:

| mutation | verdict |
|---|---|
| delete all 5 records | blocked ×5, *"provides this obligation but recorded no achieved assurance for it"*; the CG3 limitation also reverts to *"declared as true, but this closure's artifacts cannot verify it: no achieved assurance record at all"* |
| delete 1 record (`Weekday.C2`) | blocked for that obligation only; `status` → `1 with an unmet required dimension` |
| `claim.result` pass → fail | blocked ×5, *"claim.result is 'fail', not 'pass'"* |
| `support.status` supported → unsupported | blocked ×5, *"support.status is 'unsupported', not 'supported'"* |
| `claim.kind` postcondition → precondition | blocked ×5, *"achieved_record is not schema-valid: 'precondition-holds' is not one of [...]"* |
| `evidence.kind` → `kani-bounded-model-check` | blocked ×5 + both G17 recomputation errors above |
| `trust.assumptions` → `["A-SMOKE"]` | blocked ×5 + `[transitive_assumptions_within_policy]` + a G17 recomputation error |

### The gate trusts the certificate pointer and the provenance fields

**TRUST-ON-DECLARATION** — every one of these leaves `gate-g14` at **exit 0**, with the
same `VERIFIED from artifact data, not taken on declaration` line:

| mutation | exit |
|---|---|
| `evidence.scope.proof_targets` → a directory that **does not exist** | **0** |
| `evidence.scope.proof_targets` → a **real** `proof.json` with `"proofs": {}` (nothing discharged) | **0** |
| `evidence.verifier` creusot → kani (kind unchanged) | **0** |
| `evidence.harness` creusot → kani | **0** |
| `config.toolchain` `rustc/cargo-creusot/why3` → `handwritten` | **0** |
| `config.target` `x86_64-unknown-linux-gnu` → `aarch64-unknown-none` | **0** |

And nothing detects the forgery, in either direction:

```
$ ls rust/date-creusot-core/verif/date_creusot_core_rlib/TOTALLY
ls: cannot access '...': No such file or directory
$ python3 tools/ligature/ligature.pyz write-set-check >/dev/null ; echo $?
0                                    # 'write set: clean' -- ci/results/** is in NEITHER allowed_roots NOR protected_roots
$ python3 tools/ligature/ligature.pyz doctor >/dev/null ; echo $?
0
$ python3 tools/ligature/ligature.pyz gate-g14 >/dev/null ; echo $?
0
$ python3 tools/ligature/ligature.pyz report feature-ledger
error: refusing to overwrite the assurance report at ci/results/feature_ledger.json (work package 'WP-DATE-CREUSOT'): `report feature-ledger` and `record-assurance` must not share one path -- run `record-assurance` after `report feature-ledger` so the report is recorded last, or point the manifest's report.emit at a free ci/results/*.json path (e.g. ci/results/<work-package>.json) to separate the two artifacts
EXIT=1
```

The last line is what makes this a `blocker` rather than `friction`: the ledger **can
never be re-derived**, only re-recorded, because the two commands that would write it
collide on one path (already `date-ligature-051`/`-054`/`-056`). There is no
re-derivation to fall back on, so a clean `gate-g14` is not evidence that the creusot
certificates are current.

**What the CG3 line actually certifies.** It says the condition is verified *"from
artifact data, not taken on declaration"*. That is true, and worth keeping: the
`evidence.kind` really is recomputed and a Kani kind really does block. But it
certifies the ledger's own `kind` string, not the certificate that string points at.
Read it as *"the report says Creusot, and the gate did not take the report's word on the
evidence kind"* — not as *"a Creusot certificate was opened and checked."* That is the
gap `date-creusot-055` records.

### Practical consequence for this pilot

The live state is good — the ledger is a genuine `record-assurance` product and matches
a fresh regeneration byte for byte. The rule this probe implies, and the one already
followed here: **`gate-g14` exit 0 is not a certificate check.** Re-run
`record-assurance` and compare md5s; a mismatch is the only in-pilot signal that the
committed ledger is stale or hand-edited.

---

## Findings logged

**One entry appended**, per findings-schema.md:
`date-creusot-055` — *gate-g14 never re-opens the achieved-assurance record's proof
certificate, and ignores its verifier, harness, toolchain and target.* severity
**blocker**, tool `ligature`, chain `new`, pyz `3edfd03c…`, tool_version `1.1.1`.
Append-only verified by script: first 86 lines byte-identical, 87 unique ids, all 17
schema fields present.

**One escalation filed** under epic #1, per WORKER-CONTRACT §2: **#98** —
`gate-g14` crashes with an unhandled `TypeError: unhashable type: 'dict'` at
`gate_g14.py:590 check_transitive_assumptions` when a record's `trust.assumptions`
holds an object instead of an assumption id. The same edit with a **string** produces
four clean findings, so the diagnostic exists and the object shape just misses it.
Reachability caveat stated in the escalation: **not** demonstrated from
`record-assurance` — the manifest schema rejected every non-empty `trusted_assumptions`
shape I tried, so the crash is currently reachable only by editing
`ci/results/feature_ledger.json` directly, which `write-set-check` calls clean. That
second half may be the more interesting half.

**Nothing new escalated elsewhere.** #96/#97 re-confirmed, not re-filed. `check --json`
exiting 1 left exactly as found.

---

## Scope constraints (WORKER-CONTRACT §3) — confirmed

- **Only `date-creusot/` touched.** Exactly 6 files changed since 09:45, all under
  `analysis/**` or `findings/**`, both `allowed_roots` patterns: 5 new
  `analysis/ligature/probe-19-*.{py,md}` (method record) and 1 appended line in
  `findings/limitations.jsonl`.
- **No other pilot root touched:** `swisstable-verus` 0, `crypto-mixed` 0,
  `oracle-example` 0, `tools` 0 files modified.
- `write-set-check` exit 0, `write set: clean`, with the new files present.
  `doctor` exit 0. `validate-closure` exit 0. `gate-g14` exit 0.
- **Pipeline artifacts byte-identical** (`md5sum -c` against a pre-run manifest):
  `project-descriptor.json` `4cc5901a…`, `ci/results/feature_ledger.json`
  `463583d9…`, `ci/results/c_static/rust_date-creusot-core.json` `f308dc2f…`,
  `specs/_closure/date-creusot-core.json` `b2556eb3…`,
  `ci/manifest/WP-DATE-CREUSOT.json` `6a0de0fa…`, `ci/manifest/installation.json`
  `cfb4f9d2…`, `README.md` `f64f8d63…`, `analysis/ligature/closure-intent.json`
  `afa77b0d…`. `flake.nix` `8a3fdb47…`, `flake.lock` `f4bf5566…` — the same values
  #87/#89 recorded, mtimes still 09-24.
- All 10 operator `.draft` files untouched, mtimes still `2026-09-30 06:47:41–43`.
- No `git init` / `git commit` / `git stash`; no `.git` at workspace or pilot root.
  `upstream/date` not synced or inspected.
- Commands invoked, all `date-creusot/tools/ligature/ligature.pyz`: `version`,
  `status`, `check`, `doctor`, `write-set-check`, `validate`, `validate-interaction`,
  `validate-work-package`, `validate-evidence`, `validate-closure`, `gate-g14`,
  `gate g18`/`g19`/`g20`/`r1-g16`, `report feature-ledger`/`contact-sheet` (scratch
  only). **`record-assurance` on scratch only — never on the live root**, which is why
  the live ledger md5 is unchanged. **No `init`, `draft`, `approve`, `approve-pair`,
  `promote-evidence`, `record-ruling` or `accept-promotion` anywhere.**
- **Black-box rule honoured:** `sha256sum -c SHA256SUMS` first, then only `--help`,
  command output and generated files. The `.pyz` was never unzipped or read; the
  ligature source checkout was never opened. The traceback text quoted in #98 comes
  from the binary's own stdout on a scratch copy.

---

## What a follow-up should do

1. **#98** needs a human read before the ligature owner is told: it is a real
   unhandled traceback in the release gate, but reachability from the sanctioned
   producer is unestablished and the manifest schema's rejection of every non-empty
   `trusted_assumptions` shape is arguably the larger bug.
2. `date-creusot-055` wants either `gate-g14` resolving `scope.proof_targets`, or the
   CG3 line narrowed to say what it actually verified. Either closes the gap; the
   current wording invites the stronger reading.
3. `ci/results/**` belongs in `write_set.protected_roots` — a generated assurance report
   that decides a deductive release is currently unpoliced by `write-set-check`.