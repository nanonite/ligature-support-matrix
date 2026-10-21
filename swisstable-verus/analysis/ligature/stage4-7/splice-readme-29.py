#!/usr/bin/env python3
"""One-shot: splice the chainlink #29 Stage 4/4.5/7 section into README.md.

The two 48-artifact command blocks are extracted programmatically from
analysis/ligature/stage4-7/stage45-scratch-proof.txt (transcript lines 278 and 287) rather
than retyped, so the README cannot drift from the measured transcript. Also refreshes the
stale "not this stage" bullet and adds the two new rows to "Blocked on upstream".
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from path_root import pilot_root

ROOT = pilot_root()  # walks up to the dir holding project-descriptor.json
assert os.path.isfile(os.path.join(ROOT, "project-descriptor.json")), ROOT
os.chdir(ROOT)

PRE = "$ python3 tools/ligature/ligature.pyz "
lines = open("analysis/ligature/stage4-7/stage45-scratch-proof.txt").read().splitlines()


def fmt(idx, verb):
    line = lines[idx - 1]
    assert line.startswith(PRE + verb), line[:70]
    body = line[len(PRE):].replace("scratch-approval-proof", "$R")
    parts = body.split(" --artifact ")
    head, arts = parts[0], parts[1:]
    assert len(arts) == 48, len(arts)
    out = ["python3 tools/ligature/ligature.pyz " + head + " \\"]
    for i, a in enumerate(arts):
        out.append("  --artifact " + a + ("" if i == len(arts) - 1 else " \\"))
    return "\n".join(out)


RULING = fmt(278, "record-ruling")
PROMO = fmt(287, "accept-promotion")

SECTION = """## Stage 4 / 4.5 / 7: validation, gates, promotion, and the work-package manifest (chainlink #29)

### Stage 4 and Stage 4.5 on the live root are PENDING the operator batch, not failed

Nothing was approved on the live root. All 45 Stage 0-3 drafts are still `.json.draft`,
`ci/results/` holds only the Stage 0 `evidence_promotions.jsonl`, and there is **no**
`ci/results/review_log.jsonl`, **no** `ci/results/human_rulings.jsonl` and **no**
`specs/_promotions/`. The entire Stage 4 + Stage 4.5 sequence was instead run end to end on
an rsync scratch copy of this root -- `analysis/ligature/stage4-7/stage45-scratch-proof.sh`,
transcript `analysis/ligature/stage4-7/stage45-scratch-proof.txt` -- with the reviewer name
`scratch-approval-proof`, deliberately not a plausible human name, so a ruling logged there
can never be mistaken for the operator's. Everything quoted below is copied from that
transcript, not predicted.

Live root as it stands, full transcript in `analysis/ligature/stage4-7/live-root-stage4.txt`:

```
validate                       exit 0   OK (nothing to check: no boundary contracts discovered under .)
validate-interaction           exit 0   OK (nothing to check: no interactions discovered under .)
validate-bridge                exit 1   6 x [G1a] 'review' is a required property, on the 6 .draft   (#110)
validate-evidence              exit 0   OK: all evidence records pass G1a/G1b (11 discovered)
validate-conflict-resolution   exit 1   1 x [G1a] 'review' is a required property, on EC-1.json.draft (#110)
validate-witness               exit 1   2 x [G1a] 'review' is a required property, on the 2 .draft    (#110)
validate-exemption             exit 0   OK (nothing to check: no exemptions discovered under .)
validate-protocol-debt         exit 0   OK (nothing to check: no protocol-debt records discovered under .)
check                          exit 3   result: exit_code=3 conditions=['human_decision_required']
status                         exit 0   human decisions pending: 9
write-set-check                exit 0   write set: clean
doctor                         exit 0
gate-g9                        exit 1   FAIL: no promoted bridge discovered -- G9 has nothing to check
check-bridges                  exit 0   OK: 0 artifact(s) written; every promoted bridge compiled and was dispatched
gate-r1-g16                    exit 1   error: no C_static reports at ci/results/c_static/
gate-g14                       exit 1   error: no closure directory at specs/_closure
gate-g18 / g19 / g20           exit 0   OK (nothing to check: no witness specs discovered under .)
validate-closure               exit 0   OK (nothing to check: no closure artifacts discovered under .)
select-pilot-cluster           exit 1   Evaluated 0 candidate cluster(s)
```

The three validator exit-1s and `check`'s exit 3 are the **nine outstanding human
approvals**, not defects -- the same state chainlink #28 left the tree in. `gate-g9`'s
exit 1 is the "a gate that passes over zero bridges would claim what it never ran"
refusal, and it is exactly right here.

**The 1.1.1 warning carried on issue #29 about `check-bridges` / `gate-g9` crashing on a
relative `--workspace` is stale.** That was #96, fixed in 1.2.0. Measured on the scratch
copy with all 6 bridges promoted, both commands produce the correct 6 G9 findings with a
relative `--workspace .` *and* with an absolute one, with no `ValueError`. No workaround
is needed.

### Stage 4.5 works -- but two human-authority steps sit in front of it

Measured, in this order, on the scratch copy after all 36 approvable artifacts approved at
exit 0:

1. **`accept-promotion` refuses before it ever reaches the ruling gate**, on the policy
   document as it ships:

   ```
   $ python3 tools/ligature/ligature.pyz accept-promotion swisstable-verus-core --reviewer scratch-approval-proof --artifact docs/reliance-policy.md --artifact evidence/E-001.json ... (48)
   error: 'docs/reliance-policy.md' must have exactly one 'Policy version: <name>@<major>.<minor>' marker line (docs/reliance-policy.template.md's own convention) -- found 0
   EXIT=1
   ```

   `init` installs `docs/reliance-policy.md` as the template, placeholders intact, and the
   descriptor points `compatibility_policy.reliance_policy_path` at that same file -- so it is
   automatically both an `--artifact` and the `--policy-path`. `accept-policy`, the command
   documented as the way to ratify that policy, fails the same way (exit 2, same message),
   because it needs the marker line it exists to establish. The file is a
   `write_set.protected_roots` path, so an agent cannot fix it, and its project-specific
   section is unfilled too. Filed as **epic #1 #114**; logged as
   `swisstable-ligature-011`. **This is a human step: fill in `Schema version`, `Owner:`
   and a real `Policy version: <name>@<major>.<minor>` before running the batch.**

2. **With the policy filled, the human-ruling gate is real and fail-closed.** Zero rulings:

   ```
   error: refusing to mint a promotion receipt: no complete human ruling covers this accepted set
     (Stage 4.5 is gated on an explicit `record-ruling` verdict for every artifact):
     - no human ruling log at ci/results/human_rulings.jsonl -- none of the 48 artifact(s) about to
       be promoted has been ruled on: ...; record the ruling first with
       `record-ruling --reviewer <name> --verdict ratified|rejected --artifact <path> [--artifact <path> ...]`
   EXIT=1
   ```

### Steps 6-9 -- the promotion commands, verbatim from the measured transcript

The accepted set is **48 artifacts**: `docs/reliance-policy.md`, the 11 promoted evidence
records, `specs/_conflicts/EC-1.json`, the 14 boundary contracts, the 15 interactions and
the 6 bridges. The 2 witness drafts and the 7 concept specs are **not** in it -- neither is
approvable (#111). Both commands below were run exactly as written (with
`scratch-approval-proof` in place of `$R`) and are reproduced from transcript lines 278 and
287, not written from memory.

**Step 6 -- accept the policy.** Requires step 1 above to have been done by a human first.

```
python3 tools/ligature/ligature.pyz accept-policy --reviewer $R
```
Expected:
```
accepted policy: docs/reliance-policy.md
reviewer: scratch-approval-proof
policy version: swisstable-verus-reliance-policy@0.0
previous hash: sha256:36f20f198ab1de91a2dabed8242ce1a2c1a5edc4f841803f62b6e5bd24e2eea9
accepted hash: sha256:5bf42eba64872c8dd99a8a8f62fcabd850752eaaa73822e784a74a2168d1f5c1
EXIT=0
```

**Step 7 -- record ONE ratified human ruling over all 48 artifacts.** One command settles the
whole set; a ruling is hash-pinned to the exact content it covered, so re-run it if any
artifact changes afterwards.

```
__RULING__
```
Expected:
```
recorded ruling: ratified over 48 artifact(s)
reviewer: scratch-approval-proof at 2026-10-02
log: ci/results/human_rulings.jsonl
EXIT=0
```

**Step 8 -- accept the promotion.**

```
__PROMO__
```
Expected:
```
accepted: specs/_promotions/swisstable-verus-core.json
EXIT=0
```

**Step 9 -- validate the receipt ligature just wrote.**

```
python3 tools/ligature/ligature.pyz validate-promotion specs/_promotions/swisstable-verus-core.json
```
Expected:
```
OK: promotion receipt passes G1a and §7.1 checks
EXIT=0
```

The receipt that produces (fields; `artifact_manifest` elided -- 48 entries):

```
schema: "promotion-receipt/1.0"
promotion_id: "PROM-SWISSTABLE-VERUS-CORE-001"
cluster: "swisstable-verus-core"
reviewer: "scratch-approval-proof"
policy_version: "swisstable-verus-reliance-policy@0.0"
schema_versions: {"evidence": "1.0", "conflict_resolution": "1.0", "boundary": "1.0", "interaction": "1.0"}
accepted_at: "2026-10-02"
artifact_manifest: [ 48 entries ]
   first: {"path": "docs/reliance-policy.md", "hash": "sha256:5bf42eba64872c8dd99a8a8f62fcabd850752eaaa73822e784a74a2168d1f5c1"}
```

**`PROM-SWISSTABLE-VERUS-CORE-001` is derived, not chosen**: `accept-promotion` computes
`promotion_id` from `cluster` alone. That is why it is safe to record in the Stage 7 manifest
before the real receipt exists. `policy_version` above is the *scratch* placeholder version
and will be the operator's own once step 6 is taken for real.

### All 36 approvals succeed; G9 then fails on all 6 bridges

The 36 `approve` commands in steps 1-4 above all exit 0, and the post-approval validators
agree with this runbook's earlier predictions exactly:

```
validate               exit 0   OK: all boundary contracts pass G1a/G1b/G2+ (14 discovered)
                                 + INFO: 20 non-blocking finding(s), all [G2+] applies_to unverifiable (#111)
validate-interaction   exit 0   OK: all interactions pass G1a/G1b (incl. computed eligibility),
                                 G15 protocol coverage, and R2 coverage (15 discovered)
validate-bridge        exit 0   OK: all bridges pass G1a/G1b (incl. conclusion consistency)
                                 and G2 boundary cross-reference (6 discovered)
check                  exit 3   conditions ['human_decision_required'], 28 findings:
                                 2 medium G1a (the 2 witness drafts), 6 info G2, 20 info G2+
status                 exit 0   artifacts (48): promoted=47, validated=1
                                 obligations: 11 declared, 11 with an unmet required dimension
                                 human decisions pending: 2
write-set-check        exit 0   write set: clean
```

**`gate-g9` and `check-bridges` then fail, on all 6 bridges, at exit 1:**

```
  - [G9/error] BR-CONTROLBYTES-CLEARDEAD-001: bridge_logic does not compile for verus: unexpected character '=' at offset 27 in 'self.ctrl(self.capacity()) == SENTINEL' -- the compilable fragment is predicate application only: no operators, literals, quantifiers or negation
  - [G9/error] BR-CONTROLBYTES-SETDEAD-001: ... unexpected character '<' at offset 5 in 'slot < self.capacity()' ...
  - [G9/error] BR-GROUPPROBE-FREE-WINDOW-001: ... binding name 'GROUP_WIDTH' is not snake_case -- it becomes a harness parameter name
  - [G9/error] BR-GROUPPROBE-WINDOW-001: ... binding name 'GROUP_WIDTH' is not snake_case ...
  - [G9/error] BR-PROBESEQ-MASK-001: ... unexpected character '+' at offset 14 in 'capacity_mask + 1 == (1usize << capacity_bits)' ...
  - [G9/error] BR-RAWINSERT-NONFULL-001: ... unexpected character '>' at offset 16 in 'self.capacity() >= GROUP_WIDTH' ...
```

This is **not** a pilot authoring slip. The installed
`.ligature/prompts/stage-3-bridge-drafting.md` says of `premises`, at line 40,
`"premises": ["<premise expression>"]`, and at lines 112-114 calls a premise "at least one
premise expression"; it documents snake_case only for the *different* field
`required_local_facts[].fact_id` and says nothing about `bindings`. Nothing checks either
G9 rule before approval: all 6 staged at `OK: generated draft passes G1a/G1b immediate
checks`, passed `validate-bridge` at exit 0, and were each written `approved: <path> (new)
by scratch-approval-proof at 2026-10-02` at exit 0. Filed as **epic #1 #113**; logged as
`swisstable-ligature-010`. **The 6 bridges must be re-cut -- predicate application only,
snake_case bindings -- before they are promoted for real.** Re-run
`analysis/ligature/stage4-7/stage45-scratch-proof.sh` afterwards and require `gate-g9` exit 0.

### Stage 7: `ci/manifest/WP-SWISSTABLE-VERUS.json`

**Hand-authored.** ligature 1.2.1 ships no Stage 7 work-package generator: `--help` lists
43 verbs and none of them generate one. `validate-work-package` is explicitly validate-only
("Standalone, not routed through draft/approve -- a manifest is machine-generated at Stage 7
from already-promoted content"), so the generator it refers to does not exist. As P1 did, the
manifest is therefore written by hand and flagged as such.

```
$ python3 tools/ligature/ligature.pyz validate-work-package ci/manifest/WP-SWISSTABLE-VERUS.json ; echo $?
INFO: 2 non-blocking finding(s)
  - [10.1/info] ...: provenance.promotion_id 'PROM-SWISSTABLE-VERUS-CORE-001' cannot be
    resolved against a real promotion receipt yet -- chainlink #15 (detached promotion receipt)
    is not implemented
  - [10.1/info] ...: "every owned function's source path is covered by allowed_write_set" is not
    checked -- functions[] are Rust module paths with no schema-computable mapping to a file path
    without searching real crate source, which this workspace doesn't have
OK: work package manifest passes G1a and §10.1 checks
0
```

Both remaining infos are pre-existing "not implemented / not checked" notices about the
schema, not findings about this pilot's content, and they are the same two P1 got.

Every value in it is **derived**, not remembered.
`analysis/ligature/stage4-7/make-work-package-manifest.py` stands in for the missing
generator: it reads the 7 concept specs, the descriptor, the installed scripts and the rustc
host triple, and re-running it reproduces the file byte-for-byte. It refuses to write rather
than guess -- it checks that every constraint's `applies_to` names a real declared method,
that every bridge's `callee_requirement` equals its own
`bridge_logic.conclusion.obligation_id` and is a precondition-kind obligation, and that no
precondition obligation is also in `provided_guarantees`.

Shape, and the three P1 mistakes it avoids:

| field | value | why |
|---|---|---|
| `depends_on` | `[]` | This is the only work package in the workspace. P1's first manifest named `WP-DATE-CREUSOT-CORE`, which resolves to nothing. |
| `required_guarantees` | `[]` | A single-WP crate has no external callee. P1 listed `Weekday.C2/C3` in both `provided_guarantees` and `required_guarantees`; CG6 correctly called that a work package assuming its own output ("mutual satisfaction is not soundness"). |
| `write_policy` | **verbatim** copy of the descriptor's `write_set` (17 allowed / 10 protected) | This pilot's descriptor already carries crate-scoped protected globs (`rust/*/Cargo.toml`, `rust/*/build.rs`), so P1's `date-ligature-034` overlap cannot arise and no narrowing is needed. Both lists are checked equal to the descriptor by `check-runbook-29.py`. |
| `gate_integrity` | `sha256:0b844c7e...946bd` / `sha256:09dc6a92...39854` | The **real** sha256 of `scripts/witness_renderer.py` and `scripts/xml_escape.py`, recomputed by the generator from the installed files. G13 verifies both, requires each to have `protected_write_set` coverage and forbids `allowed_write_set` coverage. |
| `report.emit` | `ci/results/WP-SWISSTABLE-VERUS.json` | P1 pointed `emit` at `ci/results/feature_ledger.json`, where `report feature-ledger` and `record-assurance` then collided on one path with incompatible schemas. One path, one writer. |
| `obligations` | 36 = 30 `provided_guarantees` + 6 `required_preconditions_to_establish` | The 6 precondition obligations are established at the call site and discharged by the bridges (the only shape satisfying bridge G2, see #112), so they are never also "provided". One entry per **bridge** -- `GroupProbe.C001` has two bridges, so 6 bridges and 5 distinct bridged obligations. |
| `gates` | 9 (P1's 7 plus `g2`/`g9`) | This pilot has 6 bridges; P1 had none. |

Two schema facts were **measured by probing** `validate-work-package`, not guessed, and both
are now comments in the generator: `required_claims` has exactly two permitted values,
`callee-precondition-established` and `postcondition-holds` (there is no separate invariant
claim, so an `invariant` obligation is certified as `postcondition-holds`); and
`required_preconditions_to_establish` entries take exactly `bridge_id`,
`callsite_requirement` and `required_assurance`, with `callsite_requirement` having exactly
one permitted value, `all-discovered-resolved`.

Two things the generator found that are worth a human's eye:

- **`HashMix.C001` is a precondition obligation with no bridge.** It is the precondition on
  the one `inform` edge (`RawTable.find -> HashMix.h2`), which has no boundary contract and
  so nothing for a bridge to discharge. That is consistent, not an omission, but it means
  `HashMix.C001` is established by nothing the pipeline tracks.
- **`HashMix.h2` is `witness_required: true` and has no witness spec.** There are 3 such
  queries (`ControlBytes.count_empty`, `GroupProbe.match_full`, `HashMix.h2`) and only 2
  witness drafts. This is currently invisible because #111 keeps `accept-promotion` from
  reaching that check -- once #111 is fixed, `accept-promotion` will refuse outright until
  the third witness exists. Add it to the batch rather than discovering it then.

`provenance.artifact_set_hash` is the sha256 of the **scratch** proof's receipt, because the
schema requires the field and pattern-checks it against `^sha256:[0-9a-f]{64}$`, leaving no
honest way to write "pending". It is a real hash of a real file but it is not the live-root
artifact set; that is stated in the manifest's own `coupling_notes`, and
`provenance.promotion_id` + `provenance.artifact_set_hash` are the two fields to re-read once
the real receipt exists.

`ci/manifest/**` is in `write_set.protected_roots`, so this file is a protected-root write
done under explicit operator direction, exactly as P1's was. `write-set-check` reports the
root `clean` with 0 violations either way -- the known #90 false negative -- so it is not
evidence that the write was sanctioned.

### Keeping this section honest

`analysis/ligature/stage4-7/check-runbook-29.py` re-derives every number and hash quoted
above from the real files and exits 1 if this section disagrees -- the same discipline as
`analysis/ligature/stage0-3/check-runbook.py`, added for the same reason: the counts in this
README moved while the work was being done.

```
$ python3 analysis/ligature/stage4-7/check-runbook-29.py ; echo $?
...
0
```
"""

SECTION = SECTION.replace("__RULING__", RULING).replace("__PROMO__", PROMO)

readme = open("README.md").read()

OLD_BULLET = "- `accept-promotion`, `record-ruling`, `accept-policy` — not this stage."
NEW_BULLET = (
    "- `accept-promotion`, `record-ruling`, `accept-policy` — not *this* stage. They are\n"
    "  Stage 4.5 and they are the operator's to take; the exact commands and their measured\n"
    "  output are in \"Stage 4 / 4.5 / 7\" below."
)
assert readme.count(OLD_BULLET) == 1, readme.count(OLD_BULLET)
readme = readme.replace(OLD_BULLET, NEW_BULLET)

OLD_ROW = ("| any bridge discharging a callee precondition without listing it in `callee_guarantees` "
           "| the two Stage 3 templates disagree | **epic #1 #112** |")
NEW_ROWS = OLD_ROW + (
    "\n| **G9 failing on all 6 promoted bridges** | `stage-3-bridge-drafting.md` never states that "
    "`premises` must be predicate application only or that `bindings` keys must be snake_case, "
    "and no pre-approval gate checks either | **epic #1 #113** |"
    "\n| **`accept-promotion` refusing before the ruling gate** | `init` ships "
    "`docs/reliance-policy.md` with its `Policy version:` placeholder and `accept-policy` needs "
    "the same line it exists to stamp; the file is a protected root | **epic #1 #114** |"
)
assert readme.count(OLD_ROW) == 1
readme = readme.replace(OLD_ROW, NEW_ROWS)

if "## Stage 4 / 4.5 / 7:" in readme:
    raise SystemExit("section already present; refusing to duplicate")
readme = readme.rstrip("\n") + "\n\n" + SECTION
open("README.md", "w").write(readme)
print("README.md updated")
