use vstd::prelude::*;

verus! {
    tracked struct GhostState {
        m: Map<u64, u64>,
    }

    struct ExecTable {
        g: Tracked<GhostState>,
    }

    impl ExecTable {
        closed spec fn map(self) -> Map<u64, u64> {
            self.g@.m
        }

        fn new() -> (r: Self)
            ensures r.map() == Map::<u64, u64>::empty(),
        {
            let tracked g = GhostState { m: Map::tracked_empty() };
            ExecTable { g: Tracked(g) }
        }

        fn insert(&mut self, key: u64, value: u64)
            requires !self.map().dom().contains(key),
            ensures final(self).map() == old(self).map().insert(key, value),
        {
            proof { self.g.borrow_mut().m.tracked_insert(key, value); }
        }

        fn remove(&mut self, key: u64)
            requires self.map().dom().contains(key),
            ensures final(self).map() == old(self).map().remove(key),
        {
            proof { let tracked _old_value = self.g.borrow_mut().m.tracked_remove(key); }
        }
    }

    fn smoke() {
        let mut t = ExecTable::new();
        assert(!t.map().dom().contains(7));
        t.insert(7, 70);
        assert(t.map().dom().contains(7));
        t.remove(7);
        assert(!t.map().dom().contains(7));
    }
}
