# P1 verifier fit: Verus and Kani (P4-2, chainlink #156)

Which of P1's obligations transfer to Verus and Kani, what each verifier
needs, the likely blockers, and the crate layout. This feeds cells A2
(P4-9, #163) and A3 (P4-10, #164) of `VERIFIER-MATRIX.md` at the workspace
root.

The pilot itself was not changed. The claims below rest on small probes run
on scratch copies. `probes/replay.sh` reruns them all (about 2 minutes) and
checks every expected result; `probes/logs/` holds the committed run.

## Summary

- **Every one of the 9 obligations transfers to both verifiers.**
- **Verus: no lemma library needed in the probe.** Verus proved the two
  hardest obligations (`from_days` against its spec, C002, and the round trip,
  C007) with no lemmas, given a raised resource limit. It also proved
  `to_days` with its full spec and range, and the year-of-era exactness lemma,
  with no help at the default limit. P1's Creusot proof carries more than 20
  helper lemmas for the same functions.
- **Kani: the existing crate works unchanged.** Kani compiles P1's
  Creusot-annotated crate as it is and proves the round trip over the entire
  valid date domain in about 26 seconds. The code has no loops, so there are
  no unwind bounds.
- **"Nonlinear arithmetic" is not really a blocker for P1.** Every product in
  the algorithm has a constant factor, and every division and modulo has a
  constant divisor. That is linear integer arithmetic, which Z3 handles.
- **Verus blocker 1: division semantics.** Verus's spec-level division rounds
  toward negative infinity, while C++ and Creusot truncate toward zero. The
  specs must be restated, not copied (date-creusot-067).
- **Verus blocker 2: resource limit.** `from_days` and `round_trip` need
  `#[verifier::rlimit(200)]` or a few helper lemmas (date-creusot-068).
- **Kani blocker: C002 can't be stated as written.** Its spec is an
  unbounded-integer logic function. A harness can only compare against
  executable Rust, so the Kani version of C002 is a weaker claim (below).

## What P1 proves today

- **Scope.** `WP-DATE-CREUSOT` pins 9 obligations: `Month.C001`,
  `Weekday.C001-C003`, `Year.C001-C002`, `YearMonthDay.C002` (`from_days`),
  `YearMonthDay.C007` (`round_trip`) and `YearMonthDayLast.C001`. The concept
  specs also hold `YearMonthDay.C001/C003/C005` and `YearMonthDayLast.C002`.
  Those have contracts in the code but sit outside the work-package scope.
- **Creusot result.** `cargo creusot` reports `Proved (93 files)`; G14 closes
  `date-creusot-core` as deductive under Ligature 1.4.2.
- **Shape of the code** (`rust/date-creusot-core/src`, 1,750 lines):
  - no loops, generics, `unsafe` or heap;
  - inputs are an `i16` year (−32768 excluded), a `u8` month in 1-12, a `u8`
    day in 1-31, and an `i32` day count;
  - the arithmetic is `i32` with constant multipliers (146097, 365, 153, 400,
    5) and constant divisors (400, 146097, 1460, 36524, 146096, 365, 153, 5,
    4, 100, 7).
- **Where the proof effort went.** `year_month_day.rs` holds 38 `#[logic]`
  functions. Most of them are the Neri & Schneider exactness lemmas behind
  `round_trip` (see `FUTURE-WORK-round-trip-proof.md`).

## Probe results

| Probe | Result | What it shows |
|---|---|---|
| `verus/div.rs` | 4 verified | Verus spec `int` division is Euclidean: `(-1)/400 == -1`, `(-1)%400 == 399`. Exec `i32` division truncates: `-1/400 == 0`. `(era*146097 + doe)/146097 == era` proves with no hint |
| `verus/yoe.rs` | 2 verified, default rlimit | Year-of-era exactness, which P1's Creusot proof states with seven helper functions and a case split, proves unaided |
| `verus/civil.rs` | 2 verified, 2 errors | `to_days` with its full spec and the C005 range proves at the default limit. `from_days` and `round_trip` exceed the default resource limit |
| `verus/civil_rlimit.rs` | 4 verified | The same file with `#[verifier::rlimit(200)]` on those two: everything proves, no lemmas |
| `verus/mutant_spec.rs`, `mutant_rt.rs` | fail as intended | A wrong constant in the spec, or a negated round-trip claim, is refuted, so the proof is not vacuous |
| `kani/round_trip_full_domain` | SUCCESSFUL, ~26 s | C007 holds for every valid date, checked on P1's crate unchanged |
| `kani/round_trip_reachable` | cover SATISFIED | The validity assumption admits real dates (29 February 2000) |
| `kani/round_trip_mutant` | FAILED as intended | The negated claim is refuted |

Tools: Verus 0.2026.05.24.ecee80a (toolchain 1.95.0, in the `crypto-mixed`
shell) and cargo-kani 0.67.0 (in the `date-creusot` shell). The Verus probe
restates the algorithm on plain integers instead of P1's newtypes; the Kani
probe uses the real crate.

## Per-obligation fit

| Obligation | Claim | Verus | Kani |
|---|---|---|---|
| `Month.C001` | `ok()` iff 1 ≤ m ≤ 12 | Direct | Exhaustive over `u8` |
| `Year.C001` | `ok()` iff y ≠ −32768 | Direct | Exhaustive over `i16` |
| `Year.C002` | Gregorian leap rule | Constant-modulus arithmetic; automatic expected | Exhaustive over `i16` |
| `Weekday.C001` | `weekday_from_days(z)` is (z + 4) mod 7, Euclidean | Spec `%` is already Euclidean, so the spec gets simpler | Exhaustive over `i32`; two modulo operations |
| `Weekday.C002` | weekday ≤ 6 | Follows from C001 | Follows from C001 |
| `Weekday.C003` | ISO encoding maps 0 to 7 | Direct | Direct |
| `YearMonthDayLast.C001` | `day()` is the Gregorian month length | Direct | Exhaustive over year × month |
| `YearMonthDay.C002` | `from_days(dp)` equals `civil_from_days(dp)` | **Proved in the probe** at rlimit 200, with the spec restated in floor division | **Weaker claim.** The spec is an `Int` logic function. A harness can compare against an `i64` copy of the same algorithm, which checks overflow and casts but not the mathematics. Or C002 is carried by C007 plus range checks |
| `YearMonthDay.C007` | `round_trip()` is true for every valid date | **Proved in the probe** at rlimit 200 | **Proved in the probe**: full domain, ~26 s |

## What each cell needs

### A2: P1 on Verus (P4-9, #163). Expected: deductive, closes

- **A separate crate.** It uses Verus 1.95.0 with `vstd` and `verus!`. It
  cannot share the Creusot crate, which needs nightly-2026-04-21 and
  `creusot_std`.
- **Its own single-verifier workspace.** This follows the matrix's Axis A
  layout: its own Git root, linked as a submodule.
- **A Nix shell with Verus.** Verus is in the `swisstable-verus`,
  `crypto-mixed` and `default` shells, not in `date-creusot`. A new root
  either uses one of those or needs a flake change, which is the operator's
  call.
- **Five concept specs restated.** Each spec declares one `verifier` and
  writes its `logic` in that verifier's syntax. The IDs and English carry
  over; the logic is rewritten with `verifier: verus`. Stage 3 approval
  follows.
- **Ten interactions re-declared.** Their reliances must accept
  `verus-deductive-check`: under the reliance policy (#151), the owner's
  evidence kind has to be in the accepted set.
- **Specs in floor division** (date-creusot-067). The executable code keeps
  the C++ truncation trick, and Verus proves the two equal automatically.
- **A proof budget** (date-creusot-068). Either `#[verifier::rlimit(200)]` on
  `from_days` and `round_trip`, or a few helper lemmas. `year_of_era_exact`
  already proves unaided and is the natural first one. Proofs that depend on
  rlimit can regress on a Verus or Z3 upgrade, so record the budget with the
  proof.
- **Ligature intake.** `record-assurance --verus-json`, with the proof-note
  markers (#126) and the stale-report check (#127) in mind.
- **Oracle parity.** P1's oracle suite (`oracle/rust-check`) has to run
  against the new crate.

P1 on Verus is also **the cleanest test of matrix question Q1**: does a pure
Verus closure get CG3 VERIFIED? The code has no generic functions at all, so
if G14 withholds CG3 here, that cannot be about generics. A scratch P1-Verus
workspace is a good first probe for P4-5 (#159).

### A3: P1 on Kani (P4-10, #164). Expected: bounded, released under a CG3 record

- **No new crate needed to verify.** Kani compiles the Creusot crate as it
  is, because the `creusot_std` macros do nothing outside `cfg(creusot)`. So
  `#[cfg(kani)]` harnesses can sit on the same code. For a clean Axis A cell
  the code is still copied into its own single-verifier workspace, so that
  Creusot and Kani records never share a workspace (matrix Q5).
- **One harness per obligation**, mapped with `--kani-harness
  <obligation>=<harness>` and `--kani-crate`. Every input fits in `i16`, `u8`
  or `i32`, and the code is loop-free, so every harness can cover its whole
  input domain. The round trip, the heaviest, takes about 26 seconds.
- **Concept specs restated** with `verifier: kani` and Rust-expression logic,
  as P3's `cha_cha20.json` does. The interactions accept
  `kani-bounded-model-check`.
- **C002 needs an operator decision on its wording.** Choose between the
  `i64` reference comparison and carrying it through C007 plus range checks.
  Either way the Kani claim is narrower than the deductive one.
- **A CG3 record is still required.** G14 requires one for every Kani closure
  (matrix section 1), even though P1 has no generic code for CG3 to describe.
  That is documented Ligature behaviour. P4-10 should record it as a finding,
  not escalate it.

### For both cells

Pin the same 9 obligation IDs as the Creusot cell, so the three results
compare like for like. The 4 out-of-scope constraints can be added later. The
Verus probe already proves C001 and C005 for `to_days`.

## Findings recorded

- `date-creusot-067` (verus, friction): spec-level division is Euclidean, so
  P1's truncating-division specs cannot be copied into Verus.
- `date-creusot-068` (verus, friction): `from_days` and `round_trip` exceed the
  default rlimit without lemmas, and prove at rlimit 200.

Both are also in `PORT-GAPS.md`. The Kani results are positive and are not
limitations. The C002 wording question and the CG3 record are predictions for
P4-10, to be recorded there once observed.
