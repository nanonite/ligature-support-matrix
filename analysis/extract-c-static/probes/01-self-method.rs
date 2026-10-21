// probe 01 - baseline: self-method-call inside an inherent impl
pub struct T;
impl T {
    pub fn leaf(&self) -> usize { 1 }
    pub fn root(&self) -> usize { self.leaf() }
}
