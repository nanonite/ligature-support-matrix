// probe 03 - inherent-method-call-by-name through a local binding
pub struct T;
impl T {
    pub fn leaf(&self) -> usize { 1 }
    pub fn root(&self) -> usize {
        let me = T;
        me.leaf()
    }
}
