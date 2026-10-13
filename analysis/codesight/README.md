# P3 Botan Codesight analysis (Chainlink #42)

Repository `local/botan-9e173108f3f6` was read from
`upstream/botan` at pinned commit
`2a81eef56c96c237e590c27f9a75e60317c9c700`. Index storage is
`analysis/codesight/index`; allowed roots were this pilot's `upstream/` and
`rust/` from `.mcp.json`.

Tool versions: codesight-mcp 0.6.0 (git
`816d523a1126b210afffa8a422760bbfce42f5f6`), tree-sitter 0.26.0,
tree-sitter-cpp 0.23.4, tree-sitter-c 0.24.2, and
tree-sitter-language-pack 1.20.0.

## Index

`index-folder.json` records `success: true`, 1,199 files, 15,643 symbols, and
languages `{cpp: 912, c: 193, python: 68, yaml: 10, json: 9, xml: 2,
bash: 3, toml: 1, html: 1}`. The tool also returned the warning `Skipped 706
secret file(s)`; this report does not infer which omitted files are relevant
to the algorithm subset.

The first index attempt failed because tree-sitter-language-pack tried to
create `.download.lock` under the read-only shared cache at
`/home/goya/.cache/tree-sitter-language-pack/v1.20.0/`. The local grammar
bundle was copied to `/tmp/crypto-mixed-codesight-cache` and the successful
index used `XDG_CACHE_HOME=/tmp/crypto-mixed-codesight-cache`. The initial
sanitized `CacheLockError` and workaround are recorded as
`crypto-mcp-001` in [`../../findings/limitations.jsonl`](../../findings/limitations.jsonl).

## Source map and usable graph results

| Area | Pinned source | Evidence |
|---|---|---|
| ChaCha quarter-round and scalar block | `src/lib/stream/chacha/chacha.cpp` | `chacha_quarter_round` at line 30; `ChaCha::chacha` at line 134; `ChaCha::cipher_bytes` at line 242; `ChaCha::generate_keystream` at line 269 |
| Poly1305 setup, blocks, final reduction | `src/lib/mac/poly1305/poly1305.cpp` | `poly1305_init` at line 93; `poly1305_blocks` at line 224; `poly1305_finish` at line 265; `Poly1305::add_data` at line 377 |
| AEAD buffer processing | `src/lib/modes/aead/chacha20poly1305/chacha20poly1305.cpp` | encryption `process_msg` at line 110; decryption `process_msg` at line 154 |

The full outlines, symbol contents, imports, searches, callers, callees, impact
results, type-hierarchy attempts, and call-chain attempts are saved as JSON in
this directory. The most useful positive results are:

- `get-callers` for `chacha_quarter_round` returned `ChaCha::chacha`,
  `hchacha`, and `ChaCha::set_iv_bytes`.
- `get-callers` for `poly1305_blocks` returned `Poly1305::add_data` and
  `Poly1305::final_result`; `get-callees` for `Poly1305::add_data` returned
  `poly1305_blocks` and `poly1305_extend_powers`.
- `get-imports` found 5 includes for the ChaCha scalar file, 6 for Poly1305,
  and 6 for the AEAD file. These are include names, not resolved header
  declarations.
- `get-symbol` captured the AEAD in-place order: encryption calls ChaCha on
  `buf` then authenticates the resulting ciphertext; decryption authenticates
  the ciphertext before calling ChaCha on that same buffer.

These successful results are bounded by the gaps below; the call graph is not
a source of truth without checking each edge against its symbol body.

## Measured analysis gaps

### C++ headers and type hierarchy

`get-file-outline` returned exit 1 and `File not found in index` for each
selected header: `chacha.h`, `poly1305.h`, and
`chacha20poly1305.h`. `get-type-hierarchy` returned `Symbol not found` for
the ChaCha and Poly1305 class IDs. This means Codesight did not provide the
class declarations or state layout needed to inspect inheritance and API
boundaries. Record: `crypto-mcp-002`.

### Incorrect and incomplete call relationships

`get-callees` for `ChaCha::chacha` returned both the real
`chacha_quarter_round` helper and `store_le` from the unrelated
`src/lib/block/idea/idea_avx2/idea_avx2.cpp`. The latter is a false edge. The
same query did not return the macro-gated AVX implementations.

`get-callees` for AEAD encryption `process_msg` returned only `cipher1`, while
the saved `get-symbol` body also contains `m_poly1305->update(buf, sz)`. A
call-chain query from that method to `Poly1305::add_data` returned
`path_count: 0`; the dynamic API edge was not resolved. `get-impact` for
`ChaCha::chacha` returned zero affected symbols. Records:
`crypto-mcp-003` and `crypto-mcp-004`.

### Templates, macros, and SIMD

`search-text` found eight `BOTAN_HAS_CHACHA_*` preprocessor guards in
`chacha.cpp` (lines 97–157), and found AVX2/AVX512 method text in their
separate source files. Yet `get-file-outline` returned only a module symbol
for each ChaCha AVX2, AVX512, and SIMD32 file. Poly1305 AVX2 and AVX512
outlines each returned only a `raw()` helper; the AVX512 source has template
declarations at lines 42 and 68 that the outline omitted. These are
tree-sitter coverage gaps, not evidence that the optimized implementation is
absent. Record: `crypto-mcp-005`.

The P3 plan names scalar core-functional and byte-layer clusters. No Rust SIMD
implementation or scope ruling has been made; optimized-provider parity stays
open for that decision. [`../../PORT-GAPS.md`](../../PORT-GAPS.md) links the
transfer risks to the finding IDs.

## Ligature comparison deferred until initialization

`extract-c-static --help` works in the current uninitialized pilot, but the
actual command requires a project descriptor. Under Ligature 1.3.5 it exits
1 with an actionable missing-descriptor error rather than the old 1.2.0
traceback. The exact output is in
[`extract-c-static-before-init.txt`](extract-c-static-before-init.txt).
Because Chainlink #43 owns initialization and is currently after #42, the
Codesight-vs-`extract-c-static` comparison must run in a follow-up blocked by
#43 and before Stage 0–3 (#44). No initialization was performed during #42.

## Artifact index

- `index-folder.json`, `repo-outline.json`, and `tree-chacha.json`
- `search-*.json`, `text-*.json`, and `macros-*` / `templates-*` / `simd-*`
- `outline-*.json` and `imports-*.json`
- `callers-*`, `callees-*`, `impact-*`, `chain-*`, and `hierarchy-*`
- `symbol-*.json` for the quarter-round, ChaCha block/stream, Poly1305
  arithmetic, and AEAD encrypt/decrypt methods
- `extract-c-static-before-init.txt`
