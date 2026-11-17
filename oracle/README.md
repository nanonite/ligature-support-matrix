# tinyxml2-creusot-kani native oracle

Setup record only (Chainlink #177). No native build or source checkout exists
in this root yet.

## Oracle identity

TinyXML2 11.0.0 native oracle

Dependencies pinned by `SOURCE-PIN.json`:

- tinyxml2.cpp and tinyxml2.h at the pinned commit
- xmltest.cpp and selected resources/ and test/ cases at the same commit

## Comparison plan

Typed DOM event streams, ordered attributes, selected mutation traces, serialization bytes where defined, upstream error classes and line numbers. Fix whitespace mode and depth/resource limits in every case.

## Layout (planned)

- `oracle/cases/` — versioned JSONL cases/expectations (worker-authored).
- `oracle/rust-check/` — Rust harness that calls the native oracle
  (its `Cargo.toml`/`Cargo.lock` are protected; operator/sanctioned creation).
- `oracle/driver/` — native driver sources.
- Task-specific native build root: `/tmp/p4-<issue>-tinyxml2-creusot-kani/oracle`.
  Never build inside this repository.

Read `oracle-PROTOCOL.md` before writing any case, driver or Rust test
generator. Native agreement falsifies discrepancies; it does not replace a
proof, and it does not establish parity for excluded behaviour.
