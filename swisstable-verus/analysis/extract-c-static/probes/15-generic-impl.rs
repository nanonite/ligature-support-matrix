// probe 15 - generic impl over a policy type, the abseil template shape
pub trait Policy { fn key(&self) -> u64; }
pub struct Table<T: Policy> { pub policy: T }
impl<T: Policy> Table<T> {
    pub fn h1(&self) -> usize { (self.policy.key() % 64) as usize }
    pub fn probe_seq(&self) -> usize { self.probe_till_first_non_full_group() }
    pub fn probe_till_first_non_full_group(&self) -> usize { self.h1() }
}
