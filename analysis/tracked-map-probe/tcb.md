# Tracked Map trust note — Chainlink #120

Pinned verifier: Verus `0.2026.05.24.ecee80a`; Cargo dependency:
`vstd = 0.0.0-2026-05-24-0157`. The source inspected is
`~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/vstd-0.0.0-2026-05-24-0157/map.rs`.

The analysis clone uses `Map<u64, usize>`: a live hash maps to its current physical
slot. The operations it invokes are explicitly axiomatic in the pinned vstd source:

```rust
pub axiom fn tracked_empty() -> (tracked out_v: Self)
    ensures out_v == Map::<K, V>::empty();

pub axiom fn tracked_insert(tracked &mut self, key: K, tracked value: V)
    ensures *final(self) == Map::insert(*old(self), key, value);

pub axiom fn tracked_remove(tracked &mut self, key: K) -> (tracked v: V)
    requires old(self).dom().contains(key),
    ensures *final(self) == Map::remove(*old(self), key),
            v == old(self)[key];
```

These declarations are at `map.rs:115-138` in the pinned package. `Map::tracked_borrow`
and `Map::tracked_borrow_mut` are also `axiom fn` declarations (`map.rs:141-155`), but
the probe calls neither. The Rust `Tracked::borrow_mut()` wrapper method used to access
the tracked struct is distinct from these Map operations. `Map`'s
`empty`, `insert`, `remove`, `dom`, and `index` are specification functions, not
tracked runtime operations.

P2 and the integration broadcast `vstd::map::group_map_axioms` and
`vstd::set::group_set_axioms`. These are groups of vstd axioms (see `map.rs:336-346`
and `set.rs:999+`); broadcasting them adds trusted facts about map transitions and
Set domains/extensionality to the verifier context. They are library axioms, not
project-authored assumptions, but they enlarge the TCB of any proof that uses them.

The experiment adds no project `axiom fn`, `assume`, `admit`, or `external_body`. Its
154/0 result is therefore a proof relative to the pinned vstd axioms, not a proof with
the same trust base as the existing source-only model. This cost is why the tracked Map
remains in the analysis clone. On 2026-10-08 the operator chose to keep the
2026-10-02 scope ruling; production adoption is not authorized unless that decision
is explicitly reversed in the future.
