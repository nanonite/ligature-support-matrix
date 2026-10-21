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
    }

    fn insert_range(n: u64) -> (t: ExecTable)
        ensures t.map().dom() =~= Set::<u64>::new(|k: u64| k < n),
    {
        broadcast use vstd::map::group_map_axioms;
        broadcast use vstd::set::group_set_axioms;
        let mut t = ExecTable::new();
        let mut i: u64 = 0;
        while i < n
            invariant
                i <= n,
                t.map().dom() =~= Set::<u64>::new(|k: u64| k < i),
            decreases n - i,
        {
            assert(!t.map().dom().contains(i));
            t.insert(i, i);
            i = i + 1;
        }
        t
    }
}
