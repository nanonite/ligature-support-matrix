# Tracked-Map ghost-model probe — Chainlink #120

Status: completed as a separate P2 probe after #30. The evidence directory records
P1/P2, erase, resize, value-remapping, and TCB results. The production #30 contracts
remain unchanged; this document does not reverse the 2026-10-02 ruling.

## Question and evidence

The question is whether an incrementally maintained tracked `Map` can make the
live-set ghost model usable without a proof of extensional equality over a
derived `Set::new`.

The operator reports an independent probe against Verus
`0.2026.05.24.ecee80a` in disposable `/tmp` copies:

| Probe | Shape | Reported result |
|---|---|---|
| P1 | Executable struct holds `Tracked<GhostState>`; tracked struct owns `Map`; `tracked_empty`, insert/remove and map-transition postconditions | 3 verified, 0 errors |
| P2 | P1 plus a loop, per-iteration insert, two-way `dom()` invariants and broadcast map/set axioms | 3 verified, 0 errors |
| P3 | Bare tracked `Map` field in executable struct | Rejected: literal initialization parse error; shorthand rejected as an opaque datatype field expression |

These are operator-reported scratch results, not yet a reproduction in this
pilot tree. The implementation shape follows Verus examples: the executable
table owns a linear tracked wrapper; a separate `tracked struct` owns the map.
Proof code mutates through `self.g.borrow_mut().m.tracked_insert/remove`, and
specifications read `self.g@.m`. Do not place a bare tracked `Map` in the exec
struct.

The live-map domain is the primary live-set model and must be maintained
incrementally. The probe must define its key/value meaning and prove the
domain-to-slot relation directly; it must not introduce `ext_equal` as another
attempt to close the derived-set equality.

## Gates

1. Reproduce the P1/P2 smoke cases under the pinned Verus binary and retain the
   exact source and transcripts in `analysis/`. A green insertion smoke test is
   only setup, not acceptance.
2. Integrate insert and erase. The erase gate includes the upstream
   `WasNeverFull` branch from #30 and proves the map/slot relationship after
   both the `kEmpty` and `kDeleted` outcomes.
3. Run a bounded resize-loop spike. Keep the existing physical frame/counting
   proof obligations and source/destination placement burden. Test value/slot
   relocation and remapping; P2 tested key insertion only and does not de-risk
   `tracked_borrow_mut` or resize ownership.
4. Kill the approach if the resize slice remains unclosed after the bounded
   spike. Record the exact remaining obligation and transcript, preserve the
   current contracts, and do not claim success from new+insert alone.

Erase and resize verified; findings `swisstable-verus-011` and
`swisstable-verus-023` distinguish representation viability from the existing
derived-Set limitation. The operator decided on 2026-10-08 to keep the
2026-10-02 ruling. A future reversal requires an explicit new decision; this probe
does not authorize a contract swap.

## Trust and acceptance

The tracked operations on vstd `Map` are axiom functions. Before adopting them,
record the exact pinned definitions/signatures used and explain how those axioms
change the trusted computing base. Do not add project-authored axioms,
`assume`, `admit`, or external bodies to make the proof pass.

The probe is green because the erase integration and resize-loop gates passed
with zero Verus errors, the evidence/findings were updated, and the TCB note was
reviewed. The operator kept the existing contract scope on 2026-10-08.


## Recorded outcome

P1 and P2 each reproduce at 4 verified, 0 errors. The tracked model maps live hash to
physical slot and verifies through insert, erase, clear, and the bounded resize path;
value remapping is checked through `SwissTable::reserve`. Concrete control-window
fixtures cover both `WasNeverFull` outcomes. The branch probes found and fixed the
counter/specification error documented in findings -021/-030. An optional assertion
that one key's numeric slot changed failed at the verifier/resource limit; the bounded
claim is key/value preservation at the final map-selected slot, with no specific index
delta claimed (finding -033). See
`analysis/tracked-map-probe/results.md` and `tcb.md` for the exact source, transcripts,
and trust impact. The tracked representation remains analysis-only until a separate
operator decision on the contract ruling.
