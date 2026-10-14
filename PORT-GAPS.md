# P3 Crypto Mixed transfer gaps

These findings come from the Botan 3.13.0 Codesight analysis and the P3 port.
The port now implements the selected scalar 96-bit-nonce ChaCha20, Poly1305,
and RFC 8439 AEAD subset. Statuses remain open where analysis coverage,
provider parity, or proof scope is still incomplete.

### C++ header declarations are absent from the analysis index

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** `src/lib/stream/chacha/chacha.h`, `src/lib/mac/poly1305/poly1305.h`, and `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.h` at pinned Botan 3.13.0. Codesight returned `File not found in index`, so declaration line numbers were unavailable from its index.
- **What the Rust port does instead:** `crypto-mixed-core` implements a scalar ChaCha20 stream type, a streaming Poly1305 type, and their AEAD composition using the pinned Botan subset. It does not reproduce Botan's base-class hierarchy, provider factory, or dynamic dispatch surface.
- **Why:** The successful repository index omitted all three selected headers. Codesight could not return their outlines or ChaCha/Poly1305 type hierarchies.
- **Impact:** State invariants, interface dispatch, nonce/key limits, and ownership boundaries can be missed if the port plan is based on implementation files alone.
- **Status:** open
- **Finding ids:** `crypto-mcp-002`
- **Generalizable lesson:** A successful C++ index does not prove that headers were included. Check representative declarations and type hierarchies before using an AST index as the port inventory.

### Call-graph edges need source-level confirmation

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** `src/lib/stream/chacha/chacha.cpp:134` and `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp:110,154`.
- **What the Rust port does instead:** The Rust AEAD path explicitly derives the Poly1305 key from ChaCha counter zero, encrypts from counter one, and authenticates AAD, padding, ciphertext, and encoded lengths. The selected path was checked against the pinned Botan bodies; Codesight's general call graph remains unsuitable as sole dependency evidence.
- **Why:** Codesight returned an unrelated `store_le` edge from IDEA for `ChaCha::chacha`, omitted the AEAD-to-Poly1305 update edge, and found no call chain from AEAD encryption to `Poly1305::add_data`.
- **Impact:** Incorrect edges can produce false supplier ordering, while missing edges can hide which arithmetic and buffer operations jointly determine the AEAD tag.
- **Status:** open
- **Finding ids:** `crypto-mcp-003`, `crypto-mcp-004`
- **Generalizable lesson:** Validate call-graph results against symbol bodies whenever C++ overloads, virtual APIs, or unresolved names can connect unrelated code.

### Template and SIMD providers are not represented by their outlines

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** Macro-gated dispatch in `src/lib/stream/chacha/chacha.cpp:137,147,157`; `src/lib/stream/chacha/chacha_avx2/chacha_avx2.cpp:15`; `src/lib/stream/chacha/chacha_avx512/chacha_avx512.cpp:15`; and template declarations in `src/lib/mac/poly1305/poly1305_avx512/poly1305_avx512.cpp:42,68`.
- **What the Rust port does instead:** This P3 implementation uses scalar ChaCha20 and 26-bit-limb Poly1305 only. SIMD providers and Botan provider selection are not implemented or claimed; Verus is deferred to P4 and does not change this provider scope.
- **Why:** Codesight outlines returned only module entries for the ChaCha SIMD files and only a `raw()` helper for each Poly1305 SIMD file. Its search could see the macro and template text, but its symbol outlines did not represent those implementations.
- **Impact:** Scalar byte-level parity would not establish provider-selection or optimized-path coverage. SIMD-specific arithmetic and feature dispatch need a separate parity decision.
- **Status:** open
- **Finding ids:** `crypto-mcp-005`
- **Generalizable lesson:** Keep optimized C++ providers visible in the port inventory even when the chosen Rust implementation is scalar; an empty syntax-tool outline is not evidence that the behavior does not exist.


### Bounded Kani is the first P3 proof scope; deductive Verus is deferred

- **Category:** Unprovable or costly obligations
- **C++ construct / upstream location:** Scalar ChaCha20 quarter-round and block in `src/lib/stream/chacha/chacha.cpp:30-43,134-230`; Poly1305 initialization and limb arithmetic in `src/lib/mac/poly1305/poly1305.cpp:93-160`; AEAD composition in `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp:110-166` at Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`.
- **What the Rust port does instead:** The P3 first pass assigns ChaCha20, Poly1305, and ChaCha20-Poly1305 to the `crypto-kani` cluster. Kani harnesses cover a 65-byte ChaCha block-boundary input, all ChaCha counter values at that fixed length, Poly1305 messages of lengths 0 through 65, and pinned Botan vectors. The general symbolic ChaCha length proofs time out at the 65-byte bound; symbolic Poly1305 chunk-equivalence and one-byte symbolic AEAD round-trip attempts also time out. Verus remains deferred to P4.
- **Why:** Kani 0.67.0 expands dynamic vectors, crypto loops, allocation checks, and equality checks into bounded CBMC obligations. The manifests' minimum scopes require all accepted slice lengths up to the RFC 8439 limit (`2^38 - 64` bytes), which these bounded harnesses do not establish. The Kani-only scope also makes no deductive or constant-time claim.
- **Impact:** Passing fixed and bounded harnesses establish only their stated domains. They do not meet the manifests' full-domain requirements or prove universal arithmetic, optimized-provider parity, or side-channel behavior. A human contract revision and Kani assurance intake are required before G14 can certify the current package declarations.
- **Status:** open
- **Generalizable lesson:** When a mixed-verifier port starts with one backend, state the bounds of every result and keep omitted deductive and side-channel claims visible as separate follow-ups. A verifier described as bounded still needs manifest scopes that match feasible harness domains.
- **Finding ids:** `crypto-kani-001`, `crypto-kani-002`, `crypto-kani-003`, `crypto-kani-004`, `crypto-kani-005`

### Successful bounded verification was blocked by assertion-status intake

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** Streaming Poly1305 block processing and finalization in `src/lib/mac/poly1305/poly1305.cpp:93-160` at Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`.
- **What the Rust port does instead:** The tag-length harness calls one-shot `compute_tag` with symbolic messages of lengths 0 through 65. A fresh Kani 0.67.0 run returned 724 `SUCCESS` and 9 `UNREACHABLE` checks, zero failures, and successful verification. Three unreachable checks belong to the unused partial-buffer continuation branch; six belong to Rust library code. The tag-length assertion itself returned `SUCCESS`.
- **Why:** Ligature 1.3.9 resolved the qualified harness but rejected ancillary checks marked `UNREACHABLE`. Ligature 1.3.10 preserves those checks and requires the named obligation assertion to succeed.
- **Impact:** Ligature 1.3.10 records the bounded result and G14 consumes it. G14 still leaves Poly1305 unmet because the bounded harness does not cover the manifest's full domain; separate obligations and bridge evidence are also missing. The public `finalize` lifecycle and streaming continuation paths remain outside this harness.
- **Status:** resolved in Ligature 1.3.10; verified in a disposable pilot copy on 2026-10-14. The report recorded 724 successful checks and 9 ancillary unreachable checks; G14 consumed it and reported separate scope and missing-evidence blockers.
- **Finding ids:** `crypto-ligature-002`; related bounded-scope finding `crypto-kani-001`. Detailed reproduction and raw checks: `/tmp/crypto-133-rca/ROOT-CAUSE.md`.
- **Generalizable lesson:** Verifier adapters must preserve the backend's distinction between failed assertions, unreachable assertions, and cover properties. Recording successful bounded evidence must also preserve its actual method and input coverage.
