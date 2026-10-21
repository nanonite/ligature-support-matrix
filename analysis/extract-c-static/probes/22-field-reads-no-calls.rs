// probe 22 - field reads only: no calls, no quantifier, no ensures clause
verus::verify! {
    pub struct T { pub ctrl: u8 }
    impl T {
        pub open spec fn s(&self) -> bool { self.ctrl == 0x80 }
        pub fn is_deleted(&self) -> bool { self.ctrl == 0x80 }
    }
}
