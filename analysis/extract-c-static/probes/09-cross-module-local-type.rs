// probe 09 - a local type declared in another module, called through a binding
pub mod model {
    pub struct Ctrl { pub b: u8 }
    impl Ctrl {
        pub fn is_deleted(&self) -> bool { self.b == 0x80 }
    }
}
pub struct T { pub ctrl: model::Ctrl }
impl T {
    pub fn root(&self) -> bool {
        let c = self.ctrl;
        c.is_deleted()
    }
}
