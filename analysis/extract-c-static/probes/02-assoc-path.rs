// probe 02 - associated-path-call: Type::leaf() and Self::leaf()
pub struct T;
impl T {
    pub fn leaf(&self) -> usize { 1 }
    pub fn root(&self) -> usize { T::leaf(self) + Self::leaf(self) }
}
