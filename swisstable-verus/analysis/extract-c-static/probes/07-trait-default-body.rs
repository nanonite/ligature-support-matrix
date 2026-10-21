// probe 07 - trait method with a default body (declaration, not an impl)
pub trait Tr {
    fn leaf(&self) -> usize;
    fn root(&self) -> usize { self.leaf() }
}
pub struct T;
impl Tr for T {
    fn leaf(&self) -> usize { 1 }
}
