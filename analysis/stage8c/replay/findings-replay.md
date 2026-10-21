# crypto-mixed findings replay (chainlink #49, Stage 8C)

Independent replay of every entry in `findings/limitations.jsonl` (31 entries) of the crypto-mixed pilot, frozen at commit `6a55894`. The replaying agent did not write any of these findings and judged them only on observed output. Run on 2026-10-20.

## Method

- **Copies:** every finding got a fresh `rsync -a` copy of the frozen baseline at `stage8c-replay/work/<id>/ws/crypto-mixed/`, with `ws/tools` symlinked read-only to the workspace `tools/`. Each copy was deleted after its result was logged.
- **Historical states:** these were rebuilt inside the copy with `git checkout <commit>`, by restoring single files from history, or by extracting an older `ligature.pyz` from the copy's own history. Bundles used: 1.3.6 from 2cbbccd, 1.3.9 from c74cf6a, 1.3.10 from d391ad4/3296758, 1.3.11 from 201745b, 1.4.0 from 13e6021, 1.4.1 from 2f2152d, 1.4.2 at the baseline. Two states were never committed. The "#47 respelled, Poly1305State not yet folded" state behind crypto-ligature-010/011 was rebuilt as 74ff591 plus the four respellings, because 6667510 also contains the fold.
- **Toolchain:** `nix develop path:/home/goya/storage/full-ligature-port-workspace#crypto-mixed` (rustc 1.95.0, clang 21.1.7 with libstdc++ 14.3.0, CMake 4.1.2), cargo-kani 0.67.0, cargo-nextest 0.9.133 and rdb 0.0.0 from `~/.cargo/bin`, codesight-mcp from the workspace venv (run with `PYTHONDONTWRITEBYTECODE=1`). The Tilth MCP tools were available to the replaying agent.
- **Ligature:** run only as `python3 -I <copy>/tools/ligature/ligature.pyz ...`. No bundle was opened and the Ligature source tree was not read. No human-checkpoint verb was run.
- **Kani:** one harness at a time. `CARGO_TARGET_DIR` was always under `stage8c-replay/kani-target/`; Ligature-driven Kani reruns used Ligature's own `/tmp/ligature-kani-067-*` dirs. Recorded 180 s timeouts were replayed with `timeout 180`.
- **Oracle build:** the Botan subset and driver were rebuilt with `CRYPTO_MIXED_ORACLE_BUILD=stage8c-replay/oracle-build oracle/build_upstream.sh`. `/tmp/crypto-mixed-oracle-build` was only read and executed.
- **Logs:** full output is in `logs/<id>.log`, plus side files such as `logs/<id>.direct-kani.log`, `logs/<id>.*.json` and `logs/<id>.ptree-*.log`.

## Environment notes and incidents

- **Shared host:** load average was 10-13 throughout. Another actor ran Ligature/Kani against the live pilot during the replay (`cargo-kani --manifest-path /home/goya/storage/full-ligature-port-workspace/crypto-mixed/...`). This can only lengthen runtimes. It cannot turn a recorded timeout into a pass.
- **Read-only cache emulated:** the home grammar cache is writable here, and an unprivileged read-only bind mount was refused. crypto-mcp-001 therefore used a `chmod a-w` copy of the cache, which gives errno 13 instead of the recorded errno 30.
- **Script bug, fixed:** a replay-script bug made three steps (crypto-ligature-003 first pass, crypto-oracle-004 first pass, crypto-rdb-002 first pass) run with cwd = `$HOME` after the copy helper failed on a deleted cwd. Every command in those steps failed on missing relative paths. `$HOME` is not a git repository, so the `git checkout`/`git clean` calls were refused. A check found no new files in `$HOME`. The helper was fixed (it now `cd`s to the replay root and aborts on failure), and all three findings were rerun cleanly. Both passes stay in the logs.
- **Writes outside the replay dirs:** one probe (`touch` + `rm`) checked whether `~/.cache/tree-sitter-language-pack/v1.20.0` is writable. `/tmp/crypto-mixed-codesight-cache` was created as the repro_cmds name it (a copy of the grammar bundle) and deleted at the end. Short-lived `/tmp/s8c-rdb-*` and `/tmp/claude-.../scratchpad/rdb-adapted.txt` were also created; the `/tmp/s8c-rdb-*` copy has been deleted. Nothing was written under the workspace, chainlink was not used, and no other pilot root was touched; only date-creusot's `oracle/driver.cpp` and `upstream/date/include` were read, for crypto-oracle-003.

## Possible new Ligature defects (for epic #1 triage; not filed)

1. **write-set-check does not enforce protected_roots.** At d401338 (1.4.2, `oracle/**` protected), `write-set-check --issue 48` reports `write set is clean`, exit 0, both for new files under `oracle/` and for an edit to tracked `oracle/oracle-PROTOCOL.md`. The files appear only under `protected_unvouched`, marked "audit only -- ... this verdict does not cover them". A protected-root write is therefore not a violation (see crypto-ligature-013).
2. **Duplicate R1/G14 findings for one unresolved condition.** On 1.4.1 with the fresh C_static, `gate-g14` emits the WP-AEAD `all-discovered-resolved` error once per bridge, `check --issue 134` repeats it, and the same 4 sites also appear as possible-dispatch findings. This is minor noise (crypto-ligature-006).

The 1.3.x-1.4.1 defects in the ledger (008, 010, 002, 003, 004, 005, 006, 007) were all re-observed. Of these, 002, 003, 004, 005, 006 and 007 are no longer present on 1.4.2 at the baseline. 010 (array-return methods skipped by extract-c-static) is still present on 1.4.2. 009 (closed evidence-kind enum) is still present.


## Verdict counts

| Verdict | Count |
|---|---|
| REPRODUCED | 23 |
| REPRODUCED-RESOLVED | 4 |
| PARTIAL | 3 |
| NOT-REPRODUCED | 0 |
| NOT-RUNNABLE(ENV) | 0 |
| NOT-RUNNABLE(HUMAN) | 1 |
| NOT-RUNNABLE(PROSE) | 0 |
| **Total** | **31** |

## Per-finding summary

| ID | Tool | Recorded exit | Observed exit | Verdict | Reason |
|---|---|---|---|---|---|
| crypto-mcp-001 | mcp | 1 | 1 | REPRODUCED-RESOLVED | CacheLockError, exit 1 with a non-writable grammar cache (emulated, errno 13 vs recorded 30); workaround cache gives 1,199 files / 15,643 symbols |
| crypto-mcp-002 | mcp | 1 | 1 | REPRODUCED | All three headers: exit 1 'File not found in index' (they are absent from the index); type-hierarchy 'Symbol not found' |
| crypto-mcp-003 | mcp | 0 | 0 | REPRODUCED | Callees of ChaCha::chacha include false edge store_le at idea_avx2.cpp:38 plus real chacha_quarter_round |
| crypto-mcp-004 | mcp | 0 | 0 | REPRODUCED | get-callees returns only cipher1; get-symbol shows m_poly1305->update; call-chain to Poly1305::add_data path_count 0 |
| crypto-mcp-005 | mcp | 0 | 0 | REPRODUCED | SIMD outlines: module entry only / raw() only; template hits at avx512.cpp:42,68; 8 BOTAN_HAS_CHACHA_* guards |
| crypto-mcp-006 | mcp | 0 | 0 | REPRODUCED | Tilth attributes all 7 hits (incl. 113, 156) to ChaCha20Poly1305_Mode::update_len; the lines sit in the two process_msg methods |
| crypto-kani-001 | kani | 0 | 0 | REPRODUCED | cargo-kani 0.67.0; descriptor default=kani, closure_kind=bounded; 3 concepts verifier=kani in crypto-kani |
| crypto-kani-002 | kani | 124 | 124 | REPRODUCED | timeout 180: exit 124, still in symbolic execution (baseline; chacha20.rs unchanged since e0bd451) |
| crypto-kani-003 | kani | 124 | 124 | REPRODUCED | timeout 180: exit 124, still in symbolic execution |
| crypto-kani-004 | kani | 124 | 124 | REPRODUCED | timeout 180: exit 124 in SAT solving, at the baseline and at e0bd451 |
| crypto-kani-005 | kani | 124 | 124 | REPRODUCED | timeout 180: exit 124 in SAT solving (128k VCCs), at the baseline and at e0bd451 |
| crypto-ligature-001 | ligature | 0 | 0 | REPRODUCED | 1.3.6 record-assurance --help lists only --proof/--verus-*; no Kani intake (1.4.2 has --kani-harness) |
| crypto-ligature-002 | ligature | 1 | 1 | REPRODUCED | 1.3.9 record-assurance exit 1 'Kani did not prove every check'; direct Kani 0 of 733 failed (9 unreachable); G14 exit 1 |
| crypto-ligature-003 | ligature | 1 | 1 | REPRODUCED | 1.3.10 check-bridges exit 1 with two [G9/error] no verifier_backends.kani; BR ids rejected; bridge_001 0/418 failed |
| crypto-ligature-004 | ligature | 2 | 2 | REPRODUCED | 1.3.10 record-assurance exit 2 'Cargo metadata with --locked failed'; offline Cargo.lock is out-of-set; fixed at baseline |
| crypto-ligature-005 | ligature | 0 | 0 | REPRODUCED | 1.4.1 status reruns 2 Kani harnesses (~6.4 GB cbmc), exit 0 after 404 s, 23,264 B JSON; 20 s bound gives 124 with no output; 1.4.2 takes 4 s |
| crypto-kani-006 | kani | 0 | 0 | REPRODUCED | G14 exit 0 with CG3 degraded and accepted (per-instantiation, chainlink:135) at baseline and recording state; recording-state exit 0 needed the stale C_static |
| crypto-ligature-006 | ligature | 0 | 0 | REPRODUCED | Stale empty C_static: R1/G16 and G14 exit 0; fresh 16/12/4: G14 exit 1 (all-discovered-resolved, G17 0 vs 4); fixed in 1.4.2 (G1b refuses) |
| crypto-ligature-007 | ligature | 1 | 1 | REPRODUCED | 1.3.11/1.4.0/1.4.1: G9 needs ci/harness files that write-set-check flags (exactly 2), tracked or not; 1.4.2 baseline clean + G9 pass |
| crypto-ligature-008 | ligature | 0 | 0 | REPRODUCED-RESOLVED | 13e6021+1.4.1: 16/12/4, possible-dispatch at aead.rs:49/52/76 and poly1305.rs:32 (medium); baseline 18/18/0 |
| crypto-ligature-009 | ligature | 1 | 1 | REPRODUCED | validate-interaction exit 1: 'dudect-constant-time-test' is not one of the 3 built-in kinds |
| crypto-ligature-010 | ligature | 0 | 0 | REPRODUCED | Array-return methods skipped: 16->21 discovered, 217->204 unattributed on the rebuilt state; same +5 IDs at baseline (18->23) |
| crypto-ligature-011 | ligature | 1 | 1 | REPRODUCED-RESOLVED | Rebuilt pre-fold state: 16/16/0, gate-r1-g16 exit 1 with the 6 recorded undeclared calls; baseline exit 0 |
| crypto-ligature-012 | ligature | 2 | n/a | NOT-RUNNABLE(HUMAN) | Needs approve/record-ruling/accept-promotion + human grant + missing plan file; workaround verified (shared scope, harness 0/34 failed) |
| crypto-rdb-001 | rdb | 100 | 100 | PARTIAL | Divergence and pre-ruling 1367/3 reproduce, ruling state 1370/1370; verbatim rdb script fails (hard-coded 0x2111f0 is build-path dependent) |
| crypto-rdb-002 | rdb | 0 | 0 | PARTIAL | With an adapted address: rdi=hidden ret ptr, rsi=&self, rdx=0x3fffffffc1; stack not randomized across runs here; verbatim address wrong |
| crypto-oracle-001 | oracle | 0 | 0 | REPRODUCED | make_cases.py: 1,606 not translated with the exact breakdown; test-map 6 mapped / 27 unmapped / 1 rust-only |
| crypto-oracle-002 | oracle | 2 | 2 | REPRODUCED-RESOLVED | configure --cc=gcc warns 'CLANG 21 1' and uses clang++; make from pilot root: No rule for src/lib/base/buf_comp.cpp (exit 2); workaround builds |
| crypto-oracle-003 | oracle | 2 | 1 | PARTIAL | clang21+libstdc++14 C++20 rejects pair<string,JsonValue> (complete-class assertion), C++17 accepts; 4-5 errors, not 7 |
| crypto-ligature-013 | ligature | 0 | 0 | REPRODUCED | validate-work-package exit 0 on both manifests despite stale protected oracle/**; write-set-check --issue 48 clean |
| crypto-oracle-004 | oracle | 0 | 0 | REPRODUCED | Same-seed regeneration byte-identical; 200 ok, 195 auth_failed + 5 too_short; nextest 2580/2580 |

## Ledger defects (32)

- **crypto-mcp-001**: repro_cmd omits its precondition (a read-only shared grammar cache). Run verbatim on a host where ~/.cache is writable it would not fail, and it would write a lock file under the home cache.
- **crypto-mcp-001**: Follow-on repro_cmds (crypto-mcp-002..005) hard-code repo id local/botan-9e173108f3f6, which only exists in the committed index; re-indexing from another path yields a different id.
- **crypto-mcp-004**: repro_cmd covers only the get-callees step; the get-symbol and get-call-chain steps that support the 'actual' text are not given as commands (symbol IDs recoverable from analysis/codesight/*.json).
- **crypto-mcp-005**: repro_cmd gives only the chacha_avx2 outline; the other outlines and the two search-text queries (file patterns) are prose in 'actual'.
- **crypto-mcp-006**: pyz_sha256 for a Tilth (non-Ligature) finding records the 1.3.6 Ligature bundle hash; irrelevant to the tool under test (same pattern on all mcp/kani entries).
- **crypto-kani-001**: repro_cmd (cargo kani --version) only checks the version; the descriptor/concept facts in 'actual' need file inspection that the repro does not name.
- **crypto-kani-002**: repro_cmd records the bound only as prose ('ctx_execute stopped the run at 180 seconds'); it should be `timeout 180 cargo kani ...` so the exit 124 is reproducible as a command.
- **crypto-kani-003**: repro_cmd records the bound only as prose ('ctx_execute stopped the run at 180 seconds'); it should be `timeout 180 cargo kani ...` so the exit 124 is reproducible as a command.
- **crypto-kani-004**: repro_cmd records the bound only as prose ('ctx_execute stopped the run at 180 seconds'); it should be `timeout 180 cargo kani ...` so the exit 124 is reproducible as a command.
- **crypto-kani-005**: repro_cmd records the bound only as prose ('ctx_execute stopped the run at 180 seconds'); it should be `timeout 180 cargo kani ...` so the exit 124 is reproducible as a command.
- **crypto-ligature-001**: repro_cmd does not name the 1.3.6 bundle or commit; run verbatim at the baseline it shows a Kani intake and silently contradicts the finding. Entry should be marked resolved (Kani intake added by 1.3.9/1.3.10).
- **crypto-ligature-002**: repro_cmd names neither the commit (c74cf6a) nor the bundle; run verbatim at the baseline it would not fail. Entry should be marked resolved.
- **crypto-ligature-003**: 'passed 0 of 418 checks with 4 unreachable' is misworded: Kani reports 0 of 418 FAILED (414 SUCCESS, 4 UNREACHABLE).
- **crypto-ligature-003**: repro_cmd names the 1.3.10 bundle but not the commit; entry should be marked resolved (verifier_backends.kani added in 4d66e69).
- **crypto-ligature-004**: The entry should be marked resolved (Cargo.lock committed in 4d66e69 and added to protected_roots). The repro_cmd names the 1.3.10 bundle but not the commit (d391ad4/3296758) needed to get a tree without Cargo.lock.
- **crypto-ligature-005**: 'HEAD 13e6021 + 1.4.1 install' leaves out the uncommitted fresh C_static that the recorded run had (committed later in 2f2152d); without it the output differs (14,465 bytes, cluster degraded instead of blocked).
- **crypto-ligature-005**: Entry should note that 1.4.2 status no longer reruns Kani (4 s at the baseline).
- **crypto-kani-006**: 'actual' combines exit 0 with 'extract-c-static ... 4 unresolved possible-dispatch sites', but those come from two different C_static states: with the 4-unresolved report, 1.4.1 G14 exits 1. The recorded exit 0 is the vacuous stale-report result that crypto-ligature-006 later identified.
- **crypto-ligature-006**: Entry should be marked resolved in 1.4.2 (source-bound C_static; the legacy report is refused by G1b/G14).
- **crypto-ligature-007**: Entry should be marked resolved at 1.4.2/f4ca347. The repro_cmd lists 'released 1.3.12', a bundle that is not in the pilot's history and cannot be replayed from it.
- **crypto-ligature-010**: The recorded counts come from a state that is not a commit (respelling and the Poly1305State fold both landed in 6667510). The repro gives no commit, and at any commit 'reports 16 discovered' fails (it reports 18).
- **crypto-ligature-010**: repro_cmd does not say that a `type TagBytes = [u8; 16];` alias must be added for the crate to compile.
- **crypto-ligature-011**: repro_cmd names no state; run verbatim at the baseline it exits 0. The recorded state was never committed (6667510 also folds Poly1305State), so only a hand reconstruction reproduces the 16 discovered / 6 undeclared result.
- **crypto-ligature-012**: repro_cmd and 'command' reference a placeholder plan path (<stage7-plans-v2>/stage-7-plan-...-issue-134.json) and grant (<grant>) that are not recorded anywhere in the pilot, so the refusal cannot be replayed even by a human without recreating the plan.
- **crypto-rdb-001**: repro_cmd's rdb script (oracle/divergences/.../rdb-commands.txt) hard-codes `break 0x2111f0`, which is only valid for the original build directory. It should look the address up with nm, or break on the symbol.
- **crypto-rdb-001**: exit_code 100 is nextest's (from 'command'), not that of the repro_cmd (cargo build + rdb exit 0).
- **crypto-rdb-001**: rdb exits 0 even when its commands fail (ESRCH), so an exit-code check cannot catch a broken replay.
- **crypto-rdb-002**: repro_cmd hard-codes break 0x2111f0 (not valid outside the original build path) and assumes target/repro/debug/oracle_repro has already been built (missing build step and cwd oracle/rust-check).
- **crypto-oracle-002**: repro_cmd only covers the make-from-pilot-root half and depends on a pre-existing /tmp/crypto-mixed-oracle-build Makefile; the --cc=gcc half needs the configure command from 'command'. It must be run from the workspace root ('cd crypto-mixed').
- **crypto-oracle-003**: repro_cmd is prose with no translation unit or command line, so the '7 errors' count cannot be pinned down.
- **crypto-oracle-003**: exit_code 2 belongs to the `cmake --build` in 'command', not to the clang++ compile the repro describes (clang++ exits 1).
- **crypto-ligature-013**: The ledger 'command' (write-set-check --issue 48 --json) and repro_cmd (validate-work-package ...) are different commands; exit_code 0 holds for both, so nothing is wrong, but the pairing is confusing.

## Per-finding detail

### crypto-mcp-001 (mcp): REPRODUCED-RESOLVED

Recorded exit 1; observed exit 1. Full log: `logs/crypto-mcp-001.log`.

Commands run:

- `rm -rf analysis/codesight/index (copy only; pre-index state)`
- `cp -a ~/.cache/tree-sitter-language-pack <work>/ro-cache/ && chmod -R a-w <work>/ro-cache   # emulates the read-only shared cache`
- `XDG_CACHE_HOME=<work>/ro-cache CODE_INDEX_PATH="$PWD/analysis/codesight/index" CODESIGHT_ALLOWED_ROOTS="$PWD/upstream:$PWD/rust" ../tools/codesight-mcp/.venv/bin/codesight-mcp index-folder --path "$PWD/upstream/botan" --format json --use-ai-summaries false`
- `XDG_CACHE_HOME=<work>/ro-cache ../tools/codesight-mcp/.venv/bin/python -c "import tree_sitter_language_pack as t; t.get_parser('cpp')"`
- `workaround: same index-folder with XDG_CACHE_HOME=<work>/rw-cache (writable copy of the grammar bundle)`

Decisive output: Attempt 1: `[codesight-mcp] Sanitized error: CacheLockError`, {"success": false, "error": "An internal error occurred"}, exit 1; analysis/codesight/index not created. Direct parser call: `tree_sitter_language_pack.CacheLockError: Download cache lock error: open lock file <ro-cache>/tree-sitter-language-pack/v1.20.0/.download.lock: Permission denied (os error 13)`. Workaround: exit 0, success true, file_count 1199, symbol_count 15643, warning 'Skipped 706 secret file(s)'.

Notes: The read-only condition had to be emulated: in this environment ~/.cache/tree-sitter-language-pack is writable, and an unprivileged read-only bind mount was refused (unshare: uid_map not permitted), so the cache copy was made non-writable with chmod. Hence errno 13 (Permission denied) instead of the recorded errno 30 (Read-only file system); the failure path and sanitized CacheLockError are identical. The re-index got repo id local/botan-cdffbf00a8e0 (the id depends on the indexed path), not local/botan-9e173108f3f6.

Ledger defects:

- repro_cmd omits its precondition (a read-only shared grammar cache). Run verbatim on a host where ~/.cache is writable it would not fail, and it would write a lock file under the home cache.
- Follow-on repro_cmds (crypto-mcp-002..005) hard-code repo id local/botan-9e173108f3f6, which only exists in the committed index; re-indexing from another path yields a different id.

### crypto-mcp-002 (mcp): REPRODUCED

Recorded exit 1; observed exit 1. Full log: `logs/crypto-mcp-002.log`.

Commands run:

- `XDG_CACHE_HOME=/tmp/crypto-mixed-codesight-cache CODE_INDEX_PATH="$PWD/analysis/codesight/index" CODESIGHT_ALLOWED_ROOTS="$PWD/upstream:$PWD/rust" ../tools/codesight-mcp/.venv/bin/codesight-mcp get-file-outline --repo local/botan-9e173108f3f6 --file-path {src/lib/stream/chacha/chacha.h, src/lib/mac/poly1305/poly1305.h, src/lib/modes/aead/chacha20poly1305/chacha20poly1305.h} --repo-path "$PWD/upstream/botan" --format json`
- `same env: get-type-hierarchy --symbol-id 'src/lib/stream/chacha/chacha.cpp::Botan.ChaCha#type' and 'src/lib/mac/poly1305/poly1305.cpp::Poly1305#type'`
- `python3: membership of the three headers in the index's source_files`

Decisive output: All three get-file-outline calls: exit 1, {"error": "File not found in index"}. get-type-hierarchy: exit 1, "Symbol not found: src/lib/stream/chacha/chacha.cpp::Botan.ChaCha#type" and "...poly1305.cpp::Poly1305#type". Index source_files (1,199) contains none of the three headers although it contains 192 other .h files and chacha.cpp.

Notes: Replayed against the committed index (analysis/codesight/index, indexed_at 2026-10-12, git_head 2a81eef); index unchanged by the queries. Supplementary: the headers are absent from the index's source_files, not merely un-outlined.

### crypto-mcp-003 (mcp): REPRODUCED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-mcp-003.log`.

Commands run:

- `XDG_CACHE_HOME=/tmp/crypto-mixed-codesight-cache CODE_INDEX_PATH="$PWD/analysis/codesight/index" CODESIGHT_ALLOWED_ROOTS="$PWD/upstream:$PWD/rust" ../tools/codesight-mcp/.venv/bin/codesight-mcp get-callees --repo local/botan-9e173108f3f6 --symbol-id 'src/lib/stream/chacha/chacha.cpp::Botan.ChaCha::chacha#method' --max-depth 2 --format json`
- `sed -n '30,45p' upstream/botan/src/lib/block/idea/idea_avx2/idea_avx2.cpp`

Decisive output: callee_count 2: store_le (src/lib/block/idea/idea_avx2/idea_avx2.cpp line 38, depth 1) and chacha_quarter_round (chacha.cpp line 30). idea_avx2.cpp:38 is `void BOTAN_FN_ISA_AVX2 store_le(uint8_t out[]) const` inside SIMD_16x16, unrelated to ChaCha (chacha.cpp:215 calls Botan's free store_le).

Notes: Exact match with the recorded actual.

### crypto-mcp-004 (mcp): REPRODUCED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-mcp-004.log`.

Commands run:

- `<env> codesight-mcp get-callees --repo local/botan-9e173108f3f6 --symbol-id 'src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp::Botan.ChaCha20Poly1305_Encryption::process_msg#method' --max-depth 3 --format json`
- `<env> codesight-mcp get-symbol --repo local/botan-9e173108f3f6 --symbol-id '<same>' --repo-path "$PWD/upstream/botan" --format json`
- `<env> codesight-mcp get-call-chain --repo local/botan-9e173108f3f6 --from-symbol '<same>' --to-symbol 'src/lib/mac/poly1305/poly1305.cpp::Poly1305::add_data#function' --repo-path "$PWD/upstream/botan" --format json`

Decisive output: get-callees: callee_count 1, only cipher1 (src/lib/stream/stream_cipher.h:110). get-symbol source contains `m_poly1305->update(buf, sz);  // poly1305 of ciphertext`. get-call-chain: path_count 0, paths [].

Notes: Exact match. The get-call-chain to_symbol id is the one saved in analysis/codesight/chain-encrypt-poly.json (the repro_cmd itself only gives the get-callees step).

Ledger defects:

- repro_cmd covers only the get-callees step; the get-symbol and get-call-chain steps that support the 'actual' text are not given as commands (symbol IDs recoverable from analysis/codesight/*.json).

### crypto-mcp-005 (mcp): REPRODUCED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-mcp-005.log`.

Commands run:

- `<env> codesight-mcp get-file-outline --repo local/botan-9e173108f3f6 --file-path src/lib/stream/chacha/chacha_avx2/chacha_avx2.cpp --repo-path "$PWD/upstream/botan" --format json (and chacha_avx512, chacha_simd32, poly1305_avx2, poly1305_avx512)`
- `<env> codesight-mcp search-text --repo local/botan-9e173108f3f6 --query template --file-pattern 'src/lib/mac/poly1305/**' --format json`
- `<env> codesight-mcp search-text --repo local/botan-9e173108f3f6 --query BOTAN_HAS_CHACHA --file-pattern src/lib/stream/chacha/chacha.cpp --format json`

Decisive output: chacha_avx2/avx512/simd32 outlines: only [('(module)', 'symbol', 1)], while chacha_avx2.cpp:15 defines ChaCha::chacha_avx2_x8. poly1305_avx2 -> only raw() (line 58); poly1305_avx512 -> only raw() (line 103). search-text template: 2 hits, poly1305_avx512.cpp:42 `template <int COUNT>` and :68 `template <size_t S>`. search-text BOTAN_HAS_CHACHA in chacha.cpp: 8 hits (lines 97,103,113,119,125,137,147,157).

Notes: All four sub-claims match.

Ledger defects:

- repro_cmd gives only the chacha_avx2 outline; the other outlines and the two search-text queries (file patterns) are prose in 'actual'.

### crypto-mcp-006 (mcp): REPRODUCED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-mcp-006.log`.

Commands run:

- `mcp__tilth__tilth_search(query="m_poly1305->update", kind="content", scope="<copy>/upstream/botan/src/lib/modes/aead/chacha20poly1305")`
- `mcp__tilth__tilth_read(path="<copy>/upstream/botan/src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp", section="110-157")`
- `grep -n 'update_len\|::process_msg\|m_poly1305->update' chacha20poly1305.cpp`

Decisive output: tilth_search: `chacha20poly1305.cpp:72,94,99,113,133,156,188 [7 usages in function Botan.ChaCha20Poly1305_Mode::update_len(uint64_t len)]`. tilth_read: line 113 is inside ChaCha20Poly1305_Encryption::process_msg (110-123), line 156 inside ChaCha20Poly1305_Decryption::process_msg (154-). grep: update_len is defined at 69-73, so only line 72 is really in update_len.

Notes: Tilth MCP tools were available to the replaying agent, so this is a real Tilth replay (not a grep re-probe). Scope was an absolute path into the disposable copy rather than the workspace-relative path in the repro. Tilth version still not exposed.

Ledger defects:

- pyz_sha256 for a Tilth (non-Ligature) finding records the 1.3.6 Ligature bundle hash; irrelevant to the tool under test (same pattern on all mcp/kani entries).

### crypto-kani-001 (kani): REPRODUCED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-kani-001.log`.

Commands run:

- `nix develop ...#crypto-mixed -c bash -c 'cargo kani --version; which cargo-kani'`
- `git show {2cbbccd,6a55894}:project-descriptor.json | python3 (verifier_policy, closure_kind)`
- `git show {2cbbccd,6a55894}:crates/crypto-mixed-core/specs/{cha_cha20,poly1305,cha_cha20_poly1305}.json | python3 (concept, verifier, cluster); specs/_promotions/crypto-kani.json`

Decisive output: cargo-kani 0.67.0 (/home/goya/.cargo/bin/cargo-kani), exit 0. Descriptor at 2cbbccd and at 6a55894: verifier_policy {"default": "kani"}, closure_kind bounded. ChaCha20, Poly1305, ChaCha20Poly1305: verifier=kani, cluster=crypto-kani; all three listed in the crypto-kani promotion receipt.

Notes: A scope-decision record, not a tool defect; both claims (version discovery and Kani-only bounded configuration) hold at the recording commit and at the baseline.

Ledger defects:

- repro_cmd (cargo kani --version) only checks the version; the descriptor/concept facts in 'actual' need file inspection that the repro does not name.

### crypto-kani-002 (kani): REPRODUCED

Recorded exit 124; observed exit 124. Full log: `logs/crypto-kani-002.log`.

Commands run:

- `nix develop ...#crypto-mixed -c bash -c 'export CARGO_TARGET_DIR=$R/kani-target/crypto-kani-002; timeout 180 cargo kani --manifest-path crates/crypto-mixed-core/Cargo.toml --harness kani_chacha20_apply_keystream_output_length'   (fresh copy at baseline 6a55894)`
- `ps -eo pid,etimes,cmd | grep -E 'cbmc|kani-compiler|cargo-kani'   (no lingering processes of this run)`

Decisive output: Baseline: Checking harness at 16:20:42 (codegen 0.7 s), still in CBMC symbolic execution (unwinding chacha20_block loops; 'Not unwinding loop ... apply_keystream.0 iteration 66') when timeout fired; exit 124 after 189.5 s wall (180 s bound + nix shell start-up). No VERIFICATION line.

Notes: Harness: #[kani::unwind(66)], kani::vec::any_vec::<u8, 65>() (symbolic lengths 0..65), as described. chacha20.rs is unchanged since the recording commit e0bd451, so the baseline replay stands for the historical state. The passing fixed 65-byte harness mentioned in 'actual' was not separately replayed here (it shows up as rerun by status/gate-g14, see crypto-ligature-005). The host was shared (load average 10-13; another agent's ligature/Kani run on the live pilot was seen in ps), which can only make a timeout more likely; CBMC still had about 175 s of the 180 s bound.

Ledger defects:

- repro_cmd records the bound only as prose ('ctx_execute stopped the run at 180 seconds'); it should be `timeout 180 cargo kani ...` so the exit 124 is reproducible as a command.

### crypto-kani-003 (kani): REPRODUCED

Recorded exit 124; observed exit 124. Full log: `logs/crypto-kani-003.log`.

Commands run:

- `nix develop ...#crypto-mixed -c bash -c 'export CARGO_TARGET_DIR=$R/kani-target/crypto-kani-003; timeout 180 cargo kani --manifest-path crates/crypto-mixed-core/Cargo.toml --harness kani_chacha20_apply_keystream_capacity'   (fresh copy at baseline 6a55894)`
- `ps -eo pid,etimes,cmd | grep -E 'cbmc|kani-compiler|cargo-kani'   (no lingering processes of this run)`

Decisive output: Baseline: Checking harness at 16:23:53, still in symbolic execution (chacha20_block unwinding) at timeout; exit 124 after 189.8 s. No VERIFICATION line.

Notes: Harness: unwind(66), any_vec::<u8,65>, symbolic u32 counter, as described. chacha20.rs unchanged since e0bd451. The host was shared (load average 10-13; another agent's ligature/Kani run on the live pilot was seen in ps), which can only make a timeout more likely; CBMC still had about 175 s of the 180 s bound.

Ledger defects:

- repro_cmd records the bound only as prose ('ctx_execute stopped the run at 180 seconds'); it should be `timeout 180 cargo kani ...` so the exit 124 is reproducible as a command.

### crypto-kani-004 (kani): REPRODUCED

Recorded exit 124; observed exit 124. Full log: `logs/crypto-kani-004.log`.

Commands run:

- `nix develop ...#crypto-mixed -c bash -c 'export CARGO_TARGET_DIR=$R/kani-target/crypto-kani-004; timeout 180 cargo kani --manifest-path crates/crypto-mixed-core/Cargo.toml --harness poly1305_chunked_update_matches_one_shot_for_bounded_messages'   (fresh copy at baseline 6a55894)`
- `nix develop ...#crypto-mixed -c bash -c 'export CARGO_TARGET_DIR=$R/kani-target/crypto-kani-004-hist; timeout 180 cargo kani --manifest-path crates/crypto-mixed-core/Cargo.toml --harness poly1305_chunked_update_matches_one_shot_for_bounded_messages'   (fresh copy, git checkout e0bd451)`
- `ps -eo pid,etimes,cmd | grep -E 'cbmc|kani-compiler|cargo-kani'   (no lingering processes of this run)`

Decisive output: Baseline: Runtime Symex 3.16 s, 12358 VCCs (5421 after simplification), 'Solving with CaDiCaL 2.0.0' at 16:28:14 and 16:28:30, no result before the bound; exit 124 (187.8 s). Historical e0bd451: 12118 VCCs (5421 after simplification), no result; exit 124 (188.9 s).

Notes: Harness: unwind(16), message [u8; 8], symbolic split_at with kani::assume(split_at <= len), as described. poly1305.rs changed after e0bd451 (Poly1305State fold), so both states were replayed; both time out. The host was shared (load average 10-13; another agent's ligature/Kani run on the live pilot was seen in ps), which can only make a timeout more likely; CBMC still had about 175 s of the 180 s bound.

Ledger defects:

- repro_cmd records the bound only as prose ('ctx_execute stopped the run at 180 seconds'); it should be `timeout 180 cargo kani ...` so the exit 124 is reproducible as a command.

### crypto-kani-005 (kani): REPRODUCED

Recorded exit 124; observed exit 124. Full log: `logs/crypto-kani-005.log`.

Commands run:

- `nix develop ...#crypto-mixed -c bash -c 'export CARGO_TARGET_DIR=$R/kani-target/crypto-kani-005; timeout 180 cargo kani --manifest-path crates/crypto-mixed-core/Cargo.toml --harness aead_round_trip_holds_for_one_symbolic_byte'   (fresh copy at baseline 6a55894)`
- `nix develop ...#crypto-mixed -c bash -c 'export CARGO_TARGET_DIR=$R/kani-target/crypto-kani-005-hist; timeout 180 cargo kani --manifest-path crates/crypto-mixed-core/Cargo.toml --harness aead_round_trip_holds_for_one_symbolic_byte'   (fresh copy, git checkout e0bd451)`
- `ps -eo pid,etimes,cmd | grep -E 'cbmc|kani-compiler|cargo-kani'   (no lingering processes of this run)`

Decisive output: Baseline: Runtime Symex 14.7 s, 128991 VCCs (19477 after simplification), 'Solving with CaDiCaL 2.0.0' from 16:30:43, no result; exit 124 (189.7 s). Historical e0bd451: Symex 19.2 s, 128703 VCCs (19477 after simplification), no result; exit 124 (189.0 s).

Notes: Harness: unwind(64), symbolic key/nonce, 1-byte AAD and 1-byte plaintext, as described. aead.rs/poly1305.rs changed after e0bd451, so both states were replayed; both time out. The host was shared (load average 10-13; another agent's ligature/Kani run on the live pilot was seen in ps), which can only make a timeout more likely; CBMC still had about 175 s of the 180 s bound.

Ledger defects:

- repro_cmd records the bound only as prose ('ctx_execute stopped the run at 180 seconds'); it should be `timeout 180 cargo kani ...` so the exit 124 is reproducible as a command.

### crypto-ligature-001 (ligature): REPRODUCED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-ligature-001.log`.

Commands run:

- git checkout 2cbbccd (bundle sha256 97410d60...; `version` -> ligature 1.3.6, source 37448878... clean)
- `python3 tools/ligature/ligature.pyz record-assurance --help`
- `python3 tools/ligature/ligature.pyz record-assurance --help | grep -i -c kani`
- `baseline 6a55894 (1.4.2): python3 -I tools/ligature/ligature.pyz record-assurance --help | grep -i -A3 kani`

Decisive output: 1.3.6 help: usage `record-assurance [-h] [--proof OBLIGATION=PATH] [--verus-json PATH] [--verus-function OBLIGATION=FUNCTION] work_package`; grep -c kani = 0. Baseline 1.4.2 help lists --kani-crate PATH and --kani-harness OBLIGATION=HARNESS ('Only cargo-kani 0.67.0 is supported').

Notes: Reproduces exactly with the 1.3.6 bundle restored from 2cbbccd. No longer true at the baseline: Kani intake exists since 1.3.9/1.3.10 (see crypto-ligature-002/004). The entry does not itself record the resolution.

Ledger defects:

- repro_cmd does not name the 1.3.6 bundle or commit; run verbatim at the baseline it shows a Kani intake and silently contradicts the finding. Entry should be marked resolved (Kani intake added by 1.3.9/1.3.10).

### crypto-ligature-002 (ligature): REPRODUCED

Recorded exit 1; observed exit 1. Full log: `logs/crypto-ligature-002.log`.

Commands run:

- `git checkout c74cf6a (Ligature 1.3.9, bundle a378f38d...)`
- `nix develop ... -c cargo generate-lockfile --offline --manifest-path crates/crypto-mixed-core/Cargo.toml`
- `nix develop ... -c 'export CARGO_TARGET_DIR=<stage8c-replay>/kani-target/...; python3 -I tools/ligature/ligature.pyz record-assurance WP-CRYPTO-MIXED-PRIMITIVES-001 --kani-crate crates/crypto-mixed-core --kani-harness Poly1305.C002=kani_poly1305_finalize_tag_length'`
- `git status --short`
- `python3 -I tools/ligature/ligature.pyz gate-g14   (1.3.9 has no --json; a first attempt with --json gave a usage error, exit 2)`
- `nix develop ... -c 'cargo kani --manifest-path crates/crypto-mixed-core/Cargo.toml --harness kani_poly1305_finalize_tag_length'`
- `baseline: inspect ci/results/WP-CRYPTO-MIXED-PRIMITIVES-001.json`

Decisive output: record-assurance exit 1 after 105 s: `error: Kani did not prove every check in harness 'kani_proofs::kani_poly1305_finalize_tag_length': ['SUCCESS', 'SUCCESS', ...`; no report written (git status: only the generated Cargo.lock). gate-g14 exit 1: `[G14/error] Poly1305.C002: WP-CRYPTO-MIXED-PRIMITIVES-001 provides this obligation but recorded no achieved assurance for it ...`, `FAIL: 1 cluster(s) blocked`. Direct Kani: exit 0, 724 SUCCESS, 9 UNREACHABLE, 0 FAILURE, `** 0 of 733 failed (9 unreachable)`, `VERIFICATION:- SUCCESSFUL`, `Complete - 1 successfully verified harnesses, 0 failures, 1 total.`

Notes: Reproduces at the 1.3.9 state. The 9 UNREACHABLE checks are 3 in Poly1305State::update/process_block (the streaming continuation), 1 in poly1305::load_u32_le (crate code) and 5 in core library code. The recorded split '3 ... and 6 in Rust library code' counts load_u32_le as library code; the total of 9 matches. Not present at the baseline: the 1.4.2 report holds a Kani record for Poly1305.C002 / kani_poly1305_finalize_tag_length with an unreachable_checks list, so UNREACHABLE checks are now accepted. The entry does not record that resolution.

Ledger defects:

- repro_cmd names neither the commit (c74cf6a) nor the bundle; run verbatim at the baseline it would not fail. Entry should be marked resolved.

### crypto-ligature-003 (ligature): REPRODUCED

Recorded exit 1; observed exit 1. Full log: `logs/crypto-ligature-003.log`.

Commands run:

- `git checkout 3296758 (Ligature 1.3.10, bundle d1b20d0b...; descriptor verifier_backends: None)`
- `nix develop ... -c cargo generate-lockfile --offline --manifest-path crates/crypto-mixed-core/Cargo.toml`
- `nix develop ... -c python3 -I tools/ligature/ligature.pyz check-bridges`
- `nix develop ... -c python3 -I tools/ligature/ligature.pyz record-assurance WP-CRYPTO-MIXED-AEAD-001 --kani-crate crates/crypto-mixed-core --kani-harness BR-CRYPTO-MIXED-001=bridge_001_passes_a_fixed_thirty_two_byte_poly1305_key`
- `nix develop ... -c cargo kani --manifest-path crates/crypto-mixed-core/Cargo.toml --harness bridge_001_passes_a_fixed_thirty_two_byte_poly1305_key`
- `baseline 6a55894: gate-g9; check-bridges`

Decisive output: check-bridges exit 1: wrote ci/harness/BR-CRYPTO-MIXED-001.kani.rs and -002.kani.rs, then `FAIL: 2 finding(s)` `[G9/error] BR-CRYPTO-MIXED-00{1,2}: harness generated for kani ..., but the project descriptor configures no verifier_backends.kani command -- nothing was checked, so no result is recorded`; no ci/results/bridge_checks. record-assurance with a BR id: exit 2, `--kani-harness obligation 'BR-CRYPTO-MIXED-001' does not match the <Concept>.C<n> obligation id grammar`. Direct Kani: `** 0 of 418 failed (4 unreachable)`, VERIFICATION:- SUCCESSFUL. Baseline: descriptor has verifier_backends.kani = python3 crates/crypto-mixed-core/tests/kani_bridge_backend.py; gate-g9 `OK: all bridges pass G9 (compiled, dispatched, and checked) (3 discovered)`; check-bridges exit 0, dispatching bridge_br_crypto_mixed_00{1,2,3}.

Notes: Reproduces exactly at the 1.3.10 state. At the baseline the condition the workaround waits for is met: a Kani backend adapter is configured and G9 passes for 3 bridges. The entry does not record that resolution.

Ledger defects:

- 'passed 0 of 418 checks with 4 unreachable' is misworded: Kani reports 0 of 418 FAILED (414 SUCCESS, 4 UNREACHABLE).
- repro_cmd names the 1.3.10 bundle but not the commit; entry should be marked resolved (verifier_backends.kani added in 4d66e69).

### crypto-ligature-004 (ligature): REPRODUCED

Recorded exit 2; observed exit 2. Full log: `logs/crypto-ligature-004.log`.

Commands run:

- `git checkout d391ad4 (Ligature 1.3.10, bundle d1b20d0b...; no crates/crypto-mixed-core/Cargo.lock)`
- `nix develop ... -c 'export CARGO_TARGET_DIR=<stage8c-replay>/kani-target/...; python3 -I tools/ligature/ligature.pyz record-assurance WP-CRYPTO-MIXED-PRIMITIVES-001 --kani-crate crates/crypto-mixed-core --kani-harness Poly1305.C002=kani_poly1305_finalize_tag_length'`
- `cargo generate-lockfile --offline --manifest-path crates/crypto-mixed-core/Cargo.toml; python3 -I tools/ligature/ligature.pyz write-set-check --json`
- `cargo build --offline (in-tree target/); write-set-check --json`
- `baseline 6a55894: write-set-check --json`

Decisive output: record-assurance exit 2: `error: Cargo metadata with --locked failed before Kani could run; resolve the manifest and lockfile first (error: cannot create the lock file .../crates/crypto-mixed-core/Cargo.lock because --locked was passed to prevent this ...)`; no Cargo.lock created. With the offline lock: write-set-check exit 1, `out-of-set crates/crypto-mixed-core/Cargo.lock`. With an in-tree target dir: 50 violations (Cargo.lock + crates/crypto-mixed-core/target/**). Baseline: Cargo.lock is committed (since 4d66e69) and listed in protected_roots; write-set-check exit 0, state clean.

Notes: All three recorded behaviours reproduce at the 1.3.10 state. No longer present at the baseline: a committed, protected lockfile now exists, which is the sanctioned path the workaround asked for. The entry does not record that resolution.

Ledger defects:

- The entry should be marked resolved (Cargo.lock committed in 4d66e69 and added to protected_roots). The repro_cmd names the 1.3.10 bundle but not the commit (d391ad4/3296758) needed to get a tree without Cargo.lock.

### crypto-ligature-005 (ligature): REPRODUCED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-ligature-005.log`.

Commands run:

- `state (pass 2): git checkout 13e6021; git checkout 2f2152d -- tools/ligature ci/manifest/installation.json ci/results/c_static/crates_crypto-mixed-core.json (uncommitted 1.4.1 install plus the then-uncommitted fresh C_static)`
- `nix develop ... -c 'timeout 20 python3 -I tools/ligature/ligature.pyz status --json'   (pass 1 state)`
- `nix develop ... -c 'bash bin/status_probe.sh': timeout --kill-after=5s 1200 python3 -I tools/ligature/ligature.pyz status --json, process tree sampled every 15 s (bin/ptree.py)`
- `find . -newer <marker> -type f ! -path './.git/*'; git status --short`
- `baseline 6a55894 (1.4.2): same probe`

Decisive output: 20 s bound: exit 124, 0 bytes stdout and stderr, no leftover processes. 1200 s bound (pass 2): `exit=0 elapsed=404s stdout_bytes=23264 stderr_bytes=0`, valid JSON, cluster crypto-kani state blocked, 36 open_findings. The process tree shows cargo-kani -> cbmc for `kani_proofs::kani_chacha20_c002_exact_length_65_boundary` (--unwind 66) and `kani_proofs::kani_poly1305_finalize_tag_length` (--unwind 32); peak cbmc RSS 6,363 MB (pass 1: 6,725 MB). No workspace file changed. Baseline 1.4.2: status --json exits 0 in 4 s, 22,552 bytes, no Kani process.

Notes: The defect reproduces: status silently reruns the recorded Kani harnesses, takes minutes, uses about 6.5 GB, and a 20 s bound gives exit 124 with no output. Runtime was 404-419 s against the recorded 286 s, consistent with the loaded shared host. Pass 1 used only the committed state (stale 2cbbccd C_static): 14,465 bytes, cluster 'degraded'. The recorded 23,420-byte output (evidence status.stdout.json) carries r1-g16 findings for the fresh 16/12/4 report, so pass 2 added that file and got 23,264 bytes and cluster 'blocked', matching. No longer present at the baseline: 1.4.2 status does not rerun Kani (the entry does not record that).

Ledger defects:

- 'HEAD 13e6021 + 1.4.1 install' leaves out the uncommitted fresh C_static that the recorded run had (committed later in 2f2152d); without it the output differs (14,465 bytes, cluster degraded instead of blocked).
- Entry should note that 1.4.2 status no longer reruns Kani (4 s at the baseline).

### crypto-kani-006 (kani): REPRODUCED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-kani-006.log`.

Commands run:

- `baseline 6a55894: cat specs/_closure/crypto-kani.degradation.json; grep for generics in crates/crypto-mixed-core/src`
- `nix develop ... -c python3 -I tools/ligature/ligature.pyz gate-g14 --json`
- `recording-time state: git checkout 2f2152d + untracked BR-001/002 harness + stale 2cbbccd C_static; gate-g14 --json`

Decisive output: Baseline (1.4.2, reruns 6 Kani obligations): exit 0, single finding `[G14/degraded] generic_callees_type_universal_or_creusot_owned ... accepted as degradation under ceiling 'per-instantiation' (chainlink:135)`; degradation record: failed_conditions [generic_callees_type_universal_or_creusot_owned], affected_edges BR-001/002/003, ceiling per-instantiation, capability_gap CG3, tracking_issue chainlink:135. Recording state (1.4.1): exit 0, same single degraded finding. Only generic in src: `const fn decode_hex<const N: usize>` in kani_proofs.rs.

Notes: The CG3 degradation is reported and accepted under the reviewed record at both states. At the baseline this is a genuine exit 0 (C_static 18/18/0). At the recording-time state, exit 0 only happens with the stale empty C_static; with the fresh 16/12/4 report of that day G14 exits 1 (see crypto-ligature-006).

Ledger defects:

- 'actual' combines exit 0 with 'extract-c-static ... 4 unresolved possible-dispatch sites', but those come from two different C_static states: with the 4-unresolved report, 1.4.1 G14 exits 1. The recorded exit 0 is the vacuous stale-report result that crypto-ligature-006 later identified.

### crypto-ligature-006 (ligature): REPRODUCED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-ligature-006.log`.

Commands run:

- `state: git checkout 2f2152d (1.4.1, regenerated manifests); untracked ci/harness/BR-CRYPTO-MIXED-00{1,2}.kani.rs restored from f4ca347; git show 2cbbccd:ci/results/c_static/crates_crypto-mixed-core.json > ci/results/c_static/crates_crypto-mixed-core.json (sha256 20845eb0...d857)`
- `nix develop ... -c python3 -I tools/ligature/ligature.pyz gate-r1-g16 --json`
- `... gate-g14 --json`
- `... extract-c-static --target x86_64-unknown-linux-gnu`
- `... gate-g14 --json`
- `... check --issue 134 --json`
- `extra: baseline 6a55894 (1.4.2) with the same stale report swapped in: gate-r1-g16 --json; gate-g14 --json`

Decisive output: Stale report (discovered 0, local_concepts [], 0 callsites): gate-r1-g16 exit 0, gate_acceptance accepted, checked 0, I-CRYPTO-MIXED-001/002/003 only as info 'intent without realization'; gate-g14 exit 0, only [G14/degraded] CG3 (ceiling per-instantiation). Fresh extraction: `16 discovered, 12 resolved, 4 unresolved`; gate-g14 exit 1: two `WP-CRYPTO-MIXED-AEAD-001 requires all discovered call sites resolved, but the C_static observation reports 4 unresolved`, `[G17/error] conditions.unresolved_indirect_calls_at_or_above_medium is declared as 0 but the computed closure says 4`. check --issue 134 exit 1 with three R1 'absent from I' errors: encrypt->ChaCha20.with_counter, decrypt->ChaCha20.with_counter, Poly1305.set_key->Poly1305State.new. 1.4.2 with the stale report: gate-r1-g16 exit 1 `[G1b/error] legacy C_static report has no source binding, so freshness cannot be established`; gate-g14 exit 1 `C_static report is not safe to consume`.

Notes: Every recorded sub-result reproduces on 1.4.1 (each gate-g14 run took 207-224 s). The defect is fixed in 1.4.2, which refuses the unbound report, but the entry does not record that.

Ledger defects:

- Entry should be marked resolved in 1.4.2 (source-bound C_static; the legacy report is refused by G1b/G14).

### crypto-ligature-007 (ligature): REPRODUCED

Recorded exit 1; observed exit 1. Full log: `logs/crypto-ligature-007.log`.

Commands run:

- `state: git checkout 2f2152d (1.4.1) + untracked ci/harness/BR-CRYPTO-MIXED-00{1,2}.kani.rs (f4ca347 bytes)`
- `python3 -I tools/ligature/ligature.pyz write-set-check --json`
- `rm ci/harness/*.kani.rs; write-set-check --json`
- `gate-g9`
- `check-bridges (Kani backend dispatch); cmp regenerated harness with f4ca347`
- `write-set-check --json; gate-g9`
- `git add ci/harness && git commit (scratch git); write-set-check --json`
- `same write-set-check with the 1.4.0 (13e6021) and 1.3.11 (201745b) bundles`
- `baseline 6a55894 (1.4.2, harness tracked): write-set-check --json; gate-g9`

Decisive output: 1.4.1 as copied: exit 1, exactly 2 violations (`2 write-set violation(s): ci/harness/BR-CRYPTO-MIXED-001.kani.rs, ci/harness/BR-CRYPTO-MIXED-002.kani.rs`, out-of-set). Harness removed: exit 0, clean; gate-g9 exit 1 `[G9/error] BR-CRYPTO-MIXED-00{1,2}: no generated harness at ci/harness/BR-CRYPTO-MIXED-00N.kani.rs -- run pipeline.py check-bridges`. check-bridges exit 0, output byte-identical to f4ca347; then write-set-check exit 1 (same 2), gate-g9 exit 0 `all bridges pass G9 ... (2 discovered)`. Committed harness: exit 1 (same 2). 1.4.0 and 1.3.11: exit 1 (same 2). Baseline 1.4.2: write-set-check exit 0 clean and gate-g9 exit 0 (3 discovered).

Notes: Reproduces on 1.3.11, 1.4.0 and 1.4.1, tracked or untracked, including the 'pipeline.py' wording. 1.3.12 is not in the copy's history, so that bundle was not replayed. Not present at the baseline (1.4.2 with tracked harness files: clean write set and G9 passing together); the entry does not record that.

Ledger defects:

- Entry should be marked resolved at 1.4.2/f4ca347. The repro_cmd lists 'released 1.3.12', a bundle that is not in the pilot's history and cannot be replayed from it.

### crypto-ligature-008 (ligature): REPRODUCED-RESOLVED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-ligature-008.log`.

Commands run:

- `git checkout 13e6021; git show 2f2152d:tools/ligature/ligature.pyz > tools/ligature/ligature.pyz  (1.4.1, sha 973b883b...)`
- `nix develop ... -c python3 -I tools/ligature/ligature.pyz extract-c-static --target x86_64-unknown-linux-gnu`
- `python3: read ci/results/c_static/crates_crypto-mixed-core.json (callsite_coverage, coverage_scope, possible-dispatch callsites)`
- `baseline 6a55894: same extract-c-static`

Decisive output: 13e6021+1.4.1: `16 discovered, 12 resolved, 4 unresolved (discovered-lower-bound)`. possible-dispatch: CS-CHACHA20POLY1305-ENCRYPT-003 aead.rs:49 chacha.bytes_remaining(...), -ENCRYPT-004 aead.rs:52 chacha.apply_keystream(...), -DECRYPT-003 aead.rs:76 chacha.apply_keystream(...), CS-POLY1305-UPDATE-001 poly1305.rs:32 ?.update(...); all risk_tier medium, risk_tier_source extractor-default. coverage_scope: extractor coarse-syntactic-callgraph 0.2.0, supported_call_forms [associated-path-call, self-method-call, inherent-method-call-by-name]. Baseline (1.4.2): `18 discovered, 18 resolved, 0 unresolved`.

Notes: Resolution recorded in crypto-ligature-011 (#47 respelling); confirmed at baseline (no unresolved sites). Baseline count is 18 discovered, not the 16 recorded in -011 (later commits changed the crate).

### crypto-ligature-009 (ligature): REPRODUCED

Recorded exit 1; observed exit 1. Full log: `logs/crypto-ligature-009.log`.

Commands run:

- `control: nix develop ... -c python3 -I tools/ligature/ligature.pyz validate-interaction`
- `python3: set crates/crypto-mixed-core/specs/_interactions/I-CRYPTO-MIXED-001.json reliances[0].required_assurance.accepted_evidence_kinds = ['kani-bounded-model-check','dudect-constant-time-test'] (copy only)`
- `nix develop ... -c python3 -I tools/ligature/ligature.pyz validate-interaction`
- `python3 -I tools/ligature/ligature.pyz schema show {interaction,work-package-manifest}; record-assurance --help`

Decisive output: Control: `OK: all interactions pass ... (8 discovered)`, exit 0. Modified: `FAIL: 1 finding(s)  - [G1a/error] .../I-CRYPTO-MIXED-001.json: 'dudect-constant-time-test' is not one of ['kani-bounded-model-check', 'creusot-deductive-check', 'verus-deductive-check']`, exit 1. Bundled schemas: interaction $defs/required_assurance/accepted_evidence_kinds items enum and work-package-manifest $defs/evidence_kind enum are both exactly those three kinds. record-assurance intake flags: --proof, --verus-json/--verus-function, --kani-crate/--kani-harness only.

Notes: Baseline 1.4.2 (bundle c4d989f3, recorded sha). Feature gap confirmed as described.

### crypto-ligature-010 (ligature): REPRODUCED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-ligature-010.log`.

Commands run:

- `reconstructed state: git checkout 74ff591 + python3 bin/respell.py (the four #47 associated-path respellings, Poly1305State not folded)`
- `nix develop ... -c python3 -I tools/ligature/ligature.pyz extract-c-static --target x86_64-unknown-linux-gnu; python3 bin/csum.py ci/results/c_static/crates_crypto-mixed-core.json`
- edit (copy only): add `type TagBytes = [u8; 16];` to aead.rs and poly1305.rs and change `fn tag(..) -> [u8; 16]` / `pub fn compute_tag(..) -> [u8; 16]` to `-> TagBytes`; cargo check (compiles); rerun extract-c-static
- same before/after pair at commit 6667510 and at baseline 6a55894; control: make `tag` pub without changing its return type

Decisive output: Reconstructed state: before `16 discovered, 16 resolved, 0 unresolved`, unattributed_call_sites 217; after the return-type respelling `21 discovered, 20 resolved, 1 unresolved`, unattributed 204, new CS-CHACHA20POLY1305-ENCRYPT-005/DECRYPT-002/VERIFY-002 -> ChaCha20Poly1305.tag and CS-POLY1305-COMPUTE-TAG-001/002. At 6667510: 18 -> 23 discovered, unattributed 242 -> 229; at baseline: 18 -> 23, 240 -> 227, the same five new IDs. Control (pub tag, array return kept): 18 discovered, unchanged.

Notes: Extractor defect still present at the baseline. The recorded absolute counts (16, 217 -> 204) belong to an uncommitted intermediate state; they reproduce exactly once that state is rebuilt from 74ff591 plus the respellings that crypto-ligature-011 describes. Every committed post-respelling state gives 18 discovered, because Poly1305State was folded in the same commit 6667510. Minor: the recorded text does not mention that one of the five newly visible sites (COMPUTE-TAG-002, `state.update` on a local) is itself possible-dispatch, so the after-state is 21/20/1, not 21/21/0.

Ledger defects:

- The recorded counts come from a state that is not a commit (respelling and the Poly1305State fold both landed in 6667510). The repro gives no commit, and at any commit 'reports 16 discovered' fails (it reports 18).
- repro_cmd does not say that a `type TagBytes = [u8; 16];` alias must be added for the crate to compile.

### crypto-ligature-011 (ligature): REPRODUCED-RESOLVED

Recorded exit 1; observed exit 1. Full log: `logs/crypto-ligature-011.log`.

Commands run:

- `reconstructed state: git checkout 74ff591 + python3 bin/respell.py (aead.rs:49/52/76 -> ChaCha20::bytes_remaining(&chacha)/ChaCha20::apply_keystream(&mut chacha, ..); poly1305.rs update -> Poly1305State::update(state, input)); cargo check exit 0`
- `nix develop ... -c 'python3 -I tools/ligature/ligature.pyz extract-c-static --target x86_64-unknown-linux-gnu && python3 -I tools/ligature/ligature.pyz gate-r1-g16 --json'; validate-callsites`
- `same at commit 6667510 and at baseline 6a55894`

Decisive output: Reconstructed: `16 discovered, 16 resolved, 0 unresolved`; validate-callsites exit 0; gate-r1-g16 exit 1, counts undeclared_blocking 6: encrypt->ChaCha20.with_counter, encrypt->ChaCha20.bytes_remaining, decrypt->ChaCha20.with_counter, decrypt->ChaCha20.apply_keystream, Poly1305.set_key->Poly1305State.new, Poly1305.update->Poly1305State.update; encrypt->apply_keystream matches I-CRYPTO-MIXED-002 (info only). At 6667510: 18/18/0, gate-r1-g16 exit 1 with 4 undeclared (the two Poly1305State edges vanish with the fold). Baseline: 18/18/0, gate-r1-g16 exit 0, undeclared_blocking 0, interaction_reconciliation complete.

Notes: The recorded result reproduces exactly on the rebuilt pre-fold state. Resolution (edges declared via promoted I-CRYPTO-MIXED-004..008 at 6e6bee1) confirmed at the baseline.

Ledger defects:

- repro_cmd names no state; run verbatim at the baseline it exits 0. The recorded state was never committed (6667510 also folds Poly1305State), so only a hand reconstruction reproduces the 16 discovered / 6 undeclared result.

### crypto-ligature-012 (ligature): NOT-RUNNABLE(HUMAN)

Recorded exit 2; observed exit n/a. Full log: `logs/crypto-ligature-012.log`.

Commands run:

- `baseline: python3 (compare I-CRYPTO-MIXED-002 and -007 reliances on ChaCha20.C003; which harness BR-002/003 cite in the AEAD manifest and assurance report)`
- `python3 -I tools/ligature/ligature.pyz generate-work-package --help; tail ci/results/protected-writes.jsonl`
- `nix develop ... -c 'cargo kani --manifest-path crates/crypto-mixed-core/Cargo.toml --harness kani_chacha20_c003_aead_counter_one_stream_capacity'`

Decisive output: Not run: the recorded path needs `approve`, `record-ruling` and `accept-promotion` of a modified I-CRYPTO-MIXED-007 (human-checkpoint verbs), then generate-work-package, which 'requires an exact issue-scoped protected-write grant' (--grant-id, a human-issued one-shot grant) and a `--plan <stage7-plans-v2>/...json` file that is not in the repository. Verified workaround state: I-002 and I-007 each have one ChaCha20.C003 reliance with identical required_assurance (minimum_scope 'the bounded model encoded by Kani harness kani_chacha20_c003_aead_counter_one_stream_capacity'); that harness appears in the BR-002 and BR-003 records of the AEAD manifest and report; Kani: `** 0 of 34 failed (1 unreachable)`, VERIFICATION:- SUCCESSFUL.

Notes: The contradictory-source refusal itself was not exercised. Steps needing a human: (1) approve the I-007 draft with its own harness scope, (2) record-ruling, (3) accept-promotion, (4) issue a one-shot write grant for generate-work-package. A plan file from outside the repo is also needed. The workaround half (shared scope, 0/34 failed) is confirmed.

Ledger defects:

- repro_cmd and 'command' reference a placeholder plan path (<stage7-plans-v2>/stage-7-plan-...-issue-134.json) and grant (<grant>) that are not recorded anywhere in the pilot, so the refusal cannot be replayed even by a human without recreating the plan.

### crypto-rdb-001 (rdb): PARTIAL

Recorded exit 100; observed exit 100. Full log: `logs/crypto-rdb-001.log`.

Commands run:

- `cd oracle/rust-check && RUSTFLAGS='-C link-arg=-no-pie' CARGO_TARGET_DIR=target/repro cargo build --bin oracle_repro && rdb target/repro/debug/oracle_repro < ../divergences/boundary-aead-output-length-encrypt-0003/rdb-commands.txt   (verbatim)`
- `nm target/repro/debug/oracle_repro | grep encryption_output_length; same rdb script with the break address replaced by the nm address`
- `pre-ruling reconstruction (copy only): set the three excluded past-RFC-limit cases back to oracle_scope=compare; oracle_driver oracle/cases.jsonl oracle/golden/results.jsonl; python3 oracle/generate_oracle_tests.py; cargo nextest run --profile ci --no-fail-fast -E 'not binary(random_cases)'`
- `post-ruling control: same nextest on the unmodified cases`
- `path test: same build in /tmp/s8c-rdb-<pad>/crypto-mixed (root path length 60, same as the live pilot)`

Decisive output: oracle_repro: `result=Err(MessageTooLong)` for input 274877906881. Verbatim rdb script: nm puts encryption_output_length at 0x211240, not 0x2111f0; rdb stopped in std (`rdi = 0x4 rsi = 0x1 rdx = 0x0`, library/std/src/sys/alloc/unix.rs:13), so the divergence is not shown. With the adapted address 0x211240: `rdx = 0x3fffffffc1`, then aead.rs:21 -> aead.rs:22 -> aead.rs:27. Pre-ruling: `1370 tests run: 1367 passed, 3 failed`, exit 100; failures are the three past-limit cases, left `err message_too_long`, right `ok 274877906881 / 274877906897 / 4611686018427387920`. Post-ruling: `1370 tests run: 1370 passed`. Same-length-path build: address 0x2111e0; break 0x2111f0 never hit; rdb printed ESRCH errors and still exited 0.

Notes: The divergence, the nextest counts and the rdb diagnosis (first differing value rdx = 0x3fffffffc1 > MAX_MESSAGE_BYTES at aead.rs:21) all reproduce, and the ruling's resolved state (1370/1370) is confirmed. The repro_cmd as written does not reproduce in a clean copy, because rdb-commands.txt hard-codes a break address that depends on the build path. Three clean builds gave 0x211240, 0x211250 and 0x2111e0.

Ledger defects:

- repro_cmd's rdb script (oracle/divergences/.../rdb-commands.txt) hard-codes `break 0x2111f0`, which is only valid for the original build directory. It should look the address up with nm, or break on the symbol.
- exit_code 100 is nextest's (from 'command'), not that of the repro_cmd (cargo build + rdb exit 0).
- rdb exits 0 even when its commands fail (ESRCH), so an exit-code check cannot catch a broken replay.

### crypto-rdb-002 (rdb): PARTIAL

Recorded exit 0; observed exit 0. Full log: `logs/crypto-rdb-002.log`.

Commands run:

- `missing step supplied: cd oracle/rust-check && RUSTFLAGS='-C link-arg=-no-pie' CARGO_TARGET_DIR=target/repro cargo build --bin oracle_repro`
- `printf 'break 0x2111f0\ncontinue\nregister rdi\nregister rsi\nregister rdx\nnext\nvariable list\nquit\n' | rdb target/repro/debug/oracle_repro   (verbatim, twice)`
- `same printf with the address replaced by the nm address (0x211250 in this copy), twice`

Decisive output: Verbatim: stops in std::rt (rt.rs:206) with rdi = 0x254500, rsi = 0x252ed0, rdx = 0xfffffffffffffffc, so it does not show the claim. Adapted address, runs 1 and 2: `rdi = 0x7fffffff59a0` (hidden return pointer), `rsi = 0x7fffffff59b7` (&self), `rdx = 0x3fffffffc1` (the length); `variable list` prints only stack-slot addresses (`self = 0x7fffffff5978`, `plaintext_length = 0x7fffffff5980`). Both runs give identical stack addresses.

Notes: The ABI point reproduces once the break address is corrected: the hidden return pointer is in rdi, &self in rsi and the length in rdx. The claim 'the stack is randomized per run' does not reproduce here: two runs gave the same addresses, although host ASLR is enabled (randomize_va_space=2; ordinary processes get different stacks). It looks like rdb launched the debuggee with randomization off in this environment, while the original transcript shows randomized 0x7fff6b45... addresses, so this part depends on the environment.

Ledger defects:

- repro_cmd hard-codes break 0x2111f0 (not valid outside the original build path) and assumes target/repro/debug/oracle_repro has already been built (missing build step and cwd oracle/rust-check).

### crypto-oracle-001 (oracle): REPRODUCED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-oracle-001.log`.

Commands run:

- `nix develop ... -c 'python3 oracle/make_cases.py; git status --short oracle'`
- `nix develop ... -c 'python3 oracle/generate_oracle_tests.py; git status --short oracle'`
- `python3: count oracle/test-map.csv coverage_status; read cases.jsonl.manifest.json not_translated`

Decisive output: `wrote 1369 cases (1303 upstream-test); not translated: {...}`, exit 0; cases.jsonl, manifest, generated tests and test-map.csv byte-identical (git status clean). not_translated total 1606: XChaCha20Poly1305 192-bit nonce 1569, AEAD 64-bit nonce 1, ChaCha(8) 20, ChaCha(12) 2, ChaCha(20) 64-bit nonce 10, ChaCha(20) 192-bit nonce 4. test-map.csv: 34 rows, mapped 6 (1303 case IDs), unmapped 27, rust-only 1.

Notes: All counts match. 'Not compared' sub-checks are documentation (oracle/operations.md) and were read, not executed.

### crypto-oracle-002 (oracle): REPRODUCED-RESOLVED

Recorded exit 2; observed exit 2. Full log: `logs/crypto-oracle-002.log`.

Commands run:

- `nix develop ...#crypto-mixed -c bash -c 'cd crypto-mixed/upstream/botan && python3 configure.py --minimized-build --enable-modules=chacha20poly1305,chacha,poly1305 --disable-shared-library --cc=gcc --with-build-dir=<stage8c-replay>/oracle-build-gcc/botan'`
- `grep CXX/ABI_FLAGS <build>/Makefile; make -n -f <build>/Makefile libs (from upstream/botan; dry run)`
- `nix develop ... -c bash -c 'cd crypto-mixed && make -f <stage8c-replay>/oracle-build-gcc/botan/Makefile libs'`
- `nix develop ... -c bash -c 'cd crypto-mixed && make -f /tmp/crypto-mixed-oracle-build/botan/Makefile libs'   (repro_cmd verbatim; fails before compiling anything)`
- `workaround: CRYPTO_MIXED_ORACLE_BUILD=<stage8c-replay>/oracle-build oracle/build_upstream.sh; oracle_driver oracle/cases.jsonl <tmp>; cmp with oracle/golden/results.jsonl`

Decisive output: configure: `INFO: Implicit --cc-bin=clang++ due to environment variable CXX`, `WARNING: Tried to get gcc version, but output 'CLANG 21 1' is unexpected`, `INFO: Target is gcc:0.0-linux-x86_64`; generated Makefile `CXX = clang++`, compile lines `clang++ -fPIC -fstack-protector -m64 -pthread -std=c++20 ...` (gcc target flag set). make from the pilot root (both Makefiles): `make: *** No rule to make target 'src/lib/base/buf_comp.cpp', needed by '.../build/obj/lib/base_buf_comp.o'.  Stop.`, exit 2. Workaround: build_upstream.sh exit 0 (Target clang:21.1, modules aead base chacha chacha20poly1305 hex mac modes poly1305 rng stream utils, upstream/botan unmodified); the rebuilt driver's output for oracle/cases.jsonl is byte-identical to oracle/golden/results.jsonl.

Notes: Both symptoms and the workaround confirmed. The configure step used a build dir under stage8c-replay; /tmp/crypto-mixed-oracle-build was only read by make, which stopped before writing anything.

Ledger defects:

- repro_cmd only covers the make-from-pilot-root half and depends on a pre-existing /tmp/crypto-mixed-oracle-build Makefile; the --cc=gcc half needs the configure command from 'command'. It must be run from the workspace root ('cd crypto-mixed').

### crypto-oracle-003 (oracle): PARTIAL

Recorded exit 2; observed exit 1. Full log: `logs/crypto-oracle-003.log`.

Commands run:

- `build jsonvalue.cpp = date-creusot/oracle/driver.cpp lines 28-37 (std includes) + 48-69 (struct JsonValue) + a one-line main (read-only copy into stage8c-replay)`
- `nix develop ... -c clang++ -std=c++20 -c jsonvalue.cpp -o /dev/null   (then -std=c++17; and g++ -std=c++20)`
- `nix develop ... -c clang++ -std=c++20 -fsyntax-only -I date-creusot/upstream/date/include date-creusot/oracle/driver.cpp   (whole driver; then -std=c++17)`
- `sed -n '45,60p' oracle/driver.cpp (crypto-mixed workaround)`

Decisive output: clang 21.1.7 with libstdc++ 14.3.0 (/nix/store/...-gcc-14.3.0/include/c++/14.3.0), -std=c++20: `static assertion failed due to requirement 'std::__is_complete_or_unbounded(...std::pair<std::basic_string<char>..., JsonValue>...)': template argument must be a complete class...`, `arithmetic on a pointer to an incomplete type 'std::pair<std::basic_string<char>, JsonValue>'`, `incomplete type '_Value_type' (aka 'std::pair<std::basic_string<char>, JsonValue>') used in type trait expression`. Count: `5 errors generated.` (struct+main TU) and `4 errors generated.` (whole date-creusot driver, -fsyntax-only); exit 1. -std=c++17: compiles (exit 0). g++ 14.3 -std=c++20: compiles (exit 0). crypto-mixed's driver uses parallel `std::vector<std::string> object_keys; std::vector<JsonValue> object_values;`.

Notes: The defect reproduces: clang 21 + libstdc++ 14 in C++20 mode rejects std::vector<std::pair<std::string, JsonValue>> inside JsonValue, C++17 accepts it, and the workaround is in place. Not reproduced: the recorded '7 errors' (got 4 or 5, depending on the translation unit) and the recorded exit 2 (clang++ exits 1; 2 would be make/cmake's exit). Also found: the rejection is specific to clang+libstdc++, since g++ 14 accepts the same code in C++20.

Ledger defects:

- repro_cmd is prose with no translation unit or command line, so the '7 errors' count cannot be pinned down.
- exit_code 2 belongs to the `cmake --build` in 'command', not to the clang++ compile the repro describes (clang++ exits 1).

### crypto-ligature-013 (ligature): REPRODUCED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-ligature-013.log`.

Commands run:

- `baseline: python3 (descriptor write_set; both manifests' write_policy.protected_write_set/allowed_write_set)`
- `nix develop ... -c python3 -I tools/ligature/ligature.pyz validate-work-package ci/manifest/WP-CRYPTO-MIXED-{AEAD,PRIMITIVES}-001.json --specs-search-root crates`
- `python3 -I tools/ligature/ligature.pyz write-set-check --issue 48 --json`
- `at d401338 and 69645d2: restore oracle/driver.cpp and oracle/make_cases.py from 93407d0 as new files, then write-set-check --issue 48 --json; at d401338 also edit tracked oracle/oracle-PROTOCOL.md and rerun`

Decisive output: Baseline: descriptor allowed_roots includes 'oracle/**'; both manifests list oracle/** in write_policy.protected_write_set (not in allowed_write_set); validate-work-package `OK: work package manifest passes G1a and §10.1 checks`, exit 0 for both (two 10.1/info notes, no warning about the write_policy mismatch); write-set-check --issue 48 exit 0, state clean. d401338: descriptor protected_roots includes 'oracle/**', allowed_roots does not; 69645d2: oracle/** moved to allowed_roots.

Notes: All three parts of 'actual' reproduce. Surprise: at d401338 (Ligature 1.4.2) write-set-check --issue 48 still reports `write set is clean`, exit 0, when new files are written under protected oracle/** and even when tracked oracle/oracle-PROTOCOL.md is edited. Those files are listed only under protected_unvouched (`audit only -- the check cannot attribute them, so this verdict does not cover them`). So the pre-69645d2 block was a contract/policy block that the tool would not have enforced.

Ledger defects:

- The ledger 'command' (write-set-check --issue 48 --json) and repro_cmd (validate-work-package ...) are different commands; exit_code 0 holds for both, so nothing is wrong, but the pairing is confusing.

### crypto-oracle-004 (oracle): REPRODUCED

Recorded exit 0; observed exit 0. Full log: `logs/crypto-oracle-004.log`.

Commands run:

- `nix develop ... -c 'python3 oracle/generate_random_cases.py --seed 20261020 --driver /tmp/crypto-mixed-oracle-build/driver/oracle_driver; git status --short oracle'`
- `nix develop ... -c '/tmp/crypto-mixed-oracle-build/driver/oracle_driver oracle/random-cases.jsonl oracle/golden/random-results.jsonl; git status --short oracle'`
- `same generator + driver with the driver rebuilt from source (crypto-oracle-002)`
- `python3: outcome counts in golden/random-results.jsonl`
- `nix develop ... -c 'cd oracle/rust-check && cargo nextest run --profile ci'; junit.xml counts`

Decisive output: `wrote 1210 random cases to oracle/random-cases.jsonl (seed 20261020)`; random-cases.jsonl, manifest and golden/random-results.jsonl byte-identical. Golden: valid decrypt 200 x ok; mutated decrypt 195 authentication_failed + 5 ciphertext_too_short; 24 keystream_exhausted. nextest exit 0, junit `tests="2580" failures="0" errors="0"`. With the rebuilt driver the cases are identical too; only the manifest's `command` line differs (it records the driver path).

Notes: First attempt ran in the wrong directory because of a replay-script bug (copy helper failed after the previous copy was deleted). It ran nothing in a copy, wrote nothing, and was rerun cleanly; both attempts are in the log. Extra seeds 1-5 (6,050 cases) were not replayed; they are not part of repro_cmd.

