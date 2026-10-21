// Rust port of the pinned Abseil SwissTable subset (chainlink #30).
//
// Suppliers first: `hash_mix`, `control_bytes`, `group_probe` and `probe_seq`
// have no callers inside this crate's dependency order, so they are verified
// before `raw_table`, `table_iterator` and `swiss_table` are written against
// their postconditions.
//
// Every module is a separate `verus!` block; `verus --crate-type=lib src/lib.rs`
// verifies the whole crate in one pass.  `verif/` holds the manual lemmas this
// port needed (the ones that SMT could not derive on its own), so the
// obligations whose proof was not free are visible rather than hidden.
#![allow(unused, nonstandard_style)]

pub mod control_bytes;
pub mod group_probe;
pub mod hash_mix;
pub mod probe_seq;
pub mod raw_table;
pub mod swiss_table;
pub mod table_iterator;

#[path = "../verif/lemmas.rs"]
pub mod lemmas;

