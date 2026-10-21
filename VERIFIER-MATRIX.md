# Verifier matrix (P4-1, chainlink #155)

Draft for the P4-7 consensus checkpoint (#161). It lists every verifier
configuration P4 will test, which port covers it, the closure outcome
Ligature should report, and the evidence that counts as covered. No code.

Ligature 1.4.2 (bundle `c4d989f3…`). The rules in section 1 come from the
bundled schemas (`ligature schema show closure-profile`,
`degradation-record`, `project-descriptor`, `interaction`), the bundled CLI
contract (`ligature contract`), and the pilots' own artifacts. Where they
leave an outcome open, the row says so and points to a question in section 6
for the P4-5 probes (#159).

## 1. How Ligature judges a configuration

**Closure kinds.** A closure profile declares one of three kinds:

| Kind | Meaning (closure-profile schema) |
|---|---|
| `deductive` | Creusot- or Verus-owned; universal over inputs, modulo SMT completeness and trusted specs |
| `bounded` | Kani-owned; holds only within unwind/harness bounds and enumerated monomorphizations |
| `partial` | The cluster cannot reach full deductive closure and says so, instead of rounding up to `deductive` or down to `bounded` |

The kind is recomputed from the evidence in the transitive closure. A
`deductive` profile over a closure containing any Kani result is a G17 hard
error. A degradation record cannot excuse it; the profile has to be
re-declared `bounded` or `partial` (probe #23, on Ligature 1.1.1).

**Closure conditions.** Every condition must hold for a cluster to close.
A cluster that fails one can only be released as *degraded*, under a
reviewed degradation record that names the condition, a ceiling and a
tracking issue. It is then never reported as closed.

| Condition | Capability gap named by the schema | How Ligature decides it | Ceiling when degraded |
|---|---|---|---|
| `single_verifier_system` | CG1 (cross-verifier composition has no soundness theorem) | Recomputed from the evidence kinds in the closure | `harness-tested` |
| `owning_verifier` | none | Recomputed from the closure's achieved records; a mismatch is G17 | n/a |
| `protocol_class_all_pairwise` | none (G15 artifact or protocol-debt record) | Every bridge in the closure is `pairwise` | n/a |
| `unresolved_indirect_calls_at_or_above_medium` | none | Read from the R1/G16 C-static reports; must be 0 | n/a |
| `generic_callees_type_universal_or_creusot_owned` | CG3 (Kani verifies generics per monomorphization) | Recomputed when the closure's records settle it; otherwise it blocks unless a CG3 record names it | `per-instantiation` |
| `transitive_assumptions_within_policy` | none | Every assumption in any achieved record in the closure is allowed by the cluster's trust policy | n/a |
| `scc_wellfoundedness_discharged` | CG6 (mutual satisfaction is not soundness) | `not-applicable` when acyclic; otherwise every SCC needs a reviewed `scc_discharges` entry | n/a |

The degradation-record schema also lists CG2, CG4 and CG5 (CG5's ceiling is
`human-risk-acceptance`) without tying them to a condition. No current port
or P4 issue targets them (section 5).

**Rules that decide the composition rows:**

- **The closure crosses cluster boundaries.** A required guarantee provided
  by a work package outside the cluster is followed and checked
  (closure-profile `work_packages`). A cluster that relies on another
  verifier's cluster therefore has that verifier's evidence in its own
  closure, which makes `single_verifier_system` false.
- **Every Kani-owned cluster needs a CG3 record.** CG3 is only settled when
  no closure record is a Kani result, so every Kani closure is released as
  degraded at `per-instantiation`. P3 is the live example (#135).
- **CG3 is judged across the whole workspace.** Per the contract (#93), the
  VERIFIED verdict needs every record in every readable assurance ledger,
  and every guarantee harness in `ci/manifest`, to be Creusot's. Anything
  else withholds it. The schema's wording is narrower ("none of them is a
  Kani result"). The schema also defines `deductive` as Creusot- *or*
  Verus-owned, and Verus proves generic code for every type, so a Verus-only
  closure should get CG3 VERIFIED. If G14 withholds it there, Ligature is
  failing at what it claims (Q1). For shared workspaces the workspace-wide
  scope is documented behaviour, so its effect is measured, not escalated
  (Q5).
- **Reliance evidence follows the owner (#151).** A reliance's accepted
  evidence kinds must come from the callee cluster's owner or a declared
  `verifier_policy.supporting` verifier, and the owner's kind must stay in
  the set. Supporting evidence cannot substitute for the owner. For an
  explicitly `cross-verifier` edge, compatible intake does not establish
  composition; G14's CG1 check stays authoritative.
- **A degradation record carries one `capability_gap` and one `ceiling`**,
  but `failed_conditions` is an array (Q3).

## 2. Outcome vocabulary used below

| Code | Ligature result |
|---|---|
| **D** | Closes, `deductive` |
| **B/CG3** | Released degraded, `bounded`, ceiling `per-instantiation` (every Kani-owned cluster) |
| **P** | Declared `partial`; whether it closes depends on the conditions, as for D |
| **CG1** | Released degraded, ceiling `harness-tested` (closure spans more than one verifier) |
| **G17** | Blocked: declaration contradicts the recomputed closure |

## 3. Axis A: one port, one owning verifier

Each cell is one cluster owned by one verifier. Whether a port can be
completely defined and proved by that one verifier is a question about the
port: what the C++ code does and how the Rust design expresses it. The fit
analyses (P4-2 to P4-4) answer it. In principle every port can be done with
any one of the three verifiers, so each cell's expectation is that verifier's
full single-verifier result (D for Creusot and Verus, B/CG3 for Kani). A
cell drops to P only where its fit analysis shows part of the design is out
of that verifier's reach. Ligature's rules decide how a result is reported,
not whether the cell should exist.

**Layout recommendation:**
run each non-done cell in its own single-verifier Ligature workspace, not as
a second cluster inside the existing pilot. Per the workspace-wide CG3 rule,
adding a Verus or Kani cluster to `date-creusot` would withhold CG3 from P1's
closed Creusot cluster. That is an Axis B result (B5) and would contaminate
the Axis A cell. P4-5 confirms whether the rule fires (Q5); P4-6 (#160)
chooses the layout.

| Cell | Port | Owner | Issue | State | Expected | Risks to settle in the fit analysis |
|---|---|---|---|---|---|---|
| A1 | P1 date | Creusot | #18 (probes #19, #22) | **done** | D: G14 closes, 9 pinned obligations, CG3 VERIFIED | None open. 2 known out-of-set write-set findings (`.gitignore`, `PORT-GAPS.md`) |
| A2 | P1 date | Verus | P4-9 #163 | open | D. A CG3 refusal here would be a Ligature defect (Q1) | Fit done (P4-2 #156, `date-creusot/analysis/p4-verifier-fit/`). All 9 obligations transfer. Probes prove `from_days` and the round trip with no lemmas at rlimit 200. Specs must be restated in floor division (date-creusot-067, -068). No generic code, so it is the cleanest Q1 probe |
| A3 | P1 date | Kani | P4-10 #164 | open | B/CG3 | Fit done (P4-2 #156). Loop-free: the round trip is proved over the full valid domain on the unchanged crate in ~26 s. C002 needs an operator decision on its Kani wording. A CG3 record is required even with no generic code |
| A4 | P2 SwissTable | Verus | P4-8 #162 | open: 7 concept specs still drafts, no work packages | D: the intended Verus-only port. P only if unsafe storage or SIMD probing stay out of reach | Heaviest generics of any port, so it is the main test of Q1. Blocked first by 462 pending R1/G16 decisions (`swisstable-ligature-015`) and a stale C-static report (section 7); P4-3 #157 |
| A5 | P2 SwissTable | Creusot | P4-11 #165 | open | D: the one owner whose generic callees settle CG3 positively. P if unsafe slots or SIMD are out of reach | P4-3 #157 |
| A6 | P2 SwissTable | Kani | P4-12 #166 | open | B/CG3 | Kani's fit for unsafe slots and SIMD group probing; per-monomorphization only; P4-3 #157 |
| A7 | P3 crypto | Creusot | P4-13 #167 | open | D, or P if Poly1305's 130-bit arithmetic resists | Wrapping and rotate arithmetic, byte buffers; P4-4 #158 |
| A8 | P3 crypto | Verus | P4-14 #168 | open (deferred at #43) | D (Q1) | P4-4 #158 |
| A9 | P3 crypto | Kani | #44, #134, #135, #49 | **done** | B/CG3: `crypto-kani` released under the accepted CG3 record, 6/6 obligations, 3/3 bridges, oracle 2580/2580 | None open |

## 4. Axis B: combining verifiers

Port choice: **P3 crypto** is the main vehicle. It is the smallest port, its
oracle has 2580 tests, and its primitives-to-AEAD layering gives a natural
cross-cluster edge: the ChaCha20Poly1305 AEAD relies on ChaCha20 and
Poly1305. P1 (YearMonthDay over Year/Month/Day) is the second witness where
a row needs one.

| Row | Configuration | Issue | Port | Expected | Question |
|---|---|---|---|---|---|
| B1a | Creusot owner, Kani supporting | P4-15 #169 | P1 | Reliance accepts both kinds only with Creusot's kept (#151). If the Kani records enter the closure: G17 unless re-declared `bounded`/`partial`, plus CG1 | Q2 |
| B1b | Verus owner, Kani supporting | P4-15 #169 | P3 | As B1a, with Verus | Q2 |
| B1c | Kani owner, Creusot or Verus supporting | P4-15 #169 | P3 | B/CG3 for the owner; CG1 if the supporting records enter the closure | Q2 |
| B2a | Creusot + Kani in one closure | P4-16 #170 (supersedes #50) | P1 | G17 while declared `deductive`; after re-declaring `bounded`: CG1 and CG3. Re-runs #23 on 1.4.2 | Q3 |
| B2b | Verus + Kani in one closure | P4-16 #170 | P3 | As B2a | Q3 |
| B2c | Creusot + Verus in one closure | P4-16 #170 | P3 | Kind can stay `deductive` (both deductive); CG1. CG3 should hold, since both verifiers prove generics for every type (Q1). Which owner G14 recomputes is open | Q1, Q3, Q6 |
| B3 | Two single-verifier clusters, cross-verifier edge carried by a boundary contract | P4-17 #171 (supersedes #51) | P3 | If the caller requires the callee's guarantee, the callee's evidence is in the caller's closure: CG1 as in B2. The split only isolates the caller if the edge is a trusted assumption under its trust policy | Q4 |
| B4 | Six directed cross-cluster pairs | P4-18 #172 | P3 (P1 for C↔V) | See table below | Q1, Q4 |
| B5 | All three verifiers in one workspace: ChaCha20, Poly1305 and AEAD each owned by a different verifier | P4-19 #173 | P3 | Callee clusters keep their single-verifier outcome unless the workspace-wide CG3 rule withdraws D; the AEAD cluster gets CG1 plus its owner's CG3 | Q5 |

**B4 detail: caller cluster → callee cluster.** The callee keeps its Axis A
outcome, subject to Q5.

| Pair | Expected for the caller |
|---|---|
| Creusot → Verus | CG1; kind stays `deductive`; CG3 should hold (Q1) |
| Creusot → Kani | G17 until re-declared `bounded`/`partial`; then CG1 and CG3 |
| Verus → Creusot | CG1; CG3 should hold (Q1) |
| Verus → Kani | G17 until re-declared; then CG1 and CG3 |
| Kani → Creusot | Already `bounded`; CG1 and CG3 |
| Kani → Verus | Already `bounded`; CG1 and CG3 |

**Toolchain constraint (P4-6 #160).** Creusot (nightly-2026-04-21,
`creusot_std`) and Verus (1.95.0, `vstd`) need separate crates. Kani
harnesses (`#[cfg(kani)]`) can overlay either. Every B row that pairs Creusot
with Verus therefore spans two crates, and each verifier sees the other's
callee only through a contract it trusts (an `external_body` or equivalent).
That trusted contract is exactly what CG1 refuses to treat as a proof.

## 5. Not exercised by any current port

| Gap | What exercising it needs | Recommendation for P4-7 |
|---|---|---|
| G15, non-pairwise protocols | A bridge or interaction whose protocol is not pairwise, with its protocol-debt record (`approve-pair`) | Synthetic probe on a scratch copy of P3 |
| CG6, cycles between clusters | Two clusters that require each other's guarantees, plus a reviewed `scc_discharges` entry | Synthetic probe: a deliberate mutual reliance between P3's AEAD and Poly1305 clusters |
| CG2, CG4, CG5 | No bundled description beyond the enum and CG5's `human-risk-acceptance` ceiling | Out of P4 scope unless P4-5 finds a verb that produces them |

A fourth C++ project is not needed for any row above. Revisit only if the
fit analyses (P4-2 to P4-4) find a verifier strength that none of the three
ports exercises.

## 6. Open questions for the P4-5 probes

| # | Question | Rows it decides |
|---|---|---|
| Q1 | Confirm that a Verus-only closure gets CG3 VERIFIED, as the schema's definition of `deductive` (Creusot- or Verus-owned) requires. The contract's wording points the other way: CG3 needs Creusot ownership positively, and its Creusot disjunct "remains limited to Creusot ownership" for Verus records. A refusal is an epic #1 escalation, because Ligature would be failing at what it claims. Probe this first. | A2, A4, A8, B2c, B4 |
| Q2 | Do records from a `supporting` verifier enter G14's closure (and so make `single_verifier_system` false)? | B1a-c |
| Q3 | Can one degradation record excuse two conditions with different gaps (CG1 `harness-tested` and CG3 `per-instantiation`)? It has one `capability_gap` and one `ceiling` field. | B2a-c, B4, B5 |
| Q4 | Does carrying a cross-cluster edge as a trusted assumption, instead of a required guarantee, keep the callee's evidence out of the caller's closure? | B3, B4 |
| Q5 | Does a Kani or Verus record anywhere in the workspace withhold CG3 from an unrelated Creusot cluster? | Axis A layout, B5 |
| Q6 | In a closure with two deductive verifiers, which `owning_verifier` does G14 recompute, and does either declaration pass G17? | B2c |
| Q7 | `check-bridges` runs the backend of the verifier that owns the bridge's cluster. Which backend runs for a bridge on a cross-verifier edge? | B3, B4 |
| Q8 | `configure-crate` offers only a `cargo-verus` profile. How are Creusot and Kani crates configured in a multi-crate workspace? | P4-6, every A and B row with a new crate |

Upstream tickets are filed only for gaps these probes confirm, and only when
Ligature fails at what it claims to do. By-design limits are recorded as
findings.

## 7. Prerequisites found while drafting

- **Each pilot must be its own Git repository root for Stage 7.**
  Work-package generation requires "the workspace must be the Git repository
  root and have a committed HEAD". Done for P2 on 2026-10-20:
  `swisstable-verus/` is now its own repo (`128804f`), linked as a submodule
  on `pilot/swisstable-verus`. Its ignore rules are in `.git/info/exclude`,
  because its write_set does not account for a tracked `.gitignore`.
- Every new single-verifier workspace from the Axis A layout needs the same:
  its own Git root with a committed HEAD, linked as a submodule.
- P2 also carries a stale C-static report: 3 high findings asking for an
  `extract-c-static` re-run.

## 8. What counts as covered

A row is covered when all of the following are saved under the
configuration's evidence directory and summarized in P4-20 (#174):

1. **Declared configuration.** The descriptor's `verifier_policy` (and
   `supporting`, `crates[]`, `verifier_backends`) matches the row; concept
   specs are promoted; work packages are produced by
   `generate-work-package`; the closure profile, and any degradation record,
   are approved by the operator.
2. **Evidence intake.** `record-assurance` records for every obligation
   from the owning verifier (`--proof`, `--verus-json` or `--kani-crate`),
   plus the supporting verifier's where the row has one. Verus intake
   respects #125–#127.
3. **Gate result.** `gate g14 --json`, `check --json` and `status --json`
   outputs, with `expected_obligations` pinned. G14's per-cluster verdict
   either matches this spec's expected outcome or the mismatch is recorded
   as a finding.
4. **Behavioural parity.** The port's existing oracle suite passes against
   the configuration's crates (P1 oracle, P2 Stage 8B oracle, P3's 2580
   tests).
5. **Replayable.** Every command is recorded with its exit code and the
   Ligature bundle hash, so a fresh agent can replay it.

A row whose expected outcome is degraded is covered by a degraded release
that matches the expected gap and ceiling. A degraded result is not a
failure of the row.

## 9. Coverage count

| | Rows | Done | Open |
|---|---|---|---|
| Axis A cells | 9 | 2 (A1, A9) | 7 |
| Axis B rows | 9 (B1a-c, B2a-c, B3, B4 with its six pairs, B5) | 0 (#23 predates 1.4.2) | 9 |
| Synthetic probes | 2 (G15, CG6) | 0 | 2 |
