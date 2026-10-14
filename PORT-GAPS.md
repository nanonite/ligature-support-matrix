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
- **What the Rust port does instead:** The P3 first pass assigns ChaCha20, Poly1305, and ChaCha20-Poly1305 to `crypto-kani`. The recorded Kani obligations are ChaCha20.C002 at exactly 65 input bytes (646 successful checks, 6 unreachable safety checks), ChaCha20.C003 for every target `usize` length accepted by the AEAD length guard (30 successful, 1 unreachable), and Poly1305.C002 for symbolic messages of lengths 0 through 65 (724 successful, 9 unreachable). The two bridge records rerun source harnesses for derived-key acceptance and counter-one capacity; both pass with 4 and 1 unreachable safety checks respectively.
- **Why:** Kani 0.67.0 checks the finite model encoded by each harness. The original manifests requested full RFC/all-sequence domains; the human-approved revisions now set each minimum scope to the exact named harness model. The Kani-only scope makes no deductive or constant-time claim.
- **Impact:** The five records satisfy their revised bounded scopes and G14 consumes them. They do not establish arbitrary-length cryptographic behavior, universal generic coverage, optimized-provider parity, or side-channel behavior. G14 releases the cluster as degraded under a `per-instantiation` ceiling for CG3; P4 issue #135 tracks the generic-callee follow-up.
- **Status:** bounded P3 evidence recorded and consumed by G14 on 2026-10-14; full closure remains degraded pending #135.
- **Generalizable lesson:** When a mixed-verifier port starts with one backend, state the bounds of every result and keep omitted deductive and side-channel claims visible as separate follow-ups. A verifier described as bounded still needs manifest scopes that match feasible harness domains.
- **Finding ids:** `crypto-kani-001`, `crypto-kani-002`, `crypto-kani-003`, `crypto-kani-004`, `crypto-kani-005`

### Successful bounded verification was blocked by assertion-status intake

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** Streaming Poly1305 block processing and finalization in `src/lib/mac/poly1305/poly1305.cpp:93-160` at Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`.
- **What the Rust port does instead:** The tag-length harness calls one-shot `compute_tag` with symbolic messages of lengths 0 through 65. A fresh Kani 0.67.0 run returned 724 `SUCCESS` and 9 `UNREACHABLE` checks, zero failures, and successful verification. Three unreachable checks belong to the unused partial-buffer continuation branch; six belong to Rust library code. The tag-length assertion itself returned `SUCCESS`.
- **Why:** Ligature 1.3.9 resolved the qualified harness but rejected ancillary checks marked `UNREACHABLE`. Ligature 1.3.10 preserves those checks and requires the named obligation assertion to succeed.
- **Impact:** The actual pilot report now records the bounded result, and the approved Poly1305.C002 minimum scope matches the named harness. The public `finalize` lifecycle and streaming continuation paths remain outside this harness.
- **Status:** resolved by Ligature 1.3.10 and verified in the actual pilot on 2026-10-14. The report records 724 successful checks and 9 ancillary unreachable checks; G14 consumes it under the revised bounded scope.
- **Finding ids:** `crypto-ligature-002`; related bounded-scope finding `crypto-kani-001`. Detailed reproduction and raw checks: `/tmp/crypto-133-rca/ROOT-CAUSE.md`.
- **Generalizable lesson:** Verifier adapters must preserve the backend's distinction between failed assertions, unreachable assertions, and cover properties. Recording successful bounded evidence must also preserve its actual method and input coverage.

### Generated Kani bridge harnesses are not run without a configured backend

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** ChaCha20-Poly1305 one-time Poly1305 key setup and encryption processing in `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp:55,90,110` at Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`.
- **What the Rust port does instead:** `crates/crypto-mixed-core/tests/kani_bridge_backend.py` validates each generated bridge ID, boundary, premise, and conclusion against a fixed mapping, then runs the corresponding exact Kani source harness. G9 binds each report to the generated bridge hash and the source harness hash. A project-local bridge-only report assembler copies the two passing G9 records into the AEAD work-package report without adding obligation records.
- **Why:** The project descriptor initially lacked `verifier_backends.kani.command`, so generated bridge harnesses were not dispatched. Ligature 1.3.10's `record-assurance` also refuses an empty obligation-proof invocation for a bridge-only package; G14 requires the package report to contain its bridge records.
- **Impact:** Both bridge records now pass G9 and appear in the AEAD package report. The adapter is fail-closed if the generated DSL changes, a Kani run is incomplete, or a recorded scope/hash is stale. Ligature source was not changed.
- **Status:** resolved in the pilot on 2026-10-14; `check-bridges`, G9, and G14 verified the records.
- **Finding ids:** `crypto-ligature-003`
- **Generalizable lesson:** Generating a verifier harness is not the same as checking it. A mixed-verifier port needs a configured adapter that consumes the exact generated boundary harness and records the owning verifier's verdict.

### Locked Kani intake needs an approved lockfile path

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** ChaCha20 stream processing in `src/lib/stream/chacha/chacha.cpp:134-230` and Poly1305 arithmetic in `src/lib/mac/poly1305/poly1305.cpp:93-160` at Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`.
- **What the Rust port does instead:** The crate now has the normal generated `crates/crypto-mixed-core/Cargo.lock`, authorized as the exact protected path for issue #134. Cargo metadata and Ligature's Kani runs use the pinned toolchain; Kani target directories remain temporary and outside the checkout.
- **Why:** Ligature 1.3.10 runs `cargo metadata --locked` before Kani. A crate without a lockfile could not pass that prerequisite, and the lockfile path was not previously declared in the project or package write policy.
- **Impact:** Fresh Kani reports are now recorded and reproducible through Ligature's locked intake. The lockfile's SHA-256 is `500245d4c61242e614363a03597f8c88f7c827d02115ffbc92f8dabd774f5fc1`; `cargo metadata --locked` and `write-set-check --issue 134` pass.
- **Status:** resolved in the pilot on 2026-10-14.
- **Finding ids:** `crypto-ligature-004`
- **Generalizable lesson:** Lockfile enforcement supports reproducible verification only when the project authorizes a way to create and retain the lockfile before the verifier intake begins.
