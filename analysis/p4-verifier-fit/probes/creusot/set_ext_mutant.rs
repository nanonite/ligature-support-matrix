//! #157 probe: swisstable-verus-023's derived-set extensionality, in Creusot.
//! `stored` mirrors P2's `stored_hashes_of`, restricted to full slots.
use creusot_std::logic::{Int, Seq, Set};
use creusot_std::prelude::*;

#[logic]
pub fn stored(full: Seq<bool>, hashes: Seq<u64>, cap: Int) -> Set<u64> {
    pearlite! { Set::from_predicate(|k: u64| exists<i: Int> 0 <= i && i < cap && full[i] && hashes[i] == k) }
}

/// Control: dropping the uniqueness requirement makes erase false; this must NOT prove.
#[logic]
#[requires(0 <= s && s < cap && cap <= full.len() && cap <= hashes.len() && full[s])]
#[ensures(stored(full.set(s, false), hashes, cap) == stored(full, hashes, cap).remove(hashes[s]))]
pub fn erase_ext_mutant(full: Seq<bool>, hashes: Seq<u64>, cap: Int, s: Int) {}
