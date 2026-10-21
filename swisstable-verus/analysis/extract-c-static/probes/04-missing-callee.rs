// probe 04 - callee that is NOT defined anywhere in the crate
// (the shape a port has at every not-yet-written step)
pub struct T;
impl T {
    pub fn root(&self) -> usize { self.find_first_non_full_from_h1(0) }
}
