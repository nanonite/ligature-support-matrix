// probe 14 - the most common port shape: a method on a struct field
verus::verify! {
    pub struct T {
        pub ctrl: u8,
    }
    impl T {
        pub open spec fn h1(hash: u64) -> usize { (hash % 64) as usize }
        pub fn root(&self, hash: u64) -> bool { self.is_deleted(hash) }
        pub fn is_deleted(&self, hash: u64) -> bool { self.h1(hash) == 1 }
    }
}
