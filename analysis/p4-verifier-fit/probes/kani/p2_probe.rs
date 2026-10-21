// #157 probe (scratch copy only): Kani on P2's real Verus crate.
// Capacity 31 (capacity_bits = 5), the smallest the table allows.
use crate::raw_table::NO_HASH;
use crate::swiss_table::SwissTable;

#[kani::proof]
#[kani::unwind(50)]
fn insert_contains_erase() {
    let mut t = SwissTable::new(5);
    let k: u64 = kani::any();
    let v: u64 = kani::any();
    kani::assume(k != NO_HASH);
    assert!(t.insert(k, v));
    assert!(t.contains(&k));
    assert!(t.erase(&k));
    assert!(!t.contains(&k));
}

/// Mutant: claims the key survives erase; must FAIL.
#[kani::proof]
#[kani::unwind(50)]
fn insert_contains_erase_mutant() {
    let mut t = SwissTable::new(5);
    let k: u64 = kani::any();
    let v: u64 = kani::any();
    kani::assume(k != NO_HASH);
    assert!(t.insert(k, v));
    assert!(t.erase(&k));
    assert!(t.contains(&k));
}
