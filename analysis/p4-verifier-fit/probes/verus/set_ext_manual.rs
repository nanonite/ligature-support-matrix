use vstd::prelude::*;
verus! {
// #157 probe: the insert lemma from set_ext.rs, with explicit witnesses.
pub open spec fn stored(full: Seq<bool>, hashes: Seq<u64>, cap: int) -> Set<u64> {
    Set::new(|k: u64| exists|i: int| 0 <= i < cap && full[i] && hashes[i] == k)
}
proof fn insert_ext(full: Seq<bool>, hashes: Seq<u64>, cap: int, s: int, h: u64)
    requires 0 <= s < cap, cap <= full.len(), cap <= hashes.len(), !full[s],
    ensures stored(full.update(s, true), hashes.update(s, h), cap) == stored(full, hashes, cap).insert(h),
{
    let f2 = full.update(s, true);
    let h2 = hashes.update(s, h);
    let a = stored(f2, h2, cap);
    let b = stored(full, hashes, cap).insert(h);
    assert forall|k: u64| a.contains(k) implies b.contains(k) by {
        let i = choose|i: int| 0 <= i < cap && f2[i] && h2[i] == k;
        if i != s {
            assert(0 <= i < cap && full[i] && hashes[i] == k);
        }
    }
    assert forall|k: u64| b.contains(k) implies a.contains(k) by {
        if k == h {
            assert(0 <= s < cap && f2[s] && h2[s] == k);
        } else {
            let i = choose|i: int| 0 <= i < cap && full[i] && hashes[i] == k;
            assert(0 <= i < cap && f2[i] && h2[i] == k);
        }
    }
    assert(a =~= b);
}
fn main() {}
}
