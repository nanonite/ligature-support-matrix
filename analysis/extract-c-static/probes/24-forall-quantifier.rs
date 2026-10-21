// probe 24 - a forall quantifier in an ensures clause, no cast, no calls
verus::verify! {
    pub struct T;
    impl T {
        pub broadcast proof fn q() ensures (forall|c: u8| true) { }
        pub fn f(&self) -> bool { false }
    }
}
