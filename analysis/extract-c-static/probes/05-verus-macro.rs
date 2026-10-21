// probe 05 - the entire impl inside a verus!{} macro body
verus::verify! {
    pub struct T {
        pub ctrl: u8,
    }
    impl T {
        pub fn leaf(&self) -> usize { 1 }
        pub fn root(&self) -> usize { self.leaf() }
    }
}
