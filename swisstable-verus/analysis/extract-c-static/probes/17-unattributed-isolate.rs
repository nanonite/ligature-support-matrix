// probe 17 - isolate the unattributed_call_sites counter:
// two proof-fn calls, nothing else.
verus::verify! {
    pub struct T;
    impl T {
        pub proof fn a() { }
        pub proof fn b() { T::a(); }
    }
}
