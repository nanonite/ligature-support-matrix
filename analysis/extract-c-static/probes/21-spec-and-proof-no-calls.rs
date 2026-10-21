// probe 21 - same as 20 but with a spec fn and a proof fn, still no calls
verus::verify! {
    pub struct T { pub ctrl: u8 }
    impl T {
        pub open spec fn s(&self) -> bool { true }
        pub proof fn p() { }
        pub fn is_deleted(&self) -> bool { false }
    }
}
