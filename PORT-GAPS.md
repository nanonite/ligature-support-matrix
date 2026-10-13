# P3 Crypto Mixed transfer gaps

These findings come from the Botan 3.13.0 Codesight analysis. The Rust port
has not started; statuses below remain open until the relevant scope and
implementation decisions are made.

### C++ header declarations are absent from the analysis index

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** `src/lib/stream/chacha/chacha.h`, `src/lib/mac/poly1305/poly1305.h`, and `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.h` at pinned Botan 3.13.0. Codesight returned `File not found in index`, so declaration line numbers were unavailable from its index.
- **What the Rust port does instead:** Not implemented yet. Before defining Rust types, establish the class state, base interfaces, and method contracts from the pinned upstream declarations.
- **Why:** The successful repository index omitted all three selected headers. Codesight could not return their outlines or ChaCha/Poly1305 type hierarchies.
- **Impact:** State invariants, interface dispatch, nonce/key limits, and ownership boundaries can be missed if the port plan is based on implementation files alone.
- **Status:** open
- **Finding ids:** `crypto-mcp-002`
- **Generalizable lesson:** A successful C++ index does not prove that headers were included. Check representative declarations and type hierarchies before using an AST index as the port inventory.

### Call-graph edges need source-level confirmation

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** `src/lib/stream/chacha/chacha.cpp:134` and `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp:110,154`.
- **What the Rust port does instead:** Not implemented yet. For the initial dependency map, confirm each dependency against the corresponding upstream function body; do not derive module boundaries from Codesight edges alone.
- **Why:** Codesight returned an unrelated `store_le` edge from IDEA for `ChaCha::chacha`, omitted the AEAD-to-Poly1305 update edge, and found no call chain from AEAD encryption to `Poly1305::add_data`.
- **Impact:** Incorrect edges can produce false supplier ordering, while missing edges can hide which arithmetic and buffer operations jointly determine the AEAD tag.
- **Status:** open
- **Finding ids:** `crypto-mcp-003`, `crypto-mcp-004`
- **Generalizable lesson:** Validate call-graph results against symbol bodies whenever C++ overloads, virtual APIs, or unresolved names can connect unrelated code.

### Template and SIMD providers are not represented by their outlines

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** Macro-gated dispatch in `src/lib/stream/chacha/chacha.cpp:137,147,157`; `src/lib/stream/chacha/chacha_avx2/chacha_avx2.cpp:15`; `src/lib/stream/chacha/chacha_avx512/chacha_avx512.cpp:15`; and template declarations in `src/lib/mac/poly1305/poly1305_avx512/poly1305_avx512.cpp:42,68`.
- **What the Rust port does instead:** No SIMD implementation or scope cut has been selected. The current plan names scalar quarter-round/block and Poly1305 limb arithmetic; optimized provider behavior remains open until explicitly scoped.
- **Why:** Codesight outlines returned only module entries for the ChaCha SIMD files and only a `raw()` helper for each Poly1305 SIMD file. Its search could see the macro and template text, but its symbol outlines did not represent those implementations.
- **Impact:** Scalar byte-level parity would not establish provider-selection or optimized-path coverage. SIMD-specific arithmetic and feature dispatch need a separate parity decision.
- **Status:** open
- **Finding ids:** `crypto-mcp-005`
- **Generalizable lesson:** Keep optimized C++ providers visible in the port inventory even when the chosen Rust implementation is scalar; an empty syntax-tool outline is not evidence that the behavior does not exist.


### Bounded Kani is the first P3 proof scope; deductive Verus is deferred

- **Category:** Unprovable or costly obligations
- **C++ construct / upstream location:** Scalar ChaCha20 quarter-round and block in `src/lib/stream/chacha/chacha.cpp:30-43,134-230`; Poly1305 initialization and limb arithmetic in `src/lib/mac/poly1305/poly1305.cpp:93-160`; AEAD composition in `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp:110-166` at Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`.
- **What the Rust port does instead:** The P3 first pass assigns ChaCha20, Poly1305, and ChaCha20-Poly1305 to the `crypto-kani` cluster with bounded Kani. Verus integration is deferred to P4; the port and its harnesses do not exist yet.
- **Why:** The accepted project scope starts with the Kani mixed-crypto path. Bounded results are tied to the harness domain, bounds, and assumptions; they do not provide a deductive proof or a constant-time claim.
- **Impact:** P3 can establish only properties exercised within the declared Kani bounds. Universal arithmetic claims, optimized-provider parity, and side-channel behavior remain outside this pass.
- **Status:** ruled-scope-cut
- **Finding ids:** `crypto-kani-001`
- **Generalizable lesson:** When a mixed-verifier port starts with one backend, state the bounds of every result and keep omitted deductive and side-channel claims visible as separate follow-ups.
