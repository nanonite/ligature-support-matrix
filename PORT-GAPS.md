# Howard Hinnant/date → Rust/Creusot port gaps

Pinned upstream: `upstream/date` v3.0.5, commit
`179a6b921ccd6179b5b04dce812a89f71a51b4df`. The current Ligature recheck is
1.3.11, bundle SHA-256
`446c87f93aa84c3f538710385706fcf753cd242a1282ba88faa1ad6722cb351f`. Detailed
per-finding evidence is in
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
