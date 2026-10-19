# P3 Crypto Mixed transfer gaps

Updated 2026-10-18 from the Botan 3.13.0 Codesight/Tilth findings, the accepted P3 assurance records, the #135 operator ruling, and the installed Ligature bundle. The port implements the selected scalar 96-bit-nonce ChaCha20, Poly1305, and RFC 8439 AEAD subset. The findings ledger retains the original reproductions; entries below give their current status.

The installed `tools/ligature/ligature.pyz` is Ligature 1.4.1, attested from source commit `742cb253e0cb9753c7a34a0c32559936130e03ab`; its SHA-256 is `973b883b3f4d19e60950ce6b9f0247828459d60fadd05f0d6e29d17d19c31ab8`. `version --verify` passed on 2026-10-18. Earlier passes used 1.3.11 (`446c87f93aa84c3f538710385706fcf753cd242a1282ba88faa1ad6722cb351f`, verified 2026-10-14).

## Current P3 assurance result

The two work-package reports contain three obligation records and two bridge records, each bound to its named harness and source hashes. Kani 0.67.0 reported:

- `ChaCha20.C002`: symbolic key, nonce, and contents for an input of exactly 65 bytes; 646 successful checks and 6 ancillary `UNREACHABLE` checks.
- `ChaCha20.C003`: a symbolic target `usize` requested length, with a fixed AEAD counter-one setup; the harness checks that every length accepted by the AEAD length guard fits the remaining stream capacity; 30 successful checks and 1 ancillary `UNREACHABLE` check.
- `Poly1305.C002`: symbolic key and message contents, with message length bounded from 0 through 65 bytes; the named assertion checks the 16-byte tag length; 724 successful checks and 9 ancillary `UNREACHABLE` checks.
- `BR-CRYPTO-MIXED-001`: the named bridge harness checks its fixed 32-byte Poly1305-key model.
- `BR-CRYPTO-MIXED-002`: the named bridge harness checks the ChaCha20 counter-one capacity condition.

The approved manifest minimum scopes match these named harness models. Ligature records successful named assertions and preserves ancillary unreachable checks. The records do not establish arbitrary-length cryptographic behavior or a deductive proof. The G14 run on 2026-10-14 consumed both reports and exited successfully, while reporting the `crypto-kani` cluster as **degraded** under the accepted `per-instantiation` ceiling. The remaining condition is `generic_callees_type_universal_or_creusot_owned`; the degradation record tracks Chainlink #135. Ligature's G14 clarification (#142) identifies the accepted coverage ceiling and affected condition. P3 therefore has accepted bounded evidence and a recorded degradation, not full closure.

**Correction (2026-10-18).** That successful G14 run, and a repeat on the morning of 2026-10-18, read a C_static call-graph report extracted at the 2026-10-13 baseline, before the Rust source existed. The report had 0 call sites, so call-site validation was vacuous (see the stale C_static entry below). After the 1.4.1 manifest regeneration (#134), and against a fresh extraction (16 discovered / 12 resolved / 4 unresolved), G14 exits 1 and the cluster is **blocked**. The four unresolved `possible-dispatch` sites fail the AEAD package's `all-discovered-resolved` bridge requirement, and G17 recomputes `unresolved_indirect_calls_at_or_above_medium` as 4. `check` also reports three cross-concept calls missing from the declared interactions. The three Kani obligation records and both bridge records are still rechecked successfully, and the CG3 condition is still accepted as degraded. The outstanding work is Stage 8A call-site validation (#47).

Verus remains outside P3. No constant-time or side-channel claim is made. The scalar implementation does not claim SIMD/provider-selection parity with Botan.

## Transfer and analysis gaps

### Codesight indexing needed a writable parser cache

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** Not applicable; this is a Codesight/tree-sitter runtime-cache issue encountered while indexing the pinned Botan repository.
- **What the Rust port does instead:** No port change was needed. The Botan index was created after pointing `XDG_CACHE_HOME` at a writable temporary cache.
- **Why:** The first attempt tried to lock a parser cache under a read-only shared home directory.
- **Impact:** The failed attempt created no index. Retrying with the temporary cache succeeded with 1,199 files and 15,643 symbols.
- **Status:** Worked around for this pilot; the finding is environment-specific.
- **Finding ids:** `crypto-mcp-001`
- **Generalizable lesson:** Configure a writable parser cache before indexing in a restricted workspace.

### C++ header declarations are absent from the successful Codesight index

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** `src/lib/stream/chacha/chacha.h`, `src/lib/mac/poly1305/poly1305.h`, and `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.h` at pinned Botan 3.13.0.
- **What the Rust port does instead:** `crypto-mixed-core` implements the selected scalar ChaCha20 stream, streaming Poly1305, and their AEAD composition. It does not reproduce Botan's base-class hierarchy, provider factory, or dynamic-dispatch surface.
- **Why:** Codesight returned `File not found in index` for the selected headers, so it could not return their outlines or type hierarchies.
- **Impact:** State invariants, interface dispatch, nonce/key limits, and ownership boundaries can be missed if the port inventory relies on implementation files alone.
- **Status:** Open analysis-tool gap; this port checked the selected declarations against pinned upstream source.
- **Finding ids:** `crypto-mcp-002`
- **Generalizable lesson:** A successful C++ index does not establish header coverage. Check representative declarations and type hierarchies before relying on the index as the port inventory.

### Codesight reports a false ChaCha call-graph edge

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** `src/lib/stream/chacha/chacha.cpp:134` at pinned Botan 3.13.0.
- **What the Rust port does instead:** The Rust ChaCha20 implementation was compared with the pinned Botan function body; the unrelated edge was not used to order the port.
- **Why:** Codesight connected the ChaCha scalar block to an unrelated IDEA `store_le` helper.
- **Impact:** Trusting this edge as dependency evidence can create a false supplier relationship and misorder transfer work.
- **Status:** Open analysis-tool gap; source-level confirmation was used for this port.
- **Finding ids:** `crypto-mcp-003`
- **Generalizable lesson:** Confirm C++ call-graph edges against symbol bodies when overloads, virtual APIs, or unresolved names can connect unrelated code.

### Codesight omits the AEAD-to-Poly1305 call path

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp:110,154` at pinned Botan 3.13.0.
- **What the Rust port does instead:** The Rust AEAD path explicitly derives the Poly1305 key from ChaCha counter zero, encrypts from counter one, and authenticates AAD, padding, ciphertext, and encoded lengths; the selected path was checked against pinned Botan source.
- **Why:** Codesight omitted the AEAD-to-Poly1305 update edge and found no call chain from AEAD encryption to `Poly1305::add_data`, although the source directly updates Poly1305 with ciphertext.
- **Impact:** The graph can hide which arithmetic and buffer operations jointly determine the AEAD tag.
- **Status:** Open analysis-tool gap; source-level path confirmation was used for this port.
- **Finding ids:** `crypto-mcp-004`
- **Generalizable lesson:** Validate a call graph against the source whenever a missing edge would hide a cross-concept security dependency.

### Template and SIMD providers are not represented by Codesight outlines

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** Macro-gated dispatch in `src/lib/stream/chacha/chacha.cpp:137,147,157`; `src/lib/stream/chacha/chacha_avx2/chacha_avx2.cpp:15`; `src/lib/stream/chacha/chacha_avx512/chacha_avx512.cpp:15`; and template declarations in `src/lib/mac/poly1305/poly1305_avx512/poly1305_avx512.cpp:42,68`.
- **What the Rust port does instead:** P3 uses scalar ChaCha20 and 26-bit-limb Poly1305 only. SIMD providers and Botan provider selection are not implemented or claimed.
- **Why:** Codesight outlines showed module entries for the ChaCha SIMD files and only a `raw()` helper for each Poly1305 SIMD file. Search found macro and template text, but the outlines did not represent those implementations.
- **Impact:** Scalar parity does not establish optimized-path arithmetic or feature-dispatch coverage.
- **Status:** Open analysis blind spot; SIMD/provider parity is outside the accepted P3 subset.
- **Finding ids:** `crypto-mcp-005`
- **Generalizable lesson:** Keep optimized providers in the inventory even when the port selects a scalar implementation; an empty syntax-tool outline is not evidence that behavior is absent.

### Tilth misattributes C++ call sites to their enclosing method

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp:110-157` at pinned Botan 3.13.0.
- **What the Rust port does instead:** The Rust AEAD flow was checked against the source methods enclosing each call site.
- **Why:** Tilth returned relevant `m_poly1305->update` line hits but attributed lines 113 and 156 to `ChaCha20Poly1305_Mode::update_len`; source inspection shows they are inside the encryption and decryption `process_msg` methods.
- **Impact:** Search results can locate candidate lines but mislead callers about which method owns the behavior.
- **Status:** Open tool limitation; source-level confirmation was used for this port.
- **Finding ids:** `crypto-mcp-006`
- **Generalizable lesson:** Treat MCP line hits as candidates and verify their enclosing functions before using them as call-graph evidence.

### Ligature's syntactic call-graph extractor leaves calls on typed locals unresolved

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** Botan reaches its primitives through member pointers with virtual dispatch (`m_chacha->…`, `m_poly1305->…` in `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp:55-112` at commit `2a81eef56c96c237e590c27f9a75e60317c9c700`).
- **What the Rust port does instead:** It builds a concrete local (`let mut chacha = ChaCha20::with_counter(*key, *nonce, 1);`) and calls inherent methods on it (`aead.rs:49,52,76`). It reaches the Poly1305 state through an `Option` projection (`self.state.as_mut().ok_or(..)?.update(input)`, `poly1305.rs:32`).
- **Why:** Ligature 1.4.1's `extract-c-static` uses a coarse syntactic extractor (supported forms: associated-path call, `self` method call, inherent call by name). It cannot infer a local's or projection's receiver type, so it classifies these four ordinary static calls as `possible-dispatch` with the default medium risk.
- **Impact:** The four sites are unresolved, so the AEAD package's `all-discovered-resolved` bridge requirement and G14 fail even though the Rust code has no dynamic dispatch. To clear them, either rewrite the calls in a form the extractor resolves (e.g. `ChaCha20::apply_keystream(&mut chacha, …)`), which changes source hashes and forces fresh Kani records, or resolve them through the sanctioned call-site workflow.
- **Status:** Resolved 2026-10-19 (#47): the four sites were respelled as associated-path calls, so the extractor reports 0 unresolved. Resolving them exposed three more undeclared cross-concept calls (`crypto-ligature-011`), now staged as interactions for approval.
- **Finding ids:** `crypto-ligature-008`, `crypto-ligature-011`
- **Generalizable lesson:** Gating on a syntactic call graph puts pressure on idiomatic Rust (method calls on typed locals, `?` chains) to be rewritten into explicit path calls. Budget for that rewrite, or for a type-aware extractor, before relying on "all call sites resolved".

### Ligature's extractor drops every method that returns an array

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** Botan's Poly1305 and AEAD code writes tags and keys into caller buffers (`final_result(uint8_t[])`), so no C++ function returns an array.
- **What the Rust port does instead:** Fixed-size results are returned by value: `ChaCha20Poly1305::tag`, `Poly1305::compute_tag`, `compute_tag_chunked`, `compute_tag_segments` and `finalize` return `[u8; 16]`; `ChaCha20::block` returns `[u8; 64]`.
- **Why:** Ligature 1.4.2's `extract-c-static` silently skips any method whose return type is an array, both as a caller and as a callee, and does not count the dropped calls as unresolved (upstream #170, local #150).
- **Impact:** The real AEAD-to-Poly1305 edge (`ChaCha20Poly1305::tag -> Poly1305::compute_tag_segments`) and every call inside `compute_tag*` were invisible to R1/G16, while the report claimed every discovered site resolved. A scratch probe with only the return types aliased shows the true graph: 35 discovered, 0 unresolved, and 5 undeclared cross-concept edges after the Poly1305 fold.
- **Status:** Escalated upstream. The hidden edge is declared anyway (`I-CRYPTO-MIXED-008`, staged), so nothing needs re-approving when the fix ships.
- **Finding ids:** `crypto-ligature-010`
- **Generalizable lesson:** Idiomatic Rust returns fixed-size crypto values by value. A syntactic extractor can trip on that form, so check the extractor against a type-aware call graph before trusting its discovered count.

### The Rust AEAD computes its tag differently from Botan's streaming MAC

- **Category:** Structural differences in the port
- **C++ construct / upstream location:** Botan's `ChaCha20Poly1305_Encryption::process_msg` / `finish_msg` stream the ciphertext into a member `m_poly1305` (`update`, then `final`), after keying it with `set_key` (`src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp` at `2a81eef56c96c237e590c27f9a75e60317c9c700`).
- **What the Rust port does instead:** `ChaCha20Poly1305::tag` derives the one-time key and calls `Poly1305::compute_tag_segments` once over the RFC 8439 MAC data (AAD, padding, ciphertext, padding, lengths). The Poly1305 accumulator, previously a separate private `Poly1305State` struct, is folded into `Poly1305` itself (2026-10-19, #47), matching Botan's single class. A differential test over 3000 random cases plus the Botan vector showed identical output.
- **Why:** One-shot segment authentication is simpler to verify than a stateful streaming protocol. The separate state struct made the extractor treat a private helper as its own concept, which added five cross-concept edges.
- **Impact:** The Stage 3 interactions `I-CRYPTO-MIXED-001` (encrypt -> `Poly1305::finalize`) and `-003` (encrypt -> `Poly1305::set_key`) describe Botan's structure and are never realized in Rust (R1 reports them as intent without realization). The real edge is declared by `I-CRYPTO-MIXED-008` with a new obligation, `Poly1305.C005` (segment tag = concatenation tag).
- **Status:** Open. Retiring 001/003 also affects `BR-CRYPTO-MIXED-001` and both manifests, so it is left for the owner after the current approval round.
- **Finding ids:** `crypto-ligature-010`, `crypto-ligature-011`
- **Generalizable lesson:** Stage 3 interactions drafted from the C++ call graph can describe a call structure the port deliberately changes. Re-derive the interaction set from the implemented Rust call graph before Stage 8A, not only from the upstream map.

### A stale, empty call-graph report passed R1/G16 and G14

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** Not applicable; this is a gate-input freshness gap in Ligature. It affects whether the port's call edges were checked against the declared interactions at all.
- **What the Rust port does instead:** Nothing changed in the port. The committed `ci/results/c_static/crates_crypto-mixed-core.json` came from the 2026-10-13 baseline (`2cbbccd`), before the port's source (`e0bd451`). It recorded 0 call sites, `local_concepts: []`, and no source binding.
- **Why:** Ligature 1.4.1's `gate-r1-g16` accepted that report (0 checked; declared interactions shown only as info) and `gate-g14` read it as 0 unresolved call sites. Nothing ties a C_static observation to the source it describes.
- **Impact:** Earlier crypto-mixed G14 results (2026-10-14 and the morning of 2026-10-18) released the cluster as degraded without validating any call site. A fresh extraction blocks G14 and exposes three undeclared cross-concept calls.
- **Status:** Open; filed as local #149 / ligature-workspace #169. The fresh report is kept as the current observation.
- **Finding ids:** `crypto-ligature-006`
- **Generalizable lesson:** Any analysis artifact a gate consumes must be bound to the source revision it describes. An empty observation is the easiest stale input to miss, because it looks like "nothing to check".

### P3 deliberately uses bounded Kani evidence; Verus is deferred

- **Category:** Unprovable or costly obligations
- **C++ construct / upstream location:** ChaCha20 quarter-round and block in `src/lib/stream/chacha/chacha.cpp:30-43,134-230`; Poly1305 initialization and limb arithmetic in `src/lib/mac/poly1305/poly1305.cpp:93-160`; AEAD composition in `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp:110-166` at Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`.
- **What the Rust port does instead:** P3 assigns ChaCha20, Poly1305, and ChaCha20-Poly1305 to Kani 0.67.0. The five accepted records and their precise bounds are listed under Current P3 assurance result.
- **Why:** The approved P3 policy selects Kani-only bounded evidence and defers deductive Verus assurance to P4.
- **Impact:** The current reports do not establish arbitrary-length behavior, type-universal generic-callee coverage, SIMD/provider parity, or side-channel behavior.
- **Status:** Ruled-scope-cut for P3; Verus inclusion remains a distinct P4 task.
- **Finding ids:** `crypto-kani-001`
- **Generalizable lesson:** Record each verifier result's actual domain. A bounded result must not be presented as a deductive or unbounded claim.

### Dynamic-length ChaCha20.C002 verification timed out

- **Category:** Unprovable or costly obligations
- **C++ construct / upstream location:** ChaCha20 stream processing in `src/lib/stream/chacha/chacha.cpp:134-230` at pinned Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`.
- **What the Rust port does instead:** The accepted C002 record uses `kani_chacha20_c002_exact_length_65_boundary`, with symbolic key, nonce, and 65-byte contents. A separate `Vec` harness for symbolic lengths 0 through 65 timed out at 180 seconds.
- **Why:** Kani 0.67.0 did not finish the dynamic-`Vec` proof within the run limit.
- **Impact:** The P3 claim covers the exact 65-byte harness model, not all lengths from 0 through 65 or the full RFC 8439 message domain.
- **Status:** Ruled-scope-cut from the P3 minimum scope; the broader proof remains unestablished.
- **Finding ids:** `crypto-kani-002`
- **Generalizable lesson:** When a dynamic input proof times out, name the smaller harness that did pass and keep the discarded length range out of the claim.

### Dynamic-vector ChaCha20.C003 verification timed out

- **Category:** Unprovable or costly obligations
- **C++ construct / upstream location:** ChaCha20 counter capacity in `src/lib/stream/chacha/chacha.cpp:134-230` and the AEAD length guard in `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp:110-166` at pinned Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`.
- **What the Rust port does instead:** A dynamic-`Vec` harness with symbolic starting counter and lengths up to 65 bytes timed out at 180 seconds. The accepted C003 harness instead quantifies a symbolic target `usize` requested length for the fixed counter-one AEAD case and checks the exact guard implication recorded in the manifest.
- **Why:** The attempted vector/counter state space did not finish within the Kani run limit.
- **Impact:** The accepted C003 claim is limited to its named counter-one harness model. The timed-out harness's arbitrary starting-counter behavior is not established by this record.
- **Status:** Ruled-scope-cut from the P3 minimum scope; the broader starting-counter proof remains unestablished.
- **Finding ids:** `crypto-kani-003`
- **Generalizable lesson:** Keep the verified call-site precondition separate from a broader state-space proof that timed out; one does not imply the other.

### Symbolic Poly1305 chunked-versus-one-shot equivalence timed out

- **Category:** Unprovable or costly obligations
- **C++ construct / upstream location:** Streaming Poly1305 block processing and finalization in `src/lib/mac/poly1305/poly1305.cpp:93-160` at pinned Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`.
- **What the Rust port does instead:** The accepted Poly1305.C002 harness calls one-shot `compute_tag` with symbolic messages of lengths 0 through 65 and checks tag length. Concrete pinned-vector checks at split offsets 15, 16, 17, 32, 64, and 73 passed.
- **Why:** Kani 0.67.0 did not finish the symbolic 8-byte message and symbolic valid split-point equivalence proof within 180 seconds.
- **Impact:** The report does not prove the public streaming `finalize` lifecycle or chunked-versus-one-shot equivalence for symbolic messages.
- **Status:** Open; these properties are outside the current P3 manifest claim.
- **Finding ids:** `crypto-kani-004`
- **Generalizable lesson:** Fixed-vector boundary checks are useful evidence for those vectors, but they do not replace a symbolic equivalence proof over the declared split domain.

### Symbolic ChaCha20-Poly1305 round-trip verification timed out

- **Category:** Unprovable or costly obligations
- **C++ construct / upstream location:** AEAD encryption, authentication, and decryption in `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp:110-166` at pinned Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`.
- **What the Rust port does instead:** Separate pinned-vector checks cover concrete encryption, verify/decrypt, and tampered-tag rejection cases. The symbolic one-byte round-trip harness remains in the port but did not complete.
- **Why:** Kani exceeded the 180-second run limit for symbolic key, nonce, AAD, and plaintext values.
- **Impact:** No symbolic AEAD round-trip property is claimed by the current reports.
- **Status:** Open; the concrete pinned-vector results do not establish the symbolic round-trip property.
- **Finding ids:** `crypto-kani-005`
- **Generalizable lesson:** Separate concrete test-vector evidence from symbolic proof coverage when documenting cryptographic assurance.

### Generic-callee coverage is capped at per-instantiation under Kani (CG3)

- **Category:** Unprovable or costly obligations
- **C++ construct / upstream location:** Botan's AEAD holds its primitives behind abstract interfaces, `std::unique_ptr<StreamCipher> m_chacha` and `std::unique_ptr<MessageAuthenticationCode> m_poly1305` (`src/lib/modes/aead/chacha20poly1305/chacha20poly1305.h:52-53`). It builds them by name through factories (`chacha20poly1305.cpp:20`) and calls them through virtual dispatch, e.g. `m_chacha->write_keystream` / `m_poly1305->set_key` (`chacha20poly1305.cpp:55,88,90,112`), at Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`.
- **What the Rust port does instead:** `crypto-mixed-core` calls the concrete `ChaCha20` and `Poly1305` types directly, with no trait objects, factories, or production generics. The only generic item in the crate is the Kani test helper `decode_hex<const N: usize>`. Bridges `BR-CRYPTO-MIXED-001` (Poly1305 key from ChaCha counter zero) and `BR-CRYPTO-MIXED-002` (counter-one capacity) are checked by Kani for the concrete instantiation the harnesses build.
- **Why:** Kani checks monomorphized code within harness bounds. Ligature's closure condition `generic_callees_type_universal_or_creusot_owned` needs type-universal or deductive evidence, so Kani evidence caps it at the `per-instantiation` ceiling (capability gap CG3). Ligature's `extract-c-static` reports 16 discovered / 12 resolved / 4 unresolved with `discovered-lower-bound` completeness. The four unresolved `possible-dispatch` sites (`aead.rs:49,52,76`, `poly1305.rs:32`) are method calls whose receiver type the syntactic extractor did not infer. So the tooling cannot mechanically prove that no generic callee exists.
- **Impact:** G14 releases the `crypto-kani` cluster as **degraded**, not closed, under the reviewed record `specs/_closure/crypto-kani.degradation.json`. The bridge claims hold for the verified concrete instantiation only. Nothing is claimed for other `StreamCipher`/`MessageAuthenticationCode` implementations or for type-universal behavior. Upgrading this would need a Verus-owned (deductive) proof over an enumerated call-target set.
- **Status:** Ruled-scope-cut. Operator decision 2026-10-18 on #135 (option B): accept the per-instantiation degradation as the final P3 limitation. #135 is the tracking issue to reopen for P4/Verus work.
- **Finding ids:** `crypto-kani-006`
- **Generalizable lesson:** Replacing C++ virtual or factory dispatch with concrete Rust types makes bounded model checking practical, but a model checker still proves only the instances it runs. A closure that demands type-universal coverage needs a deductive verifier or an explicit, reviewed degradation. A lower-bound call-graph extractor cannot by itself prove that no generic callee exists.

## Ligature findings fixed or worked around in this pilot

### Kani assurance intake was missing

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** Not applicable; this was a Ligature Stage 7/G14 intake gap for Kani assurance.
- **What the Rust port does instead:** The pilot now uses Ligature's supported exact-harness Kani intake and stores source- and harness-bound records in the work-package reports.
- **Why:** Ligature 1.3.6 documented Creusot and Verus paths but did not provide Kani assurance intake.
- **Impact:** The original workflow could not produce per-obligation reports for G14. The current 1.3.11 bundle records the three approved Kani obligations and G14 rechecks them.
- **Status:** Fixed in Ligature and verified in this pilot.
- **Finding ids:** `crypto-ligature-001`
- **Generalizable lesson:** Every verifier declared in a work package needs a documented, fail-closed path from fresh verifier execution to a source-bound assurance record.

### Successful Kani runs with ancillary `UNREACHABLE` checks were rejected

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** Poly1305 tag computation for the streaming implementation in `src/lib/mac/poly1305/poly1305.cpp:93-160`; the intake defect itself was in Ligature's Kani result interpretation.
- **What the Rust port does instead:** The pilot records the successful named Poly1305 assertion and preserves the nine ancillary unreachable checks in the report.
- **Why:** Ligature 1.3.9 treated every unreachable ancillary check as failure despite a complete successful run and a successful named obligation assertion.
- **Impact:** The prior intake rejected a valid bounded run. Ligature 1.3.10 changed recording and G14 interpretation; the current report has 724 successful checks, 9 unreachable checks, and G14 consumes it under the approved bounded scope.
- **Status:** Fixed in Ligature 1.3.10 and verified in this pilot.
- **Finding ids:** `crypto-ligature-002`
- **Generalizable lesson:** Assurance adapters must distinguish failed claims from ancillary unreachable checks and preserve the backend's actual result summary.

### Kani bridge dispatch needed a configured backend and bridge-only report path

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** AEAD Poly1305 key setup and ChaCha counter capacity in `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp:55,90,110` at pinned Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`.
- **What the Rust port does instead:** The project descriptor configures `crates/crypto-mixed-core/tests/kani_bridge_backend.py`, which checks each generated bridge ID and runs its exact source harness. Ligature records the two passing G9 results; `record-assurance --bridges-only` assembles the AEAD package report from those records.
- **Why:** The initial descriptor lacked a Kani backend command, and ordinary obligation intake could not assemble a report for a package with bridges but no provided guarantees.
- **Impact:** Before configuration and bridge-only report support, the generated bridge harnesses were not checked and G14 lacked their records. Both bridge checks now pass and their records are present in the AEAD report.
- **Status:** Fixed in this pilot with the configured adapter and Ligature 1.3.11 bridge-only intake; the adapter remains project-specific.
- **Finding ids:** `crypto-ligature-003`
- **Generalizable lesson:** A generated bridge harness needs an actual verifier dispatch and a supported report path before its result can count as bridge evidence.

### Locked Kani intake needed an authorized Cargo.lock path

- **Category:** Tooling blind spots in the transfer
- **C++ construct / upstream location:** ChaCha20 stream processing in `src/lib/stream/chacha/chacha.cpp:134-230` and Poly1305 arithmetic in `src/lib/mac/poly1305/poly1305.cpp:93-160` at pinned Botan commit `2a81eef56c96c237e590c27f9a75e60317c9c700`; the prerequisite was Cargo metadata for Kani intake.
- **What the Rust port does instead:** The crate has the normal generated `crates/crypto-mixed-core/Cargo.lock`, authorized for the exact protected path. Cargo metadata and Kani intake run with `--locked`; Kani build output is directed outside the checkout.
- **Why:** Ligature's reproducible Kani intake requires `cargo metadata --locked`; the crate initially had no lockfile and its write policy did not permit creating one.
- **Impact:** Without an approved lockfile path, assurance recording stopped before Kani ran. The current lockfile SHA-256 is `500245d4c61242e614363a03597f8c88f7c827d02115ffbc92f8dabd774f5fc1`.
- **Status:** Worked around in the pilot through reviewed write authorization; Ligature source was not changed for this finding.
- **Finding ids:** `crypto-ligature-004`
- **Generalizable lesson:** Reproducible verifier intake depends on both locked dependency resolution and an approved path for creating and retaining the lockfile.

## Remaining review items

- The `per-instantiation` CG3 degradation is the operator-accepted final P3 limitation (#135, 2026-10-18). Do not relabel its Kani records as type-universal; reopen #135 for P4/Verus work.
- Complete Stage 8A call-site validation (#47) against the fresh C_static report: four unresolved `possible-dispatch` sites and three undeclared cross-concept calls currently block G14.
- Keep the Codesight header, call-graph, and template gaps and the Tilth call-site attribution limitation visible for upstream triage.
- Keep the broader timed-out Kani attempts, scalar-only provider scope, and omitted side-channel claims distinct from defects in Ligature's assurance intake.
