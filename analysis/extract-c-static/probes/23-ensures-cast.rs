// probe 23 - an ensures clause with a cast, no quantifier, no calls
verus::verify! {
    pub struct T;
    impl T {
        pub proof fn p(c: u8) ensures (c as int < 256) { }
        pub fn f(&self) -> bool { false }
    }
}
