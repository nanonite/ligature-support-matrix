// probe 18 - the spec-file shapes a Verus port leans on:
// open spec fn, proof fn, broadcast proof fn, ensures/requires clauses.
verus::verify! {
    pub struct T { pub ctrl: u8 }
    impl T {
        pub open spec fn spec_is_deleted(&self) -> bool { self.ctrl == 0x80 }
        pub proof fn lemma_ctrl_bound(c: u8) ensures (c as int < 256) { }
        pub broadcast proof fn lemma_all() ensures (forall|c: u8| true) { }
        pub fn is_deleted(&self) -> bool { self.spec_is_deleted() }
    }
}
