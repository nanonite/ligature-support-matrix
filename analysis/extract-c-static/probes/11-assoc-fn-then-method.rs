// probe 11 - associated function returning Self, then a method on the result
pub struct T;
impl T {
    pub fn new() -> Self { T }
    pub fn leaf(&self) -> usize { 1 }
    pub fn root(&self) -> usize { T::new().leaf() }
}
