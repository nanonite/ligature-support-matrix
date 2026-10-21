//! #157 probe: swisstable-verus-023's derived-set extensionality, in Creusot.
//! `stored` mirrors P2's `stored_hashes_of`, restricted to full slots.
use creusot_std::logic::{Int, Seq, Set};
use creusot_std::prelude::*;

#[logic]
pub fn stored(full: Seq<bool>, hashes: Seq<u64>, cap: Int) -> Set<u64> {
    pearlite! { Set::from_predicate(|k: u64| exists<i: Int> 0 <= i && i < cap && full[i] && hashes[i] == k) }
}

/// Insert: slot `s` goes from not full to full with hash `h`.
#[logic]
#[requires(0 <= s && s < cap && cap <= full.len() && cap <= hashes.len() && !full[s])]
#[ensures(stored(full.set(s, true), hashes.set(s, h), cap) == stored(full, hashes, cap).insert(h))]
pub fn insert_ext(full: Seq<bool>, hashes: Seq<u64>, cap: Int, s: Int, h: u64) {}

/// Erase: slot `s` stops being full; its hash leaves the set when no other full slot holds it.
#[logic]
#[requires(0 <= s && s < cap && cap <= full.len() && cap <= hashes.len() && full[s])]
#[requires(forall<j: Int> 0 <= j && j < cap && j != s && full[j] ==> hashes[j] != hashes[s])]
#[ensures(stored(full.set(s, false), hashes, cap) == stored(full, hashes, cap).remove(hashes[s]))]
pub fn erase_ext(full: Seq<bool>, hashes: Seq<u64>, cap: Int, s: Int) {}
