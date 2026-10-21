// probe 13 - self-recursion
pub struct T;
impl T {
    pub fn root(&self, n: usize) -> usize {
        if n == 0 { 0 } else { self.root(n - 1) + 1 }
    }
}
