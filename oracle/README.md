# icl-creusot-verus native oracle

Setup record only (Chainlink #177). No native build or source checkout exists
in this root yet.

## Oracle identity

Boost 1.88.0 ICL native oracle

Dependencies pinned by `SOURCE-PIN.json`:

- Boost ICL module at the pinned commit plus the matching Boost 1.88.0 dependency distribution
- pinned test/Jamfile.v2 interval/set/map suites

## Comparison plan

Pointwise denotation AND canonical segment/iteration results for each selected container style; seeded operation traces, algebraic laws, extreme endpoints and split/join mutants.

## Layout (planned)

- `oracle/cases/` — versioned JSONL cases/expectations (worker-authored).
- `oracle/rust-check/` — Rust harness that calls the native oracle
  (its `Cargo.toml`/`Cargo.lock` are protected; operator/sanctioned creation).
- `oracle/driver/` — native driver sources.
- Task-specific native build root: `/tmp/p4-<issue>-icl-creusot-verus/oracle`.
  Never build inside this repository.

Read `oracle-PROTOCOL.md` before writing any case, driver or Rust test
generator. Native agreement falsifies discrepancies; it does not replace a
proof, and it does not establish parity for excluded behaviour.
