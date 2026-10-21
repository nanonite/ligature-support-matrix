// subset-port transcription fixture (chainlink #108).  NOT a port, NOT pilot
// code: a faithful Rust transcription of the P2 SwissTable subset, one module
// per subset area, used as the Rust side of a three-way comparison whose third
// side is the pinned C++ (upstream/abseil-cpp 2065f4de) and whose fourth side
// is codesight-mcp's recorded answer.  See ../README.md and ../edge-truth.tsv.
pub mod ctrl;
pub mod group;
pub mod iteration;
pub mod open_addressing;
pub mod rehash;
pub mod tombstones;
