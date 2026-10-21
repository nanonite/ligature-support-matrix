// probe 16 - verus proof fns calling each other inside the macro
verus::verify! {
    pub struct T;
    impl T {
        pub proof fn lemma_base(a: nat) ensures (a <= a) { }
        pub proof fn lemma_step(a: nat) ensures (a <= a) {
            T::lemma_base(a);
        }
        pub fn runtime(&self) -> usize { 1 }
        pub fn root(&self) -> usize {
            let ghost g = self.runtime();
            proof { T::lemma_step(g as nat); }
            g
        }
    }
}
