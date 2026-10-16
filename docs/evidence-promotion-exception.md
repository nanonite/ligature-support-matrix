# Evidence promotion exception — `date-creusot`, E-1 … E-15

**Status:** ratified by the workspace owner.
**Ratified:** 2026-09-26 (the actual date of the ruling).
**Scope:** the 15 evidence records listed below, at the exact hashes listed below.
**Origin:** chainlink #13 (Stages 0-3), reported by that task's own worker audit.

This is a one-time exception, not a precedent. It does not change the resolution
rule in `docs/reliance-policy.md`, and it deliberately does **not** bump that
document's `Policy version:` line — the existing promotion receipt records
`date-creusot-reliance-policy@1.0` and still validates against it:

    $ python3 tools/ligature/ligature.pyz validate-promotion specs/_promotions/date-creusot-core.json
    OK: promotion receipt passes G1a and §7.1 checks

## What the gap is

The pinned binary has a draft path for evidence records and no promotion path
for them. `draft` stages `evidence/E-1.json.draft` and validates it; `approve`
then refuses the same file, because evidence records carry no review block for
it to write:

    error: no validator recognizes target evidence/E-1.json — … Evidence records
    at evidence/*.json (workspace-level) are a valid draft target but are never
    approved — they carry no review block, so approve() cannot promote them.

So there is no sanctioned route from a validated draft to a usable evidence
record. The tool's own diagnostic states that the only way to get one is to move
the file by hand. This is filed upstream as **#78** ("Stage 0 evidence has a
draft path and no promotion path"), which is a real defect in ligature 1.0.0 and
is **not** a workspace policy choice.

## Why an exception rather than a re-run

Re-staging these 15 records would produce the same bytes: each file on disk is
byte-for-byte identical to its staged draft in
`analysis/ligature/draft-responses/`, and each hash matches the one already
recorded in the promotion receipt `PROM-DATE-CREUSOT-CORE-001`. There is no
defect to repair and nothing to gain. The only thing missing was a human
authorization step that the binary cannot perform for this artifact type.

## Disposition

The 15 records are kept and ratified as an inventory. What the promotion receipt
establishes is that inventory; what it cannot establish is human authorization,
because its `reviewer` field is a name, not an act. This record supplies the
missing authorization, limited to these 15 files at these hashes.

| Record | sha256 |
| --- | --- |
| E-1 | `sha256:42c52f37afa4f484e547b5c6217c6723882e4f074a6b58e369cf8b4b399dc2f1` |
| E-2 | `sha256:6df5baf9868cbb858600cd678a9bce57fe52931284377f2fc237a8ff547f5fd4` |
| E-3 | `sha256:41d2e505349c97ff34c5ef9424ceb957c25094b6de93a5dca2d4f199d6d3ecda` |
| E-4 | `sha256:691740c45b48108a8b1a47dce799cee065af62aea8291f27a4a4a566f0f531bf` |
| E-5 | `sha256:4d1d20ea74e8cd413840d9b18854301787220c1309483167406a93c113eb7a54` |
| E-6 | `sha256:4ee4ae13443bc82f18bd654a52baa0857cb996a10f06e2fb598a0e12830f744e` |
| E-7 | `sha256:4dcb751eb1bffa1d94d23019aefa506423585978d6069d435b915090f1effae9` |
| E-8 | `sha256:ea68d19c297ab2f3fd8a3c1811ad9988fd9077c8a88a7e50e04f7da11d8d3b0e` |
| E-9 | `sha256:a1bd780e8ea0720b9621144b75be02f687d6e4033f36492c529e57e1d9ec7cc4` |
| E-10 | `sha256:c5cafb40514cec1b008e11ac2e521eb47ff5237301ab82a3f44727c1dab0fab1` |
| E-11 | `sha256:28fb4ddda138f58bb8a8823c2e9289b7a20b4db2c2db57e92cdb41edeaf60f33` |
| E-12 | `sha256:38adc7e7a5ebb6b347251d54ff771219c96c55aff03eebdc573d657cba13f370` |
| E-13 | `sha256:beee09c8df5255958c1adbaada1775fa23d49bdd039cf5d9f585e6ba31f6aa2f` |
| E-14 | `sha256:441b90744b25970060003b289460682d4de3c4c8419c4570eb73c029f424690b` |
| E-15 | `sha256:9b268fc0d0b81c719688d7bfbd2e8a5f30767d8b90dff50dbe1399d90f53452d` |

Verify before relying on this record:

    $ sha256sum evidence/E-*.json

If any hash differs, this exception no longer covers that file and the record
must be re-ratified. The exception does not travel with a modified file.

## What this record does not do

- **It is not blanket permission to promote with `mv`.** It covers these 15
  files, at these hashes, for this defect (#78). Any other artifact type, any
  other workspace, or any later edit invalidates it. Future workers must not
  read it as precedent; #78 remains open and the mechanism gap remains a real
  gap until the binary provides a promotion path for evidence records.
- **It does not settle the eight unauthorized review blocks.** The four boundary
  and four interaction specs under `rust/date-creusot-core/specs/` each carry a
  hand-authored `review` block (`reviewer: chainlink-reviewer`,
  `reviewed_at: 2026-09-25`) that was not written by the sanctioned `approve`
  path. That is a separate violation with a separate ruling, and it is not
  addressed here.
- **It does not amend the promotion receipt.** `PROM-DATE-CREUSOT-CORE-001`
  covers all 24 artifacts, including the eight whose review blocks are in
  question. A receipt that spans both the ratified evidence and the contested
  specification artifacts cannot by itself settle either. That is why the
  documented whole-driver ratification path was deliberately not run: it would
  have approved the eight specification artifacts in the same act, conflating
  the two rulings.
- **It does not close #78** and does not substitute for a fix upstream.

## Provenance

Recorded by the workspace owner ruling of 2026-09-26 on chainlink #13. The
worker audit that surfaced the gap is in #13's comment thread; the upstream
defect report is #78. The artifacts themselves were produced by the chainlink
loop's worker attempts on #13 and ratified by the reviewer on the same task.
