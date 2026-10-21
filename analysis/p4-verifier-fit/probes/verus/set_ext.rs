use vstd::prelude::*;
verus! {
// #157 probe: swisstable-verus-023's derived-set extensionality, minimal Verus form.
pub open spec fn stored(full: Seq<bool>, hashes: Seq<u64>, cap: int) -> Set<u64> {
    Set::new(|k: u64| exists|i: int| 0 <= i < cap && full[i] && hashes[i] == k)
}
proof fn insert_ext(full: Seq<bool>, hashes: Seq<u64>, cap: int, s: int, h: u64)
    requires 0 <= s < cap, cap <= full.len(), cap <= hashes.len(), !full[s],
    ensures stored(full.update(s, true), hashes.update(s, h), cap) == stored(full, hashes, cap).insert(h),
{
    assert(stored(full.update(s, true), hashes.update(s, h), cap) =~= stored(full, hashes, cap).insert(h));
}
proof fn erase_ext(full: Seq<bool>, hashes: Seq<u64>, cap: int, s: int)
    requires 0 <= s < cap, cap <= full.len(), cap <= hashes.len(), full[s],
             forall|j: int| 0 <= j < cap && j != s && full[j] ==> hashes[j] != hashes[s],
    ensures stored(full.update(s, false), hashes, cap) == stored(full, hashes, cap).remove(hashes[s]),
{
    assert(stored(full.update(s, false), hashes, cap) =~= stored(full, hashes, cap).remove(hashes[s]));
}
// Control: without uniqueness, erase is false; this must NOT verify.
proof fn erase_ext_mutant(full: Seq<bool>, hashes: Seq<u64>, cap: int, s: int)
    requires 0 <= s < cap, cap <= full.len(), cap <= hashes.len(), full[s],
    ensures stored(full.update(s, false), hashes, cap) == stored(full, hashes, cap).remove(hashes[s]),
{
    assert(stored(full.update(s, false), hashes, cap) =~= stored(full, hashes, cap).remove(hashes[s]));
}
fn main() {}
}
