// probe 08 - trait-impl method body calling a helper on the same type
pub trait Tr {
    fn leaf(&self) -> usize;
    fn root(&self) -> usize;
}
pub struct T;
impl T {
    pub fn leaf(&self) -> usize { 1 }
}
impl Tr for T {
    fn root(&self) -> usize { self.leaf() }
}
