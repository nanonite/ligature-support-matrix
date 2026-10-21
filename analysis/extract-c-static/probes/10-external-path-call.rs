// probe 10 - calls that leave the crate entirely (stdlib path, external crate)
pub struct T;
impl T {
    pub fn root(&self, a: usize, b: usize) -> usize {
        core::cmp::min(a, b) + self.leaf()
    }
    pub fn leaf(&self) -> usize { 1 }
}
