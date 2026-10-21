# SwissTable oracle operation contract

Version: 1

The operation is map_sequence. Its inputs object has exactly one field,
actions, which is an ASCII string containing semicolon-separated actions:

- insert(key,value) inserts or replaces a u64 key/value pair. The result is
  true for a new key and false for replacement.
- erase(key) removes a key and returns whether it was present.
- contains(key) returns whether the key is present.
- reserve(additional) calls the C++ map reserve(size + additional) and the Rust
  port reserve(additional). Capacity and growth timing are not included.
- clear() removes all entries.
- erase_if_all(), erase_if_none(), and erase_if_odd() erase entries by the
  named predicate and return the number removed. Oddness is computed from the
  unsigned key's low bit.

After each action, the result records the action text, its operation result,
the map size, and all key/value pairs sorted by key. The final result also
contains the sorted final map. This compares observable contents and specified
operation results only. It does not compare iteration order, capacity,
allocation, pointer identity/stability, native hash outputs, or probe and
growth costs.

The C++ map uses absl::flat_hash_map<uint64_t, uint64_t, IdentityHash> where
IdentityHash-v1(key) == key; Rust stores that same raw u64 as its hash input.
The shared input is the identity-hash mapping, not either implementation's
hash algorithm or slot placement. Key zero is excluded because the Rust port
reserves it as NO_HASH. The driver emits the protocol's null placeholder for
an excluded case; Rust checks its metadata and placeholder without comparing
behavior.

FlatHashMap.Reserve is represented by one small insert/erase/reserve/insert
sequence. It compares contents across reserve, not the upstream test's
reference-stability assertion. FlatHashMap.EraseIf covers all, none, and odd
key predicates; callable/reference and function-pointer forms are not Rust
API parity claims.
