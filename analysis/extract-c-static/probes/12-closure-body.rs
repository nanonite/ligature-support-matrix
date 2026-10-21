// probe 12 - call inside a closure body
pub struct T;
impl T {
    pub fn leaf(&self) -> usize { 1 }
    pub fn root(&self) -> usize {
        let f = |i: usize| self.leaf() + i;
        f(0)
    }
}
