// probe 20 - the smallest possible macro body: no spec fn, no proof fn, no calls
verus::verify! {
    pub struct T;
    impl T {
        pub fn is_deleted(&self) -> bool { false }
    }
}
