// probe 06 - free functions, no impl at all
pub fn leaf() -> usize { 1 }
pub fn root() -> usize { leaf() + other::leaf() }
pub mod other {
    pub fn leaf() -> usize { 2 }
}
