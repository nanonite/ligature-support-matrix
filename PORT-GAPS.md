# Howard Hinnant/date → Rust/Creusot port gaps

Pinned upstream: `upstream/date` v3.0.5, commit
`179a6b921ccd6179b5b04dce812a89f71a51b4df`. The current Ligature baseline is
1.5.1, bundle SHA-256
`d704c5a5875d200214310c1fca7854a14a105c1b74cebaa5bc03f6a870bcc030`; the live
re-check for this pilot is in
[`analysis/verification/ligature-1.5.1/README.md`](analysis/verification/ligature-1.5.1/README.md).
The P1 findings below were recorded against cargo-creusot 0.12.0-dev, which
Ligature 1.5.1's verifier compatibility matrix still lists as the measured
compatible version. Detailed per-finding evidence is in
[`analysis/ligature/reverify-VERDICTS.md`](analysis/ligature/reverify-VERDICTS.md).

This file separates source scope cuts, Codesight limits, Creusot proof and
emission friction, Ligature intake behavior, and decisions that belong to the
pilot operator.

## The Rust crate implements a scoped calendar subset

- **Category:** Cut or simplified behaviour.
- **C++ construct / upstream location:** The pinned library exposes a broader
  calendar and time-zone API across `include/date/date.h` and
  `include/date/iso_week.h`.
- **What the Rust port does instead:**
  [`rust/date-creusot-core/src/lib.rs`](rust/date-creusot-core/src/lib.rs)
  names the ported subset: `days_from_civil`/`civil_from_days` through
  `YearMonthDay::{to_days,from_days}`, `weekday_from_days`, weekday C and ISO
  encodings, `YearMonthDay::ok`, `YearMonthDayLast::day`, and
  `IsoWeekday` conversion/encoding. The modules also define the `Year`,
  `Month`, `Day`, and `Days` value types those operations need.
- **Why:** This pilot proves a bounded set of arithmetic and calendar
  relationships. It does not claim a complete Rust replacement of date's
  parsing, formatting, time-zone database, or broader calendar surface.
- **Impact:** Compatibility and proof claims apply only to the listed subset.
  Consumers must not infer parity for omitted date APIs from the verified
  arithmetic functions.
- **Status:** ruled-scope-cut.
- **Finding IDs:** none; this is the documented pilot boundary in `src/lib.rs`
  and the Stage 0–3 decision record.
- **Generalizable lesson:** State the exact transferred API surface alongside
  the proof result; a verified subset is not evidence of whole-library parity.

## Codesight cannot resolve the C++ header symbols for this subset

- **Category:** Tooling blind spots.
- **C++ construct / upstream location:** `include/date/date.h` definitions for
  civil conversion, `weekday`, and `year_month_day`; `include/date/iso_week.h`
  definitions for ISO-week operations.
- **What the Rust port does instead:** The Rust implementation and its
  contracts use the pinned C++ headers, checked-in evidence, and direct source
  review. The Codesight index provides no usable caller/callee or impact graph
  for the target header symbols.
- **Why:** The recorded Codesight file outlines classify both headers as C and
  expose only a small outline. Call, type-hierarchy, and impact queries return
  `Symbol not found`. The import graph does show `iso_week.h → date.h`, but the
  reverse import query reports zero importers.
- **Impact:** Codesight cannot establish that the listed symbols or edges are
  absent from the C++ source. Its missing results are parser/index coverage
  limits, not evidence about program behavior.
- **Status:** open.
- **Finding IDs:** `date-mcp-001`, `date-mcp-002`.
- **Generalizable lesson:** Treat a failed symbol lookup as an index limitation
  until the parser's language and extraction coverage are validated against the
  source file.

## Creusot proof reruns are blocked by the pinned environment; G14 scope omits `round_trip`

- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** The port's civil-date round trip is
  derived from `date.h`'s `year_month_day` conversion and day-count routines.
- **What the Rust port does instead:** The Rust crate contains Creusot
  contracts and checked-in proof output. There are 93 `proof.json` files under
  `rust/date-creusot-core/verif`; the saved
  `year_month_day/impl_YearMonthDay/round_trip/proof.json` contains a
  `vc_round_trip` proof tree with five Alt-Ergo prover nodes.
- **Why:** The requested pinned Nix environment is not runnable in this
  execution environment. Nix fails before reaching the recorded cvc5 patch URL:
  daemon socket access is denied and the fetcher-lock directory is read-only.
  The earlier cvc5 URL 404 therefore remains an environment finding, not a
  fresh observation in this run. The task explicitly excludes changing the
  flake.
- **Impact:** Existing proof files are available for inspection, but this pass
  cannot freshly regenerate or validate them with Creusot. The scratch G14 run
  exits 0 with `closure_kind=deductive` and zero obligations in its transitive
  closure; it does not consume `round_trip` as a closure obligation. A
  deductive closure result must not be presented as a fresh proof of that
  method.
- **Status:** open; proof reruns are NOT-RUNNABLE(ENV), and adding
  `round_trip` to the closure requires an operator-approved assurance-scope
  change through the sanctioned workflow.
- **Finding IDs:** `date-creusot-001`, `date-creusot-035`–`date-creusot-041`,
  `date-creusot-044`, `date-creusot-049`,
  `date-creusot-051`, `date-creusot-059`, `date-creusot-060`.
- **Generalizable lesson:** Keep generated proof artifacts, fresh prover runs,
  and the obligations actually consumed by a closure gate as three distinct
  claims.

## Creusot compile and logic-emission friction has source-level workarounds

- **Category:** Proof-tool build and emission friction.
- **C++ construct / upstream location:** The port's constexpr date operations
  and cross-concept calendar contracts; these findings concern the Rust and
  Why3 representation needed to verify the corresponding behavior.
- **What the Rust port does instead:** Logic bodies use `pearlite! { ... }` so
  plain `rustc` can parse them after the dummy macro removes Creusot-only items.
  The port splits or cfg-gates imports of procedural contract attributes to
  avoid `unused_imports` false positives while retaining them under Creusot.
  For cross-module proofs it spells domain constraints inline rather than
  relying on opaque logic twins or boolean logic functions; `month_length`
  takes the year and returns `Int` so its definition remains transparent.
- **Why:** The recorded Creusot 0.12 behavior includes plain-rustc parsing of
  Pearlite `@` syntax before macro erasure, false unused-import warnings for
  attribute macros, and opaque cross-module logic emission for twins and
  boolean-returning logic functions. The fixes are proof-encoding and build
  workarounds in this port, not changes to the C++ behavior being ported.
- **Impact:** The workarounds keep ordinary Rust builds and the Creusot proof
  encoding compatible, but contracts duplicate domain expressions and may
  need revision if Creusot changes its parsing or emission rules. The pinned
  Nix shell is currently NOT-RUNNABLE(ENV), so this pass could not freshly
  rerun the Creusot-dependent checks.
- **Status:** mitigated in the current Rust source; upstream behavior remains
  a recorded tool limitation, not a verified current-version fix.
- **Finding IDs:** `date-creusot-047`, `date-creusot-048`,
  `date-creusot-050`.
- **Generalizable lesson:** Keep proof-language syntax inside the verifier's
  supported parsing boundary and test both ordinary Rust compilation and
  verifier emission when changing proof encodings.

## P1 transfer gaps backfilled from the initial port

The entries above were written during the later recheck. The entries in this
section are the C++→Rust gaps the initial port (P1) found before this file
existed, reconstructed from `findings/limitations.jsonl`, `README.md`, the Rust
source, and `analysis/`. Finding ids are the original P1 records; where a later
record corrected an earlier diagnosis, both are listed. The two P1 gaps that
already had entries above are the subset scope cut and the Codesight header
misclassification.

### Era arithmetic is specified only inside C++'s non-overflow domain

- **Category:** Cut or simplified behaviour.
- **C++ construct / upstream location:** `include/date/date.h:2979-2993`
  (`year_month_day::to_days`) and `:3093-3109`
  (`year_month_day::from_days`) add the 719468 epoch shift and multiply an era
  by 146097 in `int`; `year` is stored in `short`, and `month`/`day` in
  `unsigned char` (`date.h:401-427`, `:1420-1435`, `:1545-1570`). Outside the
  representable year range those signed operations overflow, which is
  undefined behavior in C++.
- **What the Rust port does instead:**
  [`rust/date-creusot-core/src/year_month_day.rs`](rust/date-creusot-core/src/year_month_day.rs)
  mirrors the C++ widths (`Year(i16)`, `Month(u8)`, `Day(u8)`, `Days(i32)`) and
  makes the defined domain explicit: `from_days` requires
  `-12687428 <= dp <= 11248737`, and `to_days_bounded` requires a year in
  `[-32767, 32767]`, a month in `[1, 12]`, and a day in `[1, 31]`. The oracle
  uses the same domains in `oracle/operations.md`.
- **Why:** There is no defined C++ behavior to port outside the type widths and
  the day-count range in which the era arithmetic does not overflow. Evidence
  E-12 fixes the domain and E-15 records the total, normalizing behavior of
  `to_days`.
- **Impact:** `from_days` is unavailable outside its stated range, and the
  oracle cannot compare values there because upstream would invoke UB.
  `to_days` remains total so that the C++ normalization quirk is preserved.
- **Status:** ruled-scope-cut.
- **Finding IDs:** `date-creusot-001`, `date-creusot-035`; the range is also
  recorded in `evidence/E-12.json`, `evidence/E-15.json`, and
  `oracle/operations.md`.
- **Generalizable lesson:** When upstream relies on signed overflow outside its
  type widths, define and document the domain where the transfer is meaningful
  instead of claiming to port undefined behavior, and test only that domain.

### Narrowing casts in the era arithmetic generate range obligations

- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `include/date/date.h:3093-3109`
  (`year_month_day::from_days`) constructs `year{y + (m <= 2)}`,
  `month(m)`, and `day(d)`, narrowing the recovered `int` values to `short`
  and `unsigned char`; `date.h:2979-2993` performs the reverse widening.
- **What the Rust port does instead:** `from_days` ends with
  `Year((y + if m <= 2 { 1 } else { 0 }) as i16)`, `Month(m as u8)`, and
  `Day(d as u8)`. Its contract states the recovered month and day ranges and
  the postcondition against `civil_from_days`, so each narrowing cast has a
  lower and upper bound to prove.
- **Why:** Creusot emits `Int16.of_int`/`Int32.to_int` boundary goals for each
  cast. The provers could not connect the inline month/day computation to the
  `month_day_from_doy` range fact, and the year cast needed the era-recovery
  reasoning. A `proof_assert!` experiment inside `civil_from_days` made this
  worse and was reverted.
- **Impact:** At P1 `vc_from_days` stood at 55/61 goals. The root cause was
  later found to be the false logic-twin postcondition in
  `date-creusot-038`, not missing cast lemmas; after that fix `vc_from_days`
  was fully proved. The explicit range facts remain in the contracts because
  the casts still need them.
- **Status:** fixed (after `date-creusot-038`; the range contracts remain).
- **Finding IDs:** `date-creusot-001`, `date-creusot-035`,
  `date-creusot-038`.
- **Generalizable lesson:** Narrow C++ integer types create a proof obligation
  at every cast. When those obligations fail, check the specification and its
  proof twin for a false statement before writing range lemmas; a cast failure
  can be a symptom rather than the cause.

### A proof-only logic twin silently diverged from the program body

- **Category:** No faithful Rust or verifier equivalent.
- **C++ construct / upstream location:** `include/date/date.h:2979-2993`
  (`year_month_day::to_days`) and `:3093-3109`
  (`year_month_day::from_days`), the two directions of the epoch-day
  conversion.
- **What the Rust port does instead:** The contract-facing inverse is the
  `#[logic]` function `civil_from_days` in
  [`year_month_day.rs`](rust/date-creusot-core/src/year_month_day.rs), a
  hand-written twin of the executable `from_days`. Its first version omitted
  `let z = z + 719468;`, the epoch shift the program performs. The twin was
  corrected to mirror the program body.
- **Why:** Creusot contracts cannot call program functions in a logic context,
  so the inverse has to be restated as a separate proof-only body. That body is
  stripped from ordinary builds, so neither `rustc` nor the oracle executes it;
  there is no automatic refinement check tying the twin to the program.
- **Impact:** The stated postcondition was false for nearly all inputs, so the
  prover was correctly refusing to prove it. A 50,000-case brute-force
  comparison of the twin with the executable function failed 100% before the
  fix and passed afterwards. The 143-case oracle suite was unaffected before
  and after because it calls only the executable function.
- **Status:** fixed.
- **Finding IDs:** `date-creusot-038` (corrects the diagnosis in
  `date-creusot-035`/`date-creusot-036`).
- **Generalizable lesson:** Every proof-only twin needs a differential test
  against the executable function it models. A passing runtime oracle says
  nothing about code that is stripped from runtime builds.

### `round_trip` was unprovable because a callee contract omitted an identity

- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `include/date/date.h:2998-3000`
  (`year_month_day::operator sys_days`) and `:3093-3109`
  (`year_month_day::from_days`); the round trip is
  `from_days(to_days(ymd)) == ymd`.
- **What the Rust port does instead:** `YearMonthDay::round_trip` states the
  composition over the logic functions (`civil_from_days(days_from_civil(...))`)
  and calls the wrapper `to_days_bounded`. That wrapper's contract originally
  stated only the day-count range `[-12687428, 11248737]`, not the
  `days_from_civil` identity its one-line body computes. A second `#[ensures]`
  restating that identity was added.
- **Why:** A callee exposes only its own contract; a VC never sees the callee's
  body. With only the range in scope, the postcondition and the computed day
  count were unrelated terms, so the goal was unprovable in principle rather
  than merely hard for search.
- **Impact:** P1 recorded 5/7, then 6/10, sub-goals and suspected a missing
  lemma; raising the search budget made the split worse. After the missing
  `#[ensures]` was added, `vc_round_trip` closed 5/5 under the default
  `time 1 / depth 6` budget and the whole crate reported `Proved (93 files)`.
  `date-creusot-051` also claimed a resolution but did not match the tree that
  `date-creusot-059` measured from scratch; `059` supersedes it.
- **Status:** fixed.
- **Finding IDs:** `date-creusot-001`, `date-creusot-036`,
  `date-creusot-039`, `date-creusot-051`, `date-creusot-059`.
- **Generalizable lesson:** A missing postcondition on a wrapper is
  indistinguishable from a missing lemma. Dump the VC and read its hypotheses
  before writing lemmas, and make every wrapper restate the identity its body
  computes.

### The era-arithmetic inverse identities need explicit exactness lemmas

- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `include/date/date.h:2979-2993`
  (`year_month_day::to_days`) and `:3093-3109`
  (`year_month_day::from_days`). Both directions invert nested truncating
  divisions: `doe` into `era`/`yoe`/`doy`, and `doy` into month/day.
- **What the Rust port does instead:** The proof composes named `#[logic]`
  lemmas in [`year_month_day.rs`](rust/date-creusot-core/src/year_month_day.rs):
  `year_of_era_from_doe_exact` with the mixed-radix helpers
  `century_of_era_year` and `era_quotients`, plus
  `month_day_from_doy_exact`, `era_of_days`, `civil_parts`, `valid_era_day`,
  `doe_bounds`, and the composite `days_civil_round_trip` exposed through the
  boolean wrapper `civil_round_trip_holds`.
- **Why:** Integer division does not distribute over addition, so the
  automatic provers cannot invert the formula. Raising `why3find.json` from
  `time 1 / depth 6` to `time 5 / depth 12` made the split worse, ruling out
  "more search budget" as the fix. The first suggested year-of-era lemma was
  false over the full `[0, 399] × [0, 365]` box because the forward map is not
  injective there; the proved side condition `valid_era_day(yoe, doy)` selects
  exactly the 146,097 real days of a 400-year era.
- **Impact:** P1 left `round_trip` open (`date-creusot-036`/`039`/`049`). The
  later certificate proves 93/93 proof files and 270/270 leaf goals, with
  `vc_round_trip` at 5/5 sub-goals under the default budget. The 143-case
  oracle suite also passes, so the gap was proof coverage, not observed
  behavior.
- **Status:** fixed (closed later under chainlink #88).
- **Finding IDs:** `date-creusot-001`, `date-creusot-036`,
  `date-creusot-039`, `date-creusot-049`, `date-creusot-059`.
- **Generalizable lesson:** Calendar-era inversion is a mixed-radix exactness
  argument, not a search-budget problem. State the tight side condition that
  makes the recovery injective, then give the prover the digit split
  explicitly.

### Cross-module logic twins and bool predicates are opaque in Creusot

- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `include/date/date.h:1700-1715`
  (`year::is_leap`, `year::ok`), `:1570` (`month::ok`), and `:2743-2756`
  (`year_month_day_last::day`), whose contracts are used by
  `year_month_day::ok` and the day bound.
- **What the Rust port does instead:** The contracts inline the domain
  constraints (year != -32768, month in `[1, 12]`, day in `[1, 31]`, and the
  leap rule) instead of naming the `ok_logic`/`is_leap_logic` twins.
  `month_length` takes the year as `Int` and computes the leap rule internally
  so it returns `Int` and stays transparent; its `#[ensures]` restates the
  month table across the module boundary.
- **Why:** In Creusot 0.12 a `#[logic]` twin is emitted as an opaque predicate
  in every module except its home module. A `bool`-returning logic function is
  also forced to an opaque predicate (`retty` is `None`), so a contract cannot
  compute with it. A scratch crate reproduced the same-module-succeeds,
  cross-module-fails pattern.
- **Impact:** The first version of the port failed `vc_day`, `vc_ok`, and
  `vc_to_days_bounded` when the contracts named the twins and the boolean
  `is_leap_year`. Inlining fixed all of them, at the cost of duplicating the
  domain expressions in code and contracts, where they can drift apart.
- **Status:** worked-around.
- **Finding IDs:** `date-creusot-050`; `date-creusot-059` records the later
  `month_length` contract restatement.
- **Generalizable lesson:** Do not name a cross-module logic twin or a
  bool-returning logic predicate in a contract unless the verifier emits it
  transparently. Prefer a transparent `Int`-returning function or inline the
  fact, and keep the inlined copy under review.

### Tuple and record equality in the deep model blocks `eq` refinement

- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `include/date/date.h:3022-3026`
  (`operator==` for `year_month_day`) and `:2781-2785` (`operator==` for
  `year_month_day_last`), which compare the year/month/day fields directly.
- **What the Rust port does instead:** The `PartialEq::eq` contracts are spelled
  over field views (`self.0@ == other.0@`, or the component-wise conjunction)
  rather than the canonical
  `result == (self.deep_model() == other.deep_model())`. The deep models are
  named records (`YearMonthDayView`, `YearMonthDayLastView`, `CivilView`)
  rather than generated tuples, and `round_trip` compares fields instead of
  using `==`.
- **Why:** The trait's refinement goal is a tuple/record equality, and the
  provers cannot decompose a record equality on a generated tuple type when
  the hypothesis speaks about component `deep_model` functions that are opaque
  outside their home module. The canonical spelling therefore leaves
  `eq__refines` undecomposable.
- **Impact:** The canonical spelling failed the two `eq__refines` goals for
  `YearMonthDay` and `YearMonthDayLast`; the field-view spelling proves both.
  The port deliberately deviates from the canonical Creusot `eq` spec, and
  the deviation is documented at each site.
- **Status:** worked-around.
- **Finding IDs:** `date-creusot-037`, `date-creusot-059`.
- **Generalizable lesson:** A verifier's internal representation shapes the
  specification style. When generated tuple equality is opaque, state
  refinement field-wise and give the model a named record instead of forcing
  the canonical spelling.

### `const fn` is within Creusot's reach, but const-eval-only code is untested

- **Category:** Tooling blind spots in the transfer.
- **C++ construct / upstream location:** The `CONSTCD14`/`CONSTCD11`
  annotations on the ported calendar functions, for example
  `include/date/date.h:473` (`weekday_from_days`), `:706-727`
  (`year_month_day` constructors and `from_days`), `:2743`
  (`year_month_day_last::day`), `:2979` (`to_days`), and `:3093`
  (`from_days`).
- **What the Rust port does instead:** Every ported operation is a `const fn`
  mirroring the C++ annotation, and Creusot emits and discharges verification
  conditions for them. A probe also compiled const-fn versions of the era
  arithmetic (`const_days_from_civil`, `const_civil_from_days`) that are only
  evaluated at compile time; those inherited the same 33/37 and 55/61
  era-arithmetic gap as their non-const counterparts.
- **Why:** Creusot 0.12 supports contracts on `const fn`, including const-eval
  contexts. The residual failures were the shared era-arithmetic lemma gap,
  not a const-fn limitation: the `Int32` truncating division in a const body
  still has to be connected to the `Int` division in the `#[logic]` twin.
- **Impact:** `const fn` reach is not a proof gap for this port; it did not
  restrict what could be verified. Const-eval-only variants have no runtime
  callers and therefore no oracle coverage, so their behavior rests on the
  corresponding executable functions.
- **Status:** worked-around (the era gap is tracked separately).
- **Finding IDs:** `date-creusot-041`.
- **Generalizable lesson:** Test whether the verifier accepts `const fn`
  contracts instead of assuming it does not; C++ `constexpr` does not force a
  scope cut. Const-eval-only code still needs its own proof and a differential
  check against an executable path.

### The oracle covers five operations and one mapped upstream test

- **Category:** Tooling blind spots in the transfer.
- **C++ construct / upstream location:** The pinned Howard Hinnant/date ctest
  suite under `upstream/date/test/`, and the five operations in
  `oracle/operations.md`: `days_from_civil`, `civil_from_days`,
  `weekday_from_days`, `ymd_ok`, and `iso_weekday_from_days`.
- **What the Rust port does instead:** `oracle/cases.jsonl` contains 143
  differential cases executed by generated nextest tests against
  `oracle/golden/results.jsonl`. `oracle/test-map.csv` maps exactly one
  upstream test (`date_test_pass_year_month_day_test`) to case IDs; the other
  nine subset rows are `unmapped` because they exercise operations the pilot
  does not port: weekday arithmetic, `last`, and weeknum types. The C++ driver
  was rewritten with a strict parser and exact field-set validation, and
  `oracle/rust-check/.config/nextest.toml` gained the protocol's `ci` profile.
- **Why:** The pilot's scope is a calendar subset, not the whole library, and
  the inherited driver accepted unknown top-level and input fields instead of
  rejecting them. Without the `ci` profile, the protocol-required nextest
  command could not run at all.
- **Impact:** Parity is established only for the five operations and the input
  domains in `oracle/operations.md`; it is not evidence for omitted upstream
  behavior. Before the driver rewrite, a malformed case could enter the golden
  file silently. The suite has 143 cases; the "150 cases" quoted in
  `date-creusot-001` is a stale count.
- **Status:** worked-around; the coverage boundary remains.
- **Finding IDs:** `date-creusot-044`, `date-creusot-045`; the stale count is
  noted in `date-creusot-001` and `FUTURE-WORK-round-trip-proof.md`.
- **Generalizable lesson:** Map upstream tests to oracle cases explicitly and
  report the mapped and unmapped rows together. A green differential suite is
  a statement about the encoded operations and domains, not about the upstream
  library.

## R1/G16 still needs five operator-reviewed interactions

- **Category:** Tooling blind spots.
- **C++ construct / upstream location:** Cross-concept date operations
  corresponding to `year_month_day::ok`, `year_month_day_last::ok`, and
  `year_month_day_last::day` in the pinned headers.
- **What the Rust port does instead:** Rust uses direct calls across its
  `YearMonthDay`, `YearMonthDayLast`, `Year`, and `Month` modules. On the
  disposable valid-descriptor copy, R1/G16 discovers 11 call sites. Against
  the saved C_static report, five are high-severity and absent from the
  interaction set; after sanctioned `extract-c-static` refreshes the report,
  those calls are classified as value-domain inquiries and become warnings.
- **Why:** The interaction records describe architectural boundaries. The
  refreshed extractor classifies these five bool-returning calls as computed
  value-domain inquiries, while the saved report has no callee shape and treats
  them as unclassified.
- **Impact:** `gate-r1-g16` exits 1 with five high findings and nine
  informational findings when it reads the saved report. After re-extraction
  it exits 0 with five warnings, but only 6 of 11 call sites are counted as
  checked against I. The absent edges are `YearMonthDay.ok → Year.ok`,
  `YearMonthDay.ok → Month.ok`, `YearMonthDayLast.ok → Year.ok`,
  `YearMonthDayLast.ok → Month.ok`, and `YearMonthDayLast.day → Year.is_leap`.
  After resolving the descriptor conflict, the operator should refresh the
  report and decide whether warning-only, uncounted calls are acceptable or
  need reviewed interaction artifacts. This is not a claim that the Rust calls
  are incorrect.
- **Status:** open; operator decision required after the report refresh.
- **Finding IDs:** `date-creusot-042`, `date-creusot-043`, `date-ligature-036`,
  `date-ligature-038`, `date-ligature-050`.
- **Generalizable lesson:** A discovered direct call is not an approved
  architectural interaction. Keep call discovery, contract review, and
  promotion as separate steps.

## Ligature 1.3.11 still has intake and workflow gaps

- **Category:** Tooling blind spots.
- **C++ construct / upstream location:** Not a source-language semantic
  divergence. These findings concern Ligature's project descriptor, prompt,
  draft/approval, evidence, and reporting workflows used to carry the port's
  contracts.
- **What the Rust port does instead:** The pilot keeps its source and proof
  work in the Rust crate, records interaction and evidence artifacts through
  Ligature's sanctioned commands where available, and records the current
  per-finding outcomes in the verdict overlay.
- **Why:** The 1.3.11 probes still show descriptor diagnostics that differ
  across commands, a stale reliance-policy template path, draft scoping based
  on crate membership rather than the declared write set, ignored
  `specs_search_root`, no per-command exit-code contract,
  verifier-policy-independent interaction drafts, pending approvals omitted
  from `check next`, unverifiable constraint IDs, a stale doctor message about
  manifest generation, and no distinct compile-time evidence kind. A dangling
  `evidence_links` entry can still be staged, although approval rejects it at
  G4. Closure and degradation draft templates now exist, but their bundled
  schemas have no documented local inspection path.
- **Impact:** Agents can receive misleadingly clean doctor output, fail to
  identify a human approval step, or stage artifacts that only fail later in
  approval. These are intake and diagnosis gaps; they do not establish that the
  Rust implementation is incorrect.
- **Status:** open / partly resolved, per finding. The exact outputs and
  expected Ligature behavior are listed in the verdict overlay. Confirmed
  fixes include full template discovery and concept/witness approval in 1.2.2,
  plus dangling-link approval checks and protected-write detection in 1.3.4;
  draft-time dangling-link validation remains incomplete.
- **Finding IDs:** `date-ligature-004`, `date-ligature-008`,
  `date-ligature-009`, `date-ligature-018`, `date-ligature-019`,
  `date-ligature-022`–`date-ligature-024`, `date-ligature-027`–`date-ligature-029`,
  `date-ligature-032`, `date-ligature-035`, `date-ligature-040`.
- **Generalizable lesson:** Validate a drafted artifact against its project
  scope and all cross-references before staging it, then make the next action
  explicit when human approval is the only remaining step.

## The live descriptor needs an operator scope decision

- **Category:** Tooling blind spots.
- **C++ construct / upstream location:** Not applicable; this is pilot
  configuration.
- **What the Rust port does instead:** The user-owned descriptor allows
  `docs/*.md` while protecting `docs/reliance-policy.md`.
- **Why:** Those globs overlap, so Ligature 1.3.11 marks the descriptor
  `present-invalid`. `doctor` exits 0, but live `check --json` exits 5 and both
  requested gates stop before evaluating their criteria. No descriptor edit
  was made because narrowing the docs write scope is an operator decision.
- **Impact:** Current live gate state cannot be used to assess the port until
  the descriptor conflict is resolved. A temporary normalized descriptor was
  used only in scratch to run the gate probes.
- **Status:** open; operator decision required.
- **Finding IDs:** `date-ligature-004` (diagnostic asymmetry); the overlap is
  also recorded in the current `check --json` output.
- **Generalizable lesson:** Resolve overlaps between allowed and protected
  globs at the policy boundary before using gate output as a project verdict.

## The assurance report and feature-ledger projection share a configured path

- **Category:** Operator-controlled output-path decision.
- **C++ construct / upstream location:** Not applicable; this is pilot output
  configuration.
- **What the Rust port does instead:** The pilot currently sets
  `report.emit=ci/results/feature_ledger.json`, the same path used by the
  feature-ledger projection. It can generate the projection first and run
  `record-assurance` last, or an operator can authorize a distinct report path.
- **Why:** Ligature 1.3.11 refuses to overwrite an assurance report with the
  feature-ledger projection and gives the safe command order. The manifest is
  under protected `ci/manifest/**`, so changing `report.emit` is outside the
  worker's write authority. `write-set-check` also reports a stray file in
  that protected tree as a violation.
- **Impact:** The two generated artifacts cannot coexist at their current
  canonical path. The order workaround preserves the assurance report; a
  separate path requires an operator decision.
- **Status:** Operator decision required; destructive overwrite is prevented
  in 1.3.11.
- **Finding IDs:** `date-ligature-047`, `date-ligature-051`,
  `date-ligature-052`, `date-ligature-055`.
- **Generalizable lesson:** Assign distinct paths to independently generated
  artifacts, and keep configuration changes behind the authority boundary.

## Verus spec division is Euclidean, not C++ truncation

- **Category:** No faithful Rust or verifier equivalent.
- **C++ construct / upstream location:** `include/date/date.h:2976-3109`
  (`days_from_civil` / `civil_from_days`). The era steps
  `(y >= 0 ? y : y-399) / 400` and `(z >= 0 ? z : z - 146096) / 146097` rely
  on truncating signed division to compute a floor.
- **What the Rust port does instead:** The Creusot port keeps truncating `/`
  in both the code and its logic functions, because Creusot's `Int` division
  truncates. A Verus port can keep the executable form, since Rust `i32`
  division also truncates. Its specs must state the era as plain floor
  division (`y / 400`), because Verus's spec-level `/` on `int` is Euclidean.
- **Why:** Verifier spec-language semantics. Found by the P4-2 probe
  (`analysis/p4-verifier-fit/`).
- **Impact:** Specs cannot be copied between Creusot and Verus. A literal copy
  of the era expression changes its meaning for negative years: for y = −2,
  C++ and Creusot give era −1, while the copied Verus spec gives −2. Verus
  proves the executable truncation trick equal to floor division
  automatically.
- **Status:** open (applies when P4-9, chainlink #163, writes the Verus specs).
- **Finding IDs:** `date-creusot-067`.
- **Generalizable lesson:** Before porting C or C++ integer division into a
  verifier's specs, check that verifier's spec-level division semantics.
  Where the code's trick already computes a floor, state the floor directly.

## Verus needs a raised resource limit for `from_days` and `round_trip`

- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `include/date/date.h:2976-3109`,
  `civil_from_days` and the civil-date round trip it supports.
- **What the Rust port does instead:** P1's Creusot proof carries more than
  20 helper lemmas for these functions (`FUTURE-WORK-round-trip-proof.md`).
  In the P4-2 probe, Verus proves `from_days` against its spec and the round
  trip with no lemmas, but only at `#[verifier::rlimit(200)]`, 20 times the
  default. At the default limit it proves `to_days` and the year-of-era
  exactness lemma unaided.
- **Why:** Z3 has to reason through nine constant divisions and the era and
  year-of-era decomposition in a single query.
- **Impact:** Proof cost only; the obligations do hold. Proofs that depend on
  rlimit can regress on a Verus or Z3 upgrade.
- **Status:** open (applies to P4-9, chainlink #163).
- **Finding IDs:** `date-creusot-068`.
- **Generalizable lesson:** For calendar-style arithmetic with constant
  divisors, a verifier that sends the problem straight to SMT may close in
  one raised-budget query what a pipeline through an intermediate language
  needs a lemma library for. Record the budget as part of the proof, so
  upgrades can be checked against it.
