# Future work: proving `YearMonthDay::round_trip` in Creusot

**Status: RESOLVED (chainlink `#88`).** `cargo creusot` now reports
`Proved (93 files) ✔`: 93 proof files, 126 `vc_*`/`refines` goals, 202 proved
SMT calls, **0 unproved**. `vc_round_trip` is 5/5 sub-goals, every one closed
by `alt-ergo` in under 20 ms, at the *default* `why3find.json` budget
(time 1 / depth 6 — unchanged). The Neri & Schneider exactness lemmas this
file asked for are written and proved in
`rust/date-creusot-core/src/year_month_day.rs`:
`year_of_era_from_doe_exact` (the deep one, with the mixed-radix helpers
`century_of_era_year`, `era_quotients`, `div_365_of_nonneg_digit`,
`div_365_of_year`, `div_365_of_era_end`, `valid_era_day`, `era_year_start`),
plus `era_of_days`, `month_day_from_doy_exact` (with its
`_31`/`_30`/`_feb` month-class helpers and `doy_from_civil`),
`doy_of_civil_bounds*`, `yoe_of_era_year`, `leap_era_day`,
`div_4/100/400_era_shift`, `civil_parts`, and the composite
`days_civil_round_trip` / `civil_round_trip_holds`.

Three findings from the work are worth reading before the rest of this file,
because two of them contradict what this file assumed:

1. **The lemma shape suggested below is FALSE, not merely hard.** Stated over
   the whole box, "for `yoe ∈ [0,399]` and `doy ∈ [0,365]`,
   `year_of_era_from_doe(yoe*365 + yoe/4 - yoe/100 + doy) == yoe`" is wrong:
   the forward map is not injective there, because `(yoe, 365)` and
   `(yoe+1, 0)` share a day-of-era whenever era-year `yoe+1` is not a leap
   year. The proved side condition is `valid_era_day(yoe, doy)` — "(yoe, doy)
   is a real day of era-year yoe" — and an exhaustive 146,400-pair brute force
   confirms it is **exactly** tight: it selects precisely the 146,097 pairs on
   which the recovery inverts, which is also the length of a 400-year era.

2. **The proof went through as soon as the digits were named.** Writing
   `yoe = 4q + r` with `q = 25h + u` turns the forward offset into the
   mixed-radix number `doe = 36524*h + 1461*u + 365*r + doy` (radices
   4, 25, 4, 366), and the recovery's three `doe/d` terms are then just the
   three carry counters. `era_quotients` supplies them from a case split on a
   single carry value, and after that every sub-goal is plain linear
   arithmetic. This is the reusable part: the argument did not need more
   prover budget, only the right decomposition made explicit.

3. **A missing `#[ensures]` was a genuine second blocker.** `to_days_bounded`
   — the function `round_trip`'s body actually calls — stated only the
   *range* of the day count, never the `days_from_civil` identity its own body
   computes, so the postcondition and the computed day count were unconnected
   terms and the goal was *unprovable* rather than true-but-hard. Adding
   `#[ensures(result.0@ == days_from_civil(self.year.0@, self.month.0@, self.day.0@))]`
   alongside the range `#[ensures]` is necessary: with it removed, both
   `vc_round_trip` and `vc_to_days_bounded` fail again. Two further mechanical
   changes were needed as well, both for the provers' benefit rather than the
   mathematics': `CivilView` (a named record in place of the `(Int, Int, Int)`
   civil triple, since record equality on a generated tuple type cannot be
   decomposed — the same limitation that already forced `YearMonthDayView`),
   and a `bool` wrapper `civil_round_trip_holds` for the contract to name, so
   that `days_civil_round_trip`'s specification actually reaches `round_trip`'s
   VC.

The 50,000-case brute-force differential check and the oracle's 143-case suite
both still pass.

The rest of this file is kept as the record of the original investigation,
including the two approaches tried and ruled out and the status line as it
stood then; the "current status" numbers and the suggested lemma shape quoted
below are superseded by the section above. Cross-references:
`findings/limitations.jsonl` records `date-creusot-038` (fixed),
`date-creusot-039` (this gap), `date-creusot-059` (its resolution, with the
counterexamples that corrected two intermediate lemma statements) and
`date-creusot-060` (the pinned dev shell can no longer be built; see the
`nix develop` note below). Chainlink issues `#15`/`#20` (closed), `#88` (this
work), and `#18` (Stage 8C — read this file when assessing this pilot's
`closure_kind`).

## The one-sentence summary

`round_trip`'s proof obligation is **true** (verified two independent ways, outside Creusot) but **Creusot's automatic search cannot close it** without a hand-written lemma — because the correctness argument for Howard Hinnant's calendar algorithm is genuinely nontrivial integer-division reasoning, formalized properly for the first time in a 2021 paper (Neri & Schneider) that postdates the C++ code by years.

## Where this lives in the crate

`rust/date-creusot-core/src/year_month_day.rs`:
- `days_from_civil(y, m, d) -> Int` — the forward conversion (a `#[logic]` twin of the program function `to_days`).
- `civil_from_days(z) -> CivilView` — the inverse conversion (a `#[logic]` twin of the program function `from_days`). It used to return `(Int, Int, Int)`; it returns the named record now, because every contract relating a day count to a calendar date has to decompose that result and the provers cannot decompose a record equality on a generated tuple type.
- `YearMonthDay::round_trip(&self) -> bool` — states and **now fully proves** `civil_from_days(days_from_civil(y,m,d)) == (y,m,d)` for `self.ok_logic()` inputs.

`rust/date-creusot-core/src/year_month_day_last.rs`:
- `month_length(m, y) -> Int` — the month-length table. Its `#[ensures]` now restates the table, which adds no axiom but makes it visible across the module boundary (`month_day_from_doy_exact` has to read it).
- `month_day_from_doy(doy) -> (Int, Int)` and `year_of_era_from_doe(doe) -> Int` — the two recovery sub-formulas `round_trip`'s proof composes through. Both carry `#[ensures]` **range** facts; the **exactness/uniqueness** facts they lack are supplied by the separate lemmas listed at the top (their bodies still live in `year_month_day.rs`).

Run `cargo creusot` from `rust/date-creusot-core/` (inside `nix develop ..#date-creusot`) to see current status; as of the resolution it reports `Proved (93 files) ✔`. It requires the *full* `cargo creusot`, not `--only prove`, to pick up any source edit — `--only prove` reuses cached coma and silently ignores changes. Note that as of `date-creusot-060` the pinned dev shell no longer builds (cvc5-1.3.1's fetch of a GitHub-hosted patch 404s); the results quoted here were obtained with the other intact generation of the same `creusot-wrapped 0.12.0-dev` in the local store, which is the `tool_path` already recorded in this pilot's earlier findings.

## The algorithm, briefly

Hinnant's `date.h` (the C++ we're porting) converts `(year, month, day) ↔ epoch day count` via a trick: shift the year boundary to **March 1** instead of January 1, so the leap day (Feb 29) always lands at the *end* of an "era-year" rather than in the middle. That turns the usual leap-year special-casing into a clean division formula, at the cost of several nested integer divisions:

```
days_from_civil(y, m, d):
  y'   = y - (1 if m <= 2 else 0)                    # shift Jan/Feb into the prior "era-year"
  era  = (y' if y' >= 0 else y'-399) / 400            # 400-year era, sign-adjusted for trunc-div
  yoe  = y' - era*400                                 # year-of-era, in [0, 399]
  doy  = (153*(m>2 ? m-3 : m+9) + 2)/5 + d - 1         # day-of-era-year, in [0, 365]
  doe  = yoe*365 + yoe/4 - yoe/100 + doy               # day-of-era, in [0, 146096]
  return era*146097 + doe - 719468                    # shift to the 1970 epoch

civil_from_days(z):
  z    = z + 719468                                   # undo the epoch shift
  era  = (z if z >= 0 else z-146096) / 146097
  doe  = z - era*146097
  yoe  = (doe - doe/1460 + doe/36524 - doe/146096)/365 # <-- the hard inversion
  y'   = yoe + era*400
  doy  = doe - (365*yoe + yoe/4 - yoe/100)
  (m,d) = month_day_from_doy(doy)                      # another division-based inversion
  y    = y' + (1 if m <= 2 else 0)
  return (y, m, d)
```

Every "recovery" step inverts a forward step built from floor/truncating division — and integer division doesn't distribute over addition (`(a+b)/c ≠ a/c + b/c` in general), so proving these compose back to the identity is genuinely subtle. The `yoe` recovery line is the crux: it has to exactly invert `doe = yoe*365 + yoe/4 - yoe/100 + doy` for `yoe ∈ [0,399]`, which is *not* a linear function of `yoe` because of the `/4` and `/100` terms.

## Why Neri & Schneider matters here

**Cassio Neri and Lorenz Schneider, "Euclidean affine functions and their application to calendar algorithms," Software: Practice and Experience, 2021.**

Hinnant's original derivation is correct — it's been in production for years, extensively tested, and is the basis for C++20 `<chrono>` calendar support. But it was arrived at by careful construction and testing, not by a general formal argument. Neri & Schneider retroactively supply that argument: they define a class of "Euclidean affine functions" (affine maps composed with floor division) and prove exact theorems for when such a function has an exact inverse, given conditions on its coefficients relative to the modulus. Hinnant's era/day-of-era/day-of-year recovery formulas are specific instances of that general class. The paper is, in effect, the reusable lemma library a machine proof needs — the facts that have to be *supplied* to Creusot rather than discovered automatically.

## What's already been tried (don't repeat these)

1. **Raising the proof-search budget.** `why3find.json`'s `time`/`depth` were bumped from `1`/`6` to `5`/`12` as a quick experiment. Result: *worse*, not better (`7/10` failing instead of `5/7`) — the `split_vc` tactic just splits differently at higher depth, it doesn't converge. Reverted. **Conclusion: this is not a "give it more time" problem.**
2. **Inline `proof_assert!` hints.** An earlier attempt (recorded in chainlink `#12`'s history, not this file's author) tried asserting intermediate range facts (e.g. `doe ∈ [0,146096]`) directly inside a program-function body via `proof_assert!`. Even the *first* such assertion wasn't automatically dischargeable, and it cascaded into more failing goals elsewhere. **Conclusion: a bare hint isn't enough; the underlying fact itself needs to be established as a proven lemma first.**

## What actually needs to happen

Creusot has no separate "inject an axiom" mechanism outside the crate — a lemma *is* a `#[logic]` function with an `#[ensures]`, written as ordinary crate source, exactly like `year_of_era_from_doe` and `month_day_from_doy` already are. What's missing is a **stronger** fact than either currently states:

- `year_of_era_from_doe`'s current `#[ensures]` only pins down a *range*: `result ∈ [0,399]` and the leftover remainder `∈ [0,365]`. It does **not** state that this is the *unique* such `yoe`, or that it recovers the exact `yoe` used to construct its input `doe` in the first place. That stronger fact is what `round_trip` needs.
- Likely shape of the missing lemma: something like *"for `yoe ∈ [0,399]` and `doy ∈ [0,365]`, `year_of_era_from_doe(yoe*365 + yoe/4 - yoe/100 + doy) == yoe`"* — i.e. exactness of the forward-then-recover round trip at the `yoe` level, proven directly (likely via case-split on `yoe mod 4` and `yoe mod 100`, or by leaning on Neri–Schneider's general theorem's hypotheses and checking Hinnant's constants satisfy them) rather than composed from the existing range-only fact.
- Similarly for the era recovery (`(era*146097 + doe)/146097 == era` given `doe ∈ [0,146096]`) and the `month_day_from_doy` inversion, though these are likely easier — the year-of-era step is the deep one.

**Recommended approach for whoever picks this up:**
1. Read the Neri & Schneider paper's treatment of the `year_of_era`-equivalent step directly (they cover exactly Hinnant's construction as a worked example) — don't try to re-derive the case analysis from scratch.
2. Write the exactness lemma as a new `#[logic]` function near `year_of_era_from_doe` in `year_month_day_last.rs`, with its own `#[ensures]` stating the round-trip identity, and a Pearlite proof body (likely needing an explicit case split, not a one-line computation).
3. Once that lemma exists and is referenced (called) from `round_trip`'s reasoning path, re-run `cargo creusot` (full, not `--only prove`) and check whether `vc_round_trip` closes or at least shrinks.
4. If Why3/Creusot's automatic tactics still can't finish even with the lemma in scope, consider `why3find ide`/`why3find prove -i` (opens the Why3 IDE on the failed goal) for interactive proof — but note `why3find` invoked standalone needs `CREUSOT_DATA_HOME` exported manually (`cargo-creusot`'s wrapper sets this internally; calling `why3find` directly does not inherit it) and the `creusot` package registered, which wasn't successfully worked out in this session — expect to spend some time on that plumbing too.

## Verification checklist once a lemma is written

- `cargo creusot` (full) reports `vc_round_trip` fully proved (or record the new partial count if not fully closed).
- Re-run the brute-force check below to confirm nothing regressed (it should already pass — this is a sanity check on the *lemma statement*, not the implementation):
  ```python
  # from the #15 investigation — 50000-case brute force, C-style truncating division
  def tdiv(a,b):
      q = abs(a)//abs(b)
      return q if (a<0)==(b<0) else -q
  # ... (see chainlink #15's closing comment for the full script)
  ```
- `oracle/rust-check`: `cargo test --release` still reports `0 failed`. (Note: the
  suite is **143** cases, not the 150 quoted above — `oracle/cases.jsonl` has
  143 lines and each becomes one generated test, so `143 passed; 0 failed` is
  the correct current figure and the "150" is a stale number from
  `date-creusot-001`. Unchanged by this work either way.)
- Update `findings/limitations.jsonl`: mark `date-creusot-039` as resolved (append a new record referencing it, per this project's append-only convention — don't edit the original line), and update this file's status line at the top.
- If `#18` is still open when this work happens, its `gate-g14`/`validate-closure` step should reflect the change (this pilot may move from "degradation record" to genuinely `closure_kind: deductive` for this obligation).

All five items above are done; the checklist is kept verbatim as the record of
what was verified. The resolution is appended as a new `date-creusot-*` record
in `findings/limitations.jsonl` (the original `date-creusot-039` line is
untouched, per the append-only convention).

## Diagnosis — how the real cause was found

The gap resisted the approaches above because the premise behind all of them
was wrong: the remaining sub-goals were assumed to be *true but hard for
search*, when they were in fact **not provable at all**. Two techniques
settled that, both far cheaper than further lemma-writing:

1. **Replay the emitted VC outside Creusot.** `cargo creusot` writes each
   module's Coma to `rust/date-creusot-core/verif/**/<name>.coma`, and
   `cargo-creusot` shells out to `why3`/`why3find` with the load path
   `.../share/why3find/packages/creusot` and the generated
   `~/.config/creusot/why3.conf`. Assembling a single file from the crate's
   own `.coma` output and running
   `why3 prove -a compute_specified -a split_vc -P alt-ergo -P z3 -P cvc5 -P cvc4`
   on it reproduces `vc_round_trip`'s split exactly, in seconds, with no Rust
   rebuild. `why3 prove ... -o <dir>` then dumps each sub-goal as a standalone
   `.ae`/`.smt2` task — which is what makes the *hypotheses* of a sub-goal
   readable, rather than inferring them from the sub-goal count.
2. **Read the sub-goals' hypotheses.** The dumped sub-goals come with
   `(assert (ok self))`, the `from_days` postcondition
   (`civil_from_days (tqtint2 result)`) and the `to_days_bounded` postcondition
   — and `to_days_bounded`'s is only the range
   `-12687428 <= tqtint2 result <= 11248737`. Nothing anywhere in the context
   says `tqtint2 result` *is* `days_from_civil (y, m, d)`. So the goal asks the
   provers to derive the calendar round trip from a day count that is
   unconstrained within a 24-million-wide window, and no prover can do that —
   it is a false statement, not a hard one. That is also why raising the search
   budget (attempt 1 above) made things *worse* rather than better: it was
   never a search problem.

The lesson worth keeping: when a VC "should" be provable, dump the goal and
read its hypotheses before writing lemmas. A missing `#[ensures]` on a
*callee* presents exactly like a missing lemma, because a callee sees only its
own contract — here `to_days_bounded` computed the right thing but never said
so, while its one-line body `self.to_days()` had the proof sitting right
there in `to_days`'s contract.

