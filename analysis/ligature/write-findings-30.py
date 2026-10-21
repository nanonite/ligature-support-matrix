#!/usr/bin/env python3
"""Write chainlink #30's findings to findings/limitations.jsonl.

Idempotent in both directions: every row whose `id` appears below *replaces* the
ledger row of the same id if there is one, so re-running leaves the file
byte-identical, and a row's text can be corrected without leaving both the old
and the new version in the ledger. Rows owned by other issues are untouched.
"""
import collections
import hashlib
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
LEDGER = HERE.parent.parent / "findings" / "limitations.jsonl"

LIGATURE_PYZ = (HERE.parent.parent / "tools" / "ligature" / "ligature.pyz").resolve()
PYZ = hashlib.sha256(LIGATURE_PYZ.read_bytes()).hexdigest()
version_output = subprocess.check_output(
    [sys.executable, str(LIGATURE_PYZ), "version"], text=True
)
version_line = version_output.splitlines()[0]
content_hash = re.search(r"content hash: (sha256:[0-9a-f]{64})", version_output)
if not content_hash:
    raise SystemExit("ligature version did not report an attested content hash")
LIGATURE_VER = f"{version_line} (content hash {content_hash.group(1)})"
VERUS_PATH = "/nix/store/57l94534x07sysi7gjf4zkkpai6cw6vc-verus-tools/bin/verus"
VERUS_VER = ("Verus 0.2026.05.24.ecee80a; profile release; platform linux_x86_64; "
             "toolchain 1.95.0-x86_64-unknown-linux-gnu")

# findings-schema.md requires these three on every row; they identify the tooling the
# finding was observed against, not the finding itself.
TOOL_ENV = {
    "ligature": (LIGATURE_PYZ, LIGATURE_VER),
    "verus": (VERUS_PATH, VERUS_VER),
}

# Capture commands, results and statuses from one snapshot of each transcript.
# The runner currently uses --multiple-errors 200, but an override is possible;
# quoting the capture avoids labeling one budget with another's result.
CRATE_TRANSCRIPT = HERE.parent.parent / "analysis" / "verus" / "verus-transcript.txt"
PROBE_TRANSCRIPT = HERE.parent.parent / "analysis" / "verus" / "reachability-probe.txt"
RESULTS = re.compile(r"verification results::\s*(\d+) verified,\s*(\d+) errors")
EXIT = re.compile(r"^exit=(\d+)$", re.MULTILINE)


def transcript_result(path):
    """Return (text, command, result, verified, errors, exit) from one capture."""
    if not path.exists():
        raise SystemExit(f"{path} is missing; run `bash analysis/verus/run-verus.sh` first")
    text = path.read_text()
    lines = text.splitlines()
    result = RESULTS.search(text)
    status = EXIT.search(text)
    if not lines or not lines[0].startswith("$ nix develop ") or not result or not status:
        raise SystemExit(f"{path} is incomplete; run `bash analysis/verus/run-verus.sh`")
    return (text, lines[0][2:], result.group(0), int(result.group(1)),
            int(result.group(2)), int(status.group(1)))


def _module(stem):
    """Load analysis/verus/<stem>.py by path, whatever its filename's separators are."""
    import importlib.util

    path = HERE.parent / "verus" / (stem.replace("_", "-") + ".py")
    spec = importlib.util.spec_from_file_location(stem.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def error_locations(text):
    """-> {file: count} of primary error locations, read out of the transcript."""
    _results, errs, _files, _kinds = _module("err_summary").parse(text)
    return collections.Counter(f for _k, f, _l in errs if not f.startswith("rust/"))


def error_functions(text):
    """-> {function: count} of primary error locations, derived from the transcript.

    Same parser chain `analysis/verus/errors-by-fn.py` uses, so the numbers a row
    quotes and the numbers `python3 analysis/verus/errors-by-fn.py` prints cannot
    drift apart.  Nothing here is a literal.
    """
    ebf = _module("errors-by-fn")
    _results, errs, _files, _kinds = _module("err_summary").parse(text)
    index = ebf.function_index()
    counter = collections.Counter(index[(f, l)][0] for _k, f, l in errs)
    return collections.Counter({k: v for k, v in counter.items() if k != "<unknown>"})


CRATE_TEXT, VERIFY, CRATE_OUT, CRATE_OK, CRATE_BAD, CRATE_EXIT = transcript_result(CRATE_TRANSCRIPT)
PROBE_TEXT, PROBE, PROBE_OUT, PROBE_OK, PROBE_BAD, PROBE_EXIT = transcript_result(PROBE_TRANSCRIPT)
CRATE_FILES = ", ".join(f"{f} {n}" for f, n in sorted(error_locations(CRATE_TEXT).items())) or "none"
_fn = error_functions(CRATE_TEXT)
CRATE_FUNCTIONS = ", ".join(f"`{k}` {v}" for k, v in sorted(_fn.items(), key=lambda kv: (-kv[1], kv[0]))) or "none"
CRATE_FUNCTIONS_TOTAL = sum(_fn.values())
CRATE_OPEN = CRATE_BAD != 0 or CRATE_EXIT != 0


ROWS = [
    dict(
        id="swisstable-verus-001",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("The port replaces Abseil's policy-parameterized, uninitialized raw "
                 "slot storage with initialized vectors: `ControlBytes` stores control "
                 "bytes in `Vec<u8>`, RawTable stores parallel `Vec<u64>` hashes, and "
                 "SwissTable stores `Vec<u64>` values. It uses no `unsafe`, raw slot "
                 "pointers, or `MaybeUninit`; upstream poisons/unpoisons slot memory "
                 "and ties object lifetime to control-byte transitions. This changes "
                 "physical layout, initialization, destruction, and sanitizer behavior."),
        repro_cmd=VERIFY,
        exit_code=1,
        expected=("Either (a) a Vec-backed representation, with the memory/behaviour "
                  "delta recorded as a scope cut, or (b) an unsafe/raw-slot layer owned "
                  "by a second verifier."),
        actual=("Vec-backed, chosen at the implementation level only. "
                "verifier_policy in the descriptor and its `supporting` key are "
                "untouched, so chainlink #35 still decides whether the unsafe layer "
                "becomes a Kani sub-cluster or stays a scope cut at the descriptor "
                "level. Verus never sees `unsafe`, so there is nothing for it to reject."),
        workaround=("Initialized `Vec<u8>` control bytes, parallel `Vec<u64>` hashes, "
                    "and a separate `Vec<u64>` value store. The logical model is "
                    "proof-friendly; physical lifetime and address semantics are not "
                    "claimed equivalent and remain for #32 to compare where observable."),
        severity="scope-cut",
        revisit_trigger=("chainlink #35 decides the unsafe/raw-slot question; re-visit "
                         "if the descriptor grows verifier_policy.supporting, in which "
                         "case the Vec fallback becomes the documented second cluster."),
    ),
    dict(
        id="swisstable-verus-002",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("Group probing was implemented as the scalar `Group` only. The "
                 "reference's `GroupSse2Impl`/`GroupArmNeonImpl` "
                 "(hashtable_control_bytes.h L285-L470) compute the same masks with "
                 "`_mm_cmpeq_epi8`, `_mm_movemask_epi8`, `_mm_subs_epi8` and NEON "
                 "equivalents. The port contains no intrinsic and no target_feature, "
                 "so the SIMD half of the subset is not ported."),
        repro_cmd=("grep -c '_mm_\\|std::arch\\|core::arch' "
                   "rust/swisstable-verus-core/src/group_probe.rs"),
        exit_code=1,
        expected=("Either SIMD group code, or an explicit statement that the SIMD half "
                  "is out of scope for this port."),
        actual=("Scalar only, deliberately: chainlink #36 has not decided whether SIMD "
                "is in scope, a Kani-owned sub-cluster, or a scope cut, and issue #30 "
                "does not pre-empt that decision. The scalar masks are semantically the "
                "same 16 answers -- same `uint16_t` mask, same bit per slot -- so the "
                "concept's obligations are unaffected."),
        workaround="Scalar `Group` over a 16-byte window; no divergence in answers.",
        severity="scope-cut",
        revisit_trigger="chainlink #36 decides the SIMD reach question.",
    ),
    dict(
        id="swisstable-verus-003",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("The plan's P2 question -- where `unsafe` and raw-pointer slots exceed "
                 "Verus -- did not arise in this port, because the Vec-backed "
                 "representation of swisstable-verus-001 needs no unsafe at all. No "
                 "unsupported Verus feature was hit on that axis."),
        repro_cmd=("grep -rn 'unsafe\\|\\*mut\\|\\*const\\|from_raw\\|transmute' "
                   "rust/swisstable-verus-core/src/ rust/swisstable-verus-core/verif/"),
        exit_code=1,
        expected="Either a Verus failure on an unsafe/raw-pointer construct, or none.",
        actual="Zero occurrences of `unsafe`, raw pointers or transmute in the port.",
        workaround="Not needed; recorded so #35 knows the question was asked.",
        severity="friction",
        revisit_trigger="chainlink #35, if it decides to build an unsafe layer anyway.",
    ),
    dict(
        id="swisstable-verus-004",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("RawTable::find's probe-coverage property is not proved. The reference "
                 "terminates a lookup because its probe sequence visits every slot of a "
                 "2^k-1 table exactly once; that is the bijection j -> j(j+1)/2 mod "
                 "2^(k-4), which needs a bit-level induction over the quadratic-probing "
                 "offset. Without it a bounded probe run cannot distinguish 'absent' "
                 "from 'ran out of groups'."),
        repro_cmd=VERIFY,
        exit_code=1,
        expected=("Either a proved coverage lemma -- so `None` provably means absent -- or "
                  "an explicit bounded probe whose miss case is recorded."),
        actual=("The probe run is bounded by the group count, which terminates "
                "unconditionally, and followed by a full scan of the slot array, so "
                "`find` is complete (`None` provably means absent) at the cost of its "
                "worst case. RawTable.C006 is proved; expected O(1) is not what is "
                "proved. This is a scope cut about the *algorithm*, not about Verus: "
                "the probe wrap itself is the reference's `& capacity_mask` and is "
                "proved."),
        workaround="Bounded probe plus linear fallback scan. Completeness is proved; the "
                   "constant factor is not.",
        severity="scope-cut",
        revisit_trigger=("a quadratic-probing coverage lemma is written, or the "
                         "differential oracle (issue #32) shows the fallback is never "
                         "needed in the case corpus."),
    ),
    dict(
        id="swisstable-verus-005",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("Four helpers in the crate are not in the work-package manifest's "
                 "`functions` list, so Stage 8A's call-graph check may report them as "
                 "unintended call edges: `claim_first_free` (module-private free "
                 "function, the scalar find-first-non-full primitive), and "
                 "`num_groups_exec`/`bit_set`/`hash_at`/`slots_for_bits` (executable "
                 "faces of specification predicates, which Verus requires because a "
                 "specification function cannot be called from executable code)."),
        repro_cmd=("python3 -c \"import json;m=json.load(open("
                   "'ci/manifest/WP-SWISSTABLE-VERUS.json'));"
                   "print([f for f in m['functions'] if f in "
                   "('RawTable::num_groups','RawTable::claim_first_free')])\""),
        exit_code=0,
        expected="Every function reachable from a manifest function is a manifest function.",
        actual=("The helpers exist and are called. `claim_first_free` deliberately carries "
                "the find-first-non-full primitive because no concept spec attaches an "
                "obligation to it; the other three exist only because Verus separates "
                "specification and executable faces."),
        workaround="Recorded before #31 runs; decide there whether to absorb or declare them.",
        severity="friction",
        revisit_trigger="chainlink #31 (validate-callsites / gate-r1-g16).",
    ),
    dict(
        id="swisstable-verus-006",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("RawTable::insert finds an existing entry by scanning the slot array "
                 "rather than with the `Group::Match` mask inside the probe loop as "
                 "upstream does. The reason is RawTable.C004's ghost obligation, which "
                 "needs the *uniqueness* of `hash` in the table: only a complete search "
                 "establishes that, and the port does not prove probe coverage (see "
                 "swisstable-verus-004)."),
        repro_cmd=VERIFY,
        exit_code=1,
        expected="insert uses the group mask, as upstream does.",
        actual=("Linear scan, then `claim_first_free` for placement. The returned slot and "
                "the boolean are the same answers upstream gives. `find` still uses the "
                "group mask, so the raw_table_find -> GroupProbe.match_full boundary is "
                "realized where the concept specs put it."),
        workaround="Linear scan for the existing-entry lookup; placement unchanged.",
        severity="scope-cut",
        revisit_trigger="the probe-coverage lemma behind swisstable-verus-004 is written.",
    ),
    dict(
        id="swisstable-verus-008",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("The concept spec writes SwissTable as `insert(&mut self, key: K, "
                 "value: V) -> bool`. The port instantiates `K = V = u64` with the "
                 "identity hash, so a slot's stored hash *is* its key. Two restrictions "
                 "follow and both are real: a key of `NO_HASH` (zero) is refused by "
                 "RawTable, because an erased slot is zero-filled as its 'nothing here' "
                 "marker; and two distinct keys are required to have distinct hashes."),
        repro_cmd=VERIFY,
        exit_code=1,
        expected="Generic `K: Eq + Hash`, `V` arbitrary, with a ghost `Map<K, V>`.",
        actual=("`K = V = u64`. A generic payload with a ghost map is the same shape but "
                "a materially larger proof, and was out of budget for issue #30. The "
                "hash-quality restriction is the one the reference's own `Hash` policy "
                "documentation already imposes."),
        workaround=("Identity hash over u64; documented in the module header. The value "
                    "half is stored per slot and checked differentially in #32."),
        severity="scope-cut",
        revisit_trigger="a generic `K: Eq` payload with a ghost `Map<K, V>` is budgeted.",
    ),
    dict(
        id="swisstable-verus-009",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("CORRECTED after the operator's 2026-10-02 scope ruling. "
                 "SwissTable::insert requires a reusable slot and does not grow; "
                 "growth is a caller obligation via `reserve` -> `RawTable::resize`. "
                 "Upstream insert may grow automatically. An earlier version called "
                 "this a blocker and said an operator decision was still required; "
                 "the operator has now accepted this as a scope cut, not a pending "
                 "decision. Rehash is reachable through reserve, not through insert."),
        repro_cmd=VERIFY,
        exit_code=CRATE_EXIT,
        expected="Upstream insert grows the table when it needs capacity.",
        actual=("The caller must call `reserve`; it grows capacity by one bit. "
                "Its `additional` argument is currently unused, so this is not "
                "upstream's sized-to-fit reserve policy either. Neither omission is "
                "an open Verus proof obligation for issue #30."),
        workaround="Caller calls reserve before insert; documented in swiss_table.rs.",
        severity="scope-cut",
        revisit_trigger=("The operator reopens automatic insert growth or sized-to-fit "
                         "reserve as an in-scope behavior; a counting lemma alone does "
                         "not reverse the scope ruling."),
    ),
    dict(
        id="swisstable-verus-010",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command="nix develop ..#swisstable-verus -c 'cargo verus verify'",
        tool="verus",
        chain="new",
        symptom=("RESOLVED on the live root. The authorized Ligature 1.2.2 "
                 "`scaffold-crate` command created the declared crate's minimal "
                 "Cargo.toml, but it has neither the pinned `vstd` dependency nor "
                 "`[package.metadata.verus] verify = true`, so `cargo build` and "
                 "`cargo test` fail and `cargo verus verify` silently degrades to "
                 "`cargo check`. The source already guards proof-only imports with "
                 "`cfg(verus_only)`. Under the 2026-10-03 operator authorisation "
                 "(exactly one protected-root file, `rust/swisstable-verus-core/"
                 "Cargo.toml`) the live manifest now carries both lines, and all "
                 "three Cargo entry points pass."),
        repro_cmd=("bash analysis/verus/run-cargo.sh ; "
                   "sed -n '1,80p' rust/swisstable-verus-core/Cargo.toml"),
        exit_code=0,
        expected=("A Cargo-Verus manifest with the pinned `vstd` dependency and "
                  "`[package.metadata.verus] verify = true`, then passing Cargo-Verus "
                  "verification/build and test commands."),
        actual=("`cargo build` exits 0; `cargo test` exits 0 with 0 tests; "
                "`cargo verus verify` exits 0 and reports " + CRATE_OUT + " -- the "
                "same counts `analysis/verus/run-verus.sh` captures, through a "
                "different front end. Captured in "
                "analysis/verus/cargo-transcript.txt; the writer reads the counts "
                "out of the Verus transcript, not out of this one."),
        workaround=("None needed. `analysis/verus/run-cargo.sh` captures all three "
                    "so the manifest cannot silently regress; note that a second "
                    "`cargo verus verify` is a cached no-op that prints no "
                    "`verification results` line at all, which is why the runner "
                    "touches `src/lib.rs` first."),
        severity="friction",
        revisit_trigger=("The `vstd` pin is driver-matched: a Verus release bump "
                         "changes the pseudo-version `=0.0.0-2026-05-24-0157` and "
                         "must be updated here in the same change."),
    ),
    dict(
        id="swisstable-verus-011",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("The plan's \"ghost `Map` abstraction invariants\" cannot be a `ghost` "
                 "field in this Verus. A specification-valued field initializer in "
                 "executable code does not compile: `live: Set::<u64>::empty()` and "
                 "`live: Ghost::new(Set::empty())` both fail, the first with \"cannot "
                 "call function `Set::empty` with mode spec\" and the second with "
                 "\"cannot perform operation with mode spec ... kind: Constructor\". A "
                 "`let ghost live = ...` bound first fails with \"cannot access "
                 "spec-mode place in executable context\"."),
        repro_cmd=VERIFY,
        exit_code=1,
        expected="`pub ghost live: Set<u64>` initialised in the constructor's struct literal.",
        actual=("The ghost model is *derived* instead: `RawTable::stored_hashes()` and "
                "`SwissTable::contents()`/`contains_spec()` are `Set::new`/`Map::new` "
                "comprehensions over the slots. No field, no ghost bookkeeping on the "
                "executable side, and the resize obligation becomes a statement about "
                "the arrays themselves."),
        workaround="Derived comprehensions rather than a ghost model field.",
        severity="friction",
        revisit_trigger="Verus gains ghost-field initializers from specification code.",
    ),
    dict(
        id="swisstable-verus-012",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=PROBE,
        tool="verus",
        chain="new",
        symptom=("CORRECTED 2026-10-02, attempt 2. This row previously claimed Verus "
                 "0.2026.05.24 'supplies no axioms at all' for integer `&`/`|`/`^` and "
                 "none for u64 shifts, and used that as a `blocker`. That was wrong, and "
                 "the review reproduced the refutation on the same pinned binary. Every "
                 "fact the row called impossible verifies here: "
                 "`x & m <= m` (`verif/lemmas.rs::lemma_and_below`), "
                 "`x >> 57 < 128` and `x >> 57 == x / 2^57` (`::lemma_shr57`), "
                 "`1u64 << bits >= 1` and `<= 2^62` (`::lemma_pow2_range`), "
                 "`(mask | (1u16 << i)) >> i & 1 == 1` (`::lemma_bit_set`). All are "
                 "`#[verifier::bit_vector]` proof functions in "
                 "rust/swisstable-verus-core/verif/lemmas.rs, all verified. "
                 "rust/swisstable-verus-core/verif/reachability_probe.rs, which the "
                 "first attempt wrote to demonstrate the claim, has been rewritten to "
                 "demonstrate the opposite."),
        repro_cmd=PROBE,
        exit_code=1,
        expected=("Verus's documented model: a `#[verifier::bit_vector]` proof function "
                  "is discharged by Z3's bit-vector theory, and integer mode then treats "
                  "the operators as ordinary spec functions."),
        actual=PROBE_OUT + " (analysis/verus/reachability-probe.txt, captured by "
               "`bash analysis/verus/run-verus.sh`; this row quotes that file rather "
               "than a literal). Eight probe functions verify: `r == hash >> 57`; "
               "`r == hash >> 57` with `r <= 0x7F`; `r <= m` for `r == x & m`; "
               "`r == (1u64 << bits) - 1`; `(r >> i) & 1 == 1` for `r == mask | (1 << i)`; "
               "`r == (1u64 << bits) - 1`. The `errors` in that line are the four "
               "deliberate negative cases documented in `swisstable-verus-016`, each of "
               "which the file states is *expected* not to verify. (An earlier version "
               "of this row also listed `r == 2 * size_of::<usize>()` among the "
               "verifying probes; that was a tautology and the case was replaced -- see "
               "the correction note in -016.) No `assume`, no `admit`, no "
               "`external_body`.",
        workaround=("Nothing to work around: the reference's own operators are used "
                    "throughout the port. `hash_mix.rs` computes `hash >> 57`, "
                    "`probe_seq.rs` wraps with `& capacity_mask`, and `group_probe.rs` "
                    "returns `uint16_t` masks, as the concept specs say. The attempt-1 "
                    "substitutions were reverted."),
        severity="friction",
        revisit_trigger=("n/a -- the finding was wrong and is restated only so the ledger "
                         "does not leave a false blocker standing. See "
                         "swisstable-verus-014 for the correction and "
                         "swisstable-verus-015 for the real, much smaller limitation."),
    ),
    dict(
        id="swisstable-verus-013",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("SCOPE: the current crate verification result, distinct from -014's "
                 "historical process failure and -015's bitwise bridge lemmas. "
                 + ("Proof obligations remain open. " if CRATE_OPEN else
                    "The captured crate verification is now clean. ")
                 + "The captured analysis/verus/verus-transcript.txt reports " + CRATE_OUT
                 + " with exit=" + str(CRATE_EXIT) + ". Primary error locations by "
                 "file: " + CRATE_FILES + "; by function: " + CRATE_FUNCTIONS +
                 " (" + str(CRATE_FUNCTIONS_TOTAL) + " primary locations). "
                 "Historical correction: an earlier revision blamed erase on -017's "
                 "set extensionality; the pre-write specification defect described "
                 "in -020 was fixed. The operator subsequently removed set-level "
                 "extensionality from this issue's proof scope (-023); no current "
                 "failure should be attributed to that discarded postcondition."),
        repro_cmd=VERIFY,
        exit_code=CRATE_EXIT,
        expected="A captured crate run with zero errors and exit 0 on the scoped contracts.",
        actual=CRATE_OUT + "; exit=" + str(CRATE_EXIT) +
               "; primary error locations: " + CRATE_FILES + ".",
        workaround=("No proof shortcut claimed for current errors. Historical "
                    "correction: attempt 1's proposed bounded `capacity_size` constructor "
                    "workaround rested on a false bitwise diagnosis; withdrawn in -012/-014. "
                    "-017/-023's set-level obligation was explicitly scoped out, not proved."),
        severity="blocker" if CRATE_OPEN else "friction",
        revisit_trigger=("Discharge the remaining transcript locations on the scoped "
                         "per-slot/counting contracts; do not reinstate the abandoned "
                         "set-level contract without a new operator ruling." if CRATE_OPEN
                         else "none -- rerun the crate capture if the port changes."),
    ),
    dict(
        id="swisstable-verus-014",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        symptom=("SCOPE: a process failure, not an open obligation. Chainlink #30 "
                 "attempt 1 misdiagnosed Verus as having no integer bitwise or shift "
                 "axioms, on the strength of four hand-written probes whose "
                 "postconditions it then read as impossibilities. It never tested "
                 "`#[verifier::bit_vector]` mode, the documented way to get those "
                 "facts, so it never distinguished 'SMT could not derive this' from "
                 "'Verus has no model for this'. The consequence was three "
                 "unjustified algorithmic substitutions in the port and a `blocker` "
                 "finding whose `revisit_trigger` pointed the operator at a Verus "
                 "upgrade that does not exist. The reviewer caught it on the same "
                 "pinned binary; the correction is recorded in -012 and the probe file "
                 "now demonstrates the true situation. Retained so the ledger carries "
                 "the failure and not only the corrected text."),
        command=PROBE,
        tool="verus",
        chain="new",
        repro_cmd=PROBE,
        exit_code=0,
        expected=("A worker hitting an SMT failure distinguishes an unmodelled operator "
                  "from an under-specified query before recording it as a tool "
                  "limitation."),
        actual=("Not distinguished. The four probes were integer-mode; bit-vector mode "
                "was never tried. Recorded so the ledger carries the failure rather than "
                "only the corrected text."),
        workaround=("Test `#[verifier::bit_vector]` before concluding an operator is "
                    "unmodelled. `verif/reachability_probe.rs` is now the reusable probe "
                    "for exactly that, and it is standalone so its transcript stands "
                    "without the crate."),
        severity="friction",
        revisit_trigger=("any later pilot whose SMT failures touch bitwise or shift "
                         "operators."),
    ),
    dict(
        id="swisstable-verus-015",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        symptom=("SCOPE: the real, small version of the retired -012 -- integer-mode "
                 "specification clauses that mention a bitwise operator. An "
                 "*integer-mode* clause mentioning `&`, `|`, `<<` or `>>` needs the "
                 "corresponding fact stated as a `#[verifier::bit_vector]` proof "
                 "function first: `x & m <= m` is not derivable inline, and neither is "
                 "'setting bit `i` leaves bit `j` alone'. Both are one-line lemmas, but "
                 "each port function that masks an index has to call them, and a missing "
                 "call surfaces as a `postcondition not satisfied` rather than as an "
                 "error about the operator -- which is how this was originally "
                 "misdiagnosed. The nine bridges that discharge them are in "
                 "verif/lemmas.rs and all verify; `verif/reachability_probe.rs` is the "
                 "standalone reproduction."),
        command=VERIFY,
        tool="verus",
        chain="new",
        repro_cmd=VERIFY,
        exit_code=1,
        expected=("Integer mode derives the bounds it needs from the expression's own "
                  "type, with no help."),
        actual=("Nine bridge lemmas in verif/lemmas.rs, each one line: "
                "`lemma_and_below`, `lemma_and_below_usize`, `lemma_shr57`, "
                "`lemma_pow2_range`, `lemma_slots_at_least_group`, "
                "`lemma_slots_roundtrip`, `lemma_bit_set`, "
                "`lemma_or_preserves_other_bit`, `lemma_zero_has_no_bit`. All verify. "
                "This is ordinary boilerplate, not a missing feature."),
        workaround=("State the fact as a bit-vector proof function and call it in a "
                    "`proof { }` block before the expression that needs it."),
        severity="friction",
        revisit_trigger=("a Verus release that discharges these in integer mode directly."),
    ),
    dict(
        id="swisstable-verus-016",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=PROBE,
        tool="verus",
        chain="new",
        symptom=("CORRECTED 2026-10-02, attempt 4. Verus 0.2026.05.24 in this pinned "
                 "build says nothing useful about `usize`. Four negative probes in "
                 "verif/reachability_probe.rs, all four failing, all four said in their "
                 "own doc comment to be expected failures: "
                 "`std::mem::size_of::<usize>() as u64 == 4` (size_of is opaque, so the "
                 "*width* is not a fact this Verus supplies); `usize::MAX as u64 == "
                 "0xFFFF_FFFF` (it is neither 32- nor 64-bit, so no bound can be written "
                 "in terms of it); and both round-trip postconditions for `fn(x: u64) "
                 "-> usize`, in the `u64` view and the `int` view. The third of these "
                 "is the load-bearing one: no postcondition relating a narrowed `usize` "
                 "to its `u64` source is provable, in either view. "
                 "ATTEMPT 3 WAS WRONG ON THE FIRST POINT AND IS RETRACTED HERE: it "
                 "concluded 'usize is 32 bits' from a probe whose postcondition restated "
                 "its own body -- a tautology, true for any width, so it verified and "
                 "proved nothing. Asserted as the literal `4` it fails. No claim about "
                 "the width is made any more. The port's `capacity_bits <= 31` bound is "
                 "now derived only from what is proved: `lemma_slots_roundtrip` shows "
                 "`2^bits - 1 <= 0xFFFF_FFFF`, which is the smallest bound nameable here, "
                 "so the capacity fits whatever `usize` turns out to be."),
        repro_cmd=PROBE,
        exit_code=1,
        expected=("`size_of::<usize>()` and `usize::MAX` are nameable, and a "
                  "range-checked narrowing cast relates to its source, so an "
                  "exact-value postcondition can be written across the boundary."),
        actual=PROBE_OUT + " -- see analysis/verus/reachability-probe.txt, where the "
               "four failures are exactly the ones the file itself predicts.",
        workaround=("Postconditions that cross the boundary are stated over the `int` "
                    "view; the exact masked value is proved in `advance`'s postcondition "
                    "and in `well_formed`, both over `u64`, and the bound ProbeSeq.C002 "
                    "actually asks for survives unchanged. Capacity is capped at "
                    "`2^31 - 1` slots, which for this subset is a range no test corpus "
                    "reaches."),
        severity="friction",
        revisit_trigger=("a Verus release whose `usize` casts and `size_of` are modelled; "
                         "the `global size_of usize` setting that would do it exists in "
                         "the binary but this build rejects every syntax offered on the "
                         "command line and in a crate header."),
    ),
    dict(
        id="swisstable-verus-017",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("HISTORICAL, NOW A SCOPE CUT (operator ruling 2026-10-02): the "
                 "former derived-model set-extensionality obligations are not part of "
                 "the accepted #30 proof contract. `stored_hashes()` remains a "
                 "derived `Set::new` comprehension, but #30 proves the operator-approved "
                 "per-slot and counting properties instead. No `ext_equal` or other "
                 "set-equality proof is claimed. The tracked-Map representation is a "
                 "separate proposed probe, sequenced after #30, not a fifth extensionality "
                 "variant and not an authorization to change the #30 contracts."),
        repro_cmd=VERIFY,
        exit_code=1,
        expected=("The old derived-Set equality is either recorded as outside #30's "
                  "accepted contract or addressed by a separately reviewed model "
                  "representation."),
        actual=("No set equality is claimed by #30; its per-slot/counting contracts "
                "verify. The tracked-Map proposal is a distinct representation probe in "
                "#120, sequenced after #30. The failed `Set::new` extensionality attempts "
                "remain historical evidence, not a reason to add another extensionality "
                "variant."),
        workaround=("None claimed. Two attempts at the restructuring `-017`'s own "
                    "revisit_trigger named have now been made and both are recorded "
                    "here. (1) The pointwise membership restatement of C004 -- "
                    "`forall k, final.contains(k) <==> old.contains(k) || k == hash` "
                    "-- was implemented and then withdrawn: the specification is the "
                    "right one and `lemma_stored_in` sees through it, but the two "
                    "quantifiers propagate to every caller, and `SwissTable::insert` "
                    "went 20 -> 22 locations carrying them, which is a net regression. "
                    "(2) A proof block discharging that restatement inline in "
                    "`insert` was implemented and then withdrawn: it does not close, and "
                    "took insert from 21 to 27 locations while failing. Neither was "
                    "hidden -- both are this row."),
        severity="scope-cut",
        revisit_trigger=("Evaluate only through the separate tracked-Map representation "
                         "probe #120. Do not restart the derived-Set extensionality variants; "
                         "a contract change requires a separate operator decision."),
    ),
    dict(
        id="swisstable-verus-018",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=PROBE,
        tool="verus",
        chain="new",
        symptom=("`usize::MAX` is unnameable, so any *precondition* written against it "
                 "is unsatisfiable and can never be discharged. TWO sites did exactly "
                 "that and are now restated against the literal `0x7FFF_FFFF`: "
                 "`ControlBytes::new` (src/control_bytes.rs:117, was "
                 "`capacity + 1 <= usize::MAX - PAD_BYTES`), `SwissTable::reserve` "
                 "(src/swiss_table.rs:263, was `additional <= usize::MAX - capacity`). "
                 "`GroupProbe::load` was NOT restated; the workaround field says so. "
                 "The consequence was that "
                 "`RawTable::new` (raw_table.rs:138) and `RawTable::resize` "
                 "(raw_table.rs:598) failed with 'precondition not satisfied' on that "
                 "clause -- and `RawTable::new` is the entry point for every mutator of "
                 "the subset, so nothing downstream of it could verify."),
        repro_cmd=("grep -n 'usize::MAX' rust/swisstable-verus-core/src/*.rs ; "
                   + PROBE),
        exit_code=1,
        expected=("`usize::MAX` is a nameable constant, so an overflow guard written "
                  "against it is satisfiable."),
        actual=PROBE_OUT + " -- `probe_usize_max_is_unnameable` fails, and is the "
               "evidence; see analysis/verus/reachability-probe.txt.",
        workaround=("Every restated `requires` clause now uses the literal `0x7FFF_FFFF`. "
                    "CORRECTION: an earlier revision claimed that is 'the same figure "
                    "`slots_for_bits` already guarantees'. It was not -- "
                    "`lemma_slots_roundtrip` ensured only `0xFFFF_FFFF` -- so the failure "
                    "moved clauses rather than going away. Fixed by tightening that lemma to "
                    "`0x7FFF_FFFF`, which discharges raw_table.rs:138 outright because "
                    "`RawTable::new` already requires `capacity_bits <= 31` and "
                    "`2^31 - 1 == 0x7FFF_FFFF`, which discharges raw_table.rs:138 and with it the whole of `RawTable::new` and `SwissTable::new`. ONE site still needs `usize::MAX`: "
                    "`GroupProbe::load`'s loop invariant, where proving `base + i` cannot "
                    "wrap before it is used as a `Vec` index requires naming the type "
                    "maximum. The split form (`base <= len`, `GROUP_WIDTH <= len - base`) was "
                    "implemented and does not discharge the index check, so it was reverted; "
                    "the site is documented in place rather than left looking clean."),
        severity=("friction" if False else "friction"),
        revisit_trigger=("`GroupProbe::load`'s index check only: it still needs the type "
                         "maximum, which `swisstable-verus-016` shows this Verus will not "
                         "name. The `requires` clauses are discharged."),
    ),
    dict(
        id="swisstable-verus-019",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("`RawTable::resize` carried `self.model()` as a loop invariant, and it "
                 "is FALSE there, not merely unproved. `clear_dead()` runs before the "
                 "move loop and turns every full byte into a tombstone while "
                 "`self.hashes` still holds that slot's key, so `slot_model`'s clause "
                 "`!is_full_spec(i) ==> slot_hash(i) == NO_HASH` does not hold for the "
                 "reclaimed slots. A second false classification treated a reclaimed "
                 "slot as full when it was actually dead; the transient predicate must "
                 "state `is_dead_spec(i) <==> before[i] <= 0x7F`. These are false facts, "
                 "not solver gaps; the current reclaim-window model states the actual "
                 "intermediate state."),
        repro_cmd=("sed -n '/pub open spec fn reclaiming_model/,/^    }/p' "
                   "rust/swisstable-verus-core/src/raw_table.rs"),
        exit_code=CRATE_EXIT,
        expected="The corrected reclaim-window invariant and the scoped resize preservation postconditions verify.",
        actual=("The crate transcript reports " + CRATE_OUT + "; exit=" + str(CRATE_EXIT)
                + ". The final proof explicitly connects the source-indexed `dest` and "
                "destination-indexed `owner` records to both existential survival "
                "postconditions. The crate has zero primary error locations."),
        workaround=("Use `reclaiming_model(before, before_hashes)` for the transient "
                    "metadata/payload state, retain pairwise-distinctness and placement "
                    "records, and prove the public witnesses before moving the new table "
                    "into `self`."),
        severity="friction",
        revisit_trigger="none for the current scoped contract; rerun after resize changes.",
    ),
    dict(
        id="swisstable-verus-020",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("The erase path was specified so that `RawTable::erase` cannot be "
                 "called at all. `SwissTable::erase` branched on `capacity() <= "
                 "GROUP_WIDTH` and pre-wrote the tombstone via `ctrl_mut().set_dead` "
                 "before handing the slot to `RawTable::erase`, whose `model()` "
                 "precondition then fails: `kDeleted` is `0xFE > 0x7F`, so "
                 "`is_full_spec(slot)` becomes false while `hashes[slot]` still holds "
                 "the key, falsifying `slot_model`'s `!is_full_spec(i) ==> slot_hash(i) "
                 "== NO_HASH`. The second precondition, "
                 "`stored_hashes().contains(slot_hash(slot))`, is false for the same "
                 "reason: `stored_hashes()` filters on `is_full_spec`. The branch was "
                 "also dead -- `capacity_bits >= 5` gives `capacity >= 31 > GROUP_WIDTH "
                 "== 16`, so the tombstone was always written. A comment on "
                 "`RawTable::erase` asserted the opposite ('a slot that is already "
                 "tombstoned still has its live key in `hashes`, so the derived model "
                 "stays right either way'), which is false for the derived model. "
                 "Separately, `ctrl_mut` handed out `&mut ControlBytes` with no "
                 "`well_formed` postcondition, so Verus could not carry the array "
                 "invariant into `set_dead` at all, making the manifest's declared "
                 "`swiss_table_erase__to__control_bytes_set_dead` boundary "
                 "undischargeable as drafted."),
        repro_cmd=VERIFY,
        exit_code=1,
        expected=("Either upstream's `Erase` shape -- the container hands over a full "
                  "slot and `RawTable::erase` chooses `kEmpty` vs `kDeleted` itself, "
                  "which is what its `if self.ctrl.is_full(slot)` guard already does -- "
                  "or a tombstoning variant whose preconditions admit a not-full slot."),
        actual=("The first. `SwissTable::erase` now calls `RawTable::erase` directly; "
                "the dead branch and the pre-write are gone, `ctrl_mut` is deleted "
                "(it had no other caller and no sound postcondition), and the false "
                "comment on `RawTable::erase` is replaced by the correct one. erase's "
                "error count went 11 -> 4 and `swiss_table.rs` 27 -> 20."),
        workaround=("None needed beyond the above. What remains in erase is the "
                    "`stored_hashes().remove(...)` postcondition -- the extensionality, "
                    "recorded separately as -017 -- plus three SwissTable-level clauses."),
        severity="friction",
        revisit_trigger=("the manifest's `swiss_table_erase__to__control_bytes_set_dead` "
                         "boundary edge is now unrealised, because the container no "
                         "longer calls `ControlBytes::set_dead`. The reference's `Erase` "
                         "does not make the container do that either, so the boundary "
                         "looks mis-stated in the Stage 7 manifest rather than in the "
                         "port; see `swisstable-spec-008`."),
    ),
    dict(
        id="swisstable-verus-021",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=("sed -n '868,885p' upstream/abseil-cpp/absl/container/internal/"
                 "raw_hash_set.cc ; sed -n '708,712p' upstream/abseil-cpp/absl/container/"
                 "internal/raw_hash_set.cc"),
        tool="verus",
        chain="new",
        symptom=("Historical divergence: an earlier RawTable::erase always wrote a "
                 "tombstone, and an intermediate port rule used a dead capacity branch. "
                 "The current implementation follows upstream's `WasNeverFull` "
                 "predicate: it computes the empty-window counts from control bytes and "
                 "writes `kEmpty` exactly when the predicate holds, otherwise "
                 "`kDeleted`. Inspection of the pinned C++ shows that `growth_info` is "
                 "updated after this choice; it is not an input to `WasNeverFull`. The "
                 "broader growth-left accounting remains outside the port."),
        repro_cmd=("sed -n '708,723p' upstream/abseil-cpp/absl/container/internal/"
                   "raw_hash_set.cc ; sed -n '286,320p' rust/swisstable-verus-core/"
                   "src/control_bytes.rs ; sed -n '882,968p' rust/swisstable-verus-core/"
                   "src/raw_table.rs ; bash analysis/verus/run-verus.sh"),
        exit_code=0,
        expected=("`kEmpty` exactly when `WasNeverFull(c, index)`, i.e. the same "
                  "post-erase control-byte state as abseil."),
        actual=("The current `RawTable::erase` calls the verified control-byte predicate "
                "and selects `set_empty`/`set_dead` accordingly; the crate transcript "
                "reports " + CRATE_OUT + "."),
        workaround=("The erase-byte divergence is fixed. Missing growth-left scheduling "
                    "and deletion-budget metadata remain a separate behavior scope cut "
                    "documented with swisstable-verus-009."),
        severity="friction",
        revisit_trigger=("Reopen only if #32 finds a remaining control-byte mismatch or "
                         "the operator brings full growth-left accounting into scope."),
    ),
    dict(
        id="swisstable-spec-008",
        pilot="swisstable-verus",
        stage="stage0-3-draft-review",
        command=("cat rust/swisstable-verus-core/specs/_boundaries/"
                 "swiss_table_erase__to__control_bytes_set_dead.json.draft"),
        tool="ligature",
        chain="new",
        symptom=("The staged boundary draft "
                 "`rust/swisstable-verus-core/specs/_boundaries/"
                 "swiss_table_erase__to__control_bytes_set_dead.json.draft` asserts that "
                 "the container writes the tombstone itself before delegating the slot to "
                 "the table. Upstream makes no such call: `EraseMetaOnlySmall` "
                 "(raw_hash_set.cc:856) and `EraseMetaOnlyLarge` (:868), called from "
                 "raw_hash_set.h:3490/:3493, both write the control byte themselves. The "
                 "edge drove the port into a specification that is unprovable for a "
                 "derived ghost model, because writing `kDeleted` first makes the slot "
                 "not-full while its key is still stored -- see `swisstable-verus-020`. "
                 "CORRECTION: an earlier revision of this row put the defect in the Stage "
                 "7 manifest, `ci/manifest/WP-SWISSTABLE-VERUS.json`. That is wrong -- the "
                 "manifest has no `boundaries` key at all, and grepping it for the edge "
                 "returns nothing. The declaring artefact is the Stage 3 boundary draft "
                 "above. An earlier revision's `repro_cmd` also cited "
                 "`raw_hash_set.cc L1592-L1620` for a function named `Erase` that does "
                 "not exist; those lines are `InsertSlot`'s probed-item buffer and "
                 "`GrowToNextCapacity`."),
        repro_cmd=("cat rust/swisstable-verus-core/specs/_boundaries/"
                   "swiss_table_erase__to__control_bytes_set_dead.json.draft ; "
                   "python3 -c \"import json;print(sorted(json.load(open("
                   "'ci/manifest/WP-SWISSTABLE-VERUS.json')).keys()))\" ; "
                   "sed -n '868,880p' upstream/abseil-cpp/absl/container/internal/"
                   "raw_hash_set.cc"),
        exit_code=0,
        expected="A boundary edge should correspond to a call the reference makes.",
        actual=("No such call exists upstream, and the edge is declared in a Stage 3 "
                "boundary draft, not in the Stage 7 manifest. Both are protected roots, "
                "so it is reported rather than edited."),
        workaround=("The port follows the reference: `RawTable::erase` writes the byte, "
                    "so the staged edge is unrealised. #31's validate-callsites may "
                    "report it as a missing call edge."),
        severity="blocker",
        revisit_trigger=("the operator's Stage 4 batch: drop the edge or re-draft it to "
                         "`swiss_table_erase__to__raw_table_erase` (which is already "
                         "staged), alongside swisstable-spec-001/-002/-003."),
    ),
    dict(
        id="swisstable-verus-022",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command="sed -n '/pub fn insert/,/^    }/p' rust/swisstable-verus-core/src/raw_table.rs",
        tool="verus",
        chain="new",
        symptom=("`RawTable::insert` verified with its body writes missing. Attempt 10's "
                 "revert spliced from `let ghost before_hashes` to `(slot, true)`, which "
                 "removed `self.ctrl.set_full(slot, mix.h2())`, "
                 "`self.hashes[slot] = hash` and `self.len_ = self.len_ + 1` along with "
                 "the proof block they surrounded. The function still returned `(slot, "
                 "true)` and still satisfied its postconditions vacuously, so attempts "
                 "10 and 11 reported `insert 18` and 54 locations -- a number produced by "
                 "a table that inserted nothing. With the writes restored the same "
                 "transcript reads `insert 19` and 55 locations. The two attempts' "
                 "apparent improvement was an artefact."),
        repro_cmd=("grep -n 'self.ctrl.set_full(slot' rust/swisstable-verus-core/src/"
                   "raw_table.rs ; python3 analysis/verus/errors-by-fn.py"),
        exit_code=1,
        expected=("A verifying body. Verus accepted a mutator that performed no mutation "
                  "because every postcondition it checked was either about `slot` or "
                  "vacuously true."),
        actual=("Restored in attempt 12. The three writes are back at raw_table.rs:535-537 "
                "and the honest count is 55 locations, `insert` 19."),
        workaround=("None. Recorded because the earlier per-attempt numbers in this "
                    "workspace's comments and ledger rows for attempts 10-11 are wrong "
                    "by 1 location and 1 error for this reason, and an operator reading "
                    "them back should know that."),
        severity="blocker",
        revisit_trigger=("none -- it is fixed. Kept so the attempt 10/11 numbers are "
                         "explained rather than left to look like progress."),
    ),
    dict(
        id="swisstable-verus-023",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("`ext_equal` over a derived `Set::new` comprehension does not close, and "
                 "the three workarounds for it have now all been tried and all measured. "
                 "The ghost model has to be derived (`stored_hashes()` is `Set::new` over "
                 "an existential of slots) because a specification-valued field cannot be "
                 "initialised from executable code (`swisstable-verus-011`), so every "
                 "obligation over it is a set extensionality. Attempted: (a) "
                 "`assert_sets_equal!`, with `vstd::set::group_set_axioms` broadcast; (b) an "
                 "explicit `#[trigger]` on the existential; (c) an inline proof block in "
                 "`insert` using the verified `lemma_stored_in`; (d) restating C004 "
                 "pointwise over `stored_in` so no `Set` appears in the postcondition at "
                 "all -- the cleanest form, and the one this row is filed about. (d) is "
                 "expressible but still does not close, and it costs the caller: "
                 "`SwissTable::insert` went 20 -> 22 locations because its C002 "
                 "`r == !old.contains_spec(key)` and `final.contains_spec(key)` now have to "
                 "be transferred through the pointwise clause, and `RawTable::insert` "
                 "went 19 -> 21. Total 55 -> 57. All four were reverted; the ledger and "
                 "README report the better 55."),
        repro_cmd=("sed -n '/pub fn insert(&mut self, hash/,/^    }/p' "
                   "rust/swisstable-verus-core/src/raw_table.rs ; "
                   "bash analysis/verus/run-verus.sh ; "
                   "python3 analysis/verus/errors-by-fn.py"),
        exit_code=1,
        expected=("Either `A =~= B` over two `Set::new` comprehensions closes once the "
                  "membership is visible, or the pointwise restatement discharges without "
                  "paying a caller-side cost."),
        actual=("Neither. Membership IS visible -- `lemma_stored_in` proves "
                "`stored_hashes().contains(k) <==> stored_in(k)` and verifies -- but "
                "discharging the two-directional extensionality from it does not follow, "
                "and the pointwise form is expressible yet still unclosed."),
        workaround=("Ruled out of scope by the operator on 2026-10-02, not retried: "
                    "the contracts are per-slot frame and counting contracts, and the "
                    "set-level obligations are recorded here as a limitation rather "
                    "than proved. Four approaches measured, none kept."),
        severity="scope-cut",
        revisit_trigger=("RULED 2026-10-02: the operator accepted this as a recorded "
                         "pilot limitation and re-scoped #30 to per-slot frame and "
                         "counting contracts, with set-level obligations explicitly out "
                         "of scope. Do not start a fifth variant. The separate "
                         "tracked-Map representation probe #120 may test a different "
                         "ghost model; contract changes remain a separate operator "
                         "decision."),
    ),
    dict(
        id="swisstable-verus-024",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("The per-file error split was reported wrong, and the claim that the "
                 "supplier modules are error-free rested on evidence that could not "
                 "distinguish a complete diagnostic set from a truncated one. Two "
                 "defects, both mine. (1) For fourteen attempts the README and the "
                 "issue comments printed `55  src/raw_table.rs` / `20  src/"
                 "swiss_table.rs`. 55 is the TOTAL primary error locations, not "
                 "raw_table.rs's share; `err-summary.py` prints 55 as the total and "
                 "splits it 35/20. raw_table.rs was overstated by 20. (2) Every "
                 "transcript was captured with `--multiple-errors 20` and terminates "
                 "with `error: aborting due to 55 previous errors`, and `--multiple-"
                 "errors` is a query budget rather than a documented error cap, so a "
                 "reader could not tell whether the 55 were all of the errors."),
        repro_cmd=("VERUS_ERROR_BUDGET=20 bash analysis/verus/run-verus.sh ; "
                   "VERUS_ERROR_BUDGET=200 bash analysis/verus/run-verus.sh ; "
                   "python3 analysis/verus/err-summary.py"),
        exit_code=1,
        expected=("the two budgets to agree, so the emitted set is complete; and the "
                  "per-file line to carry the file's own count."),
        actual=("They agree exactly. At 200 the transcript reads the same 98 verified / "
                "16 errors, the same 55 primary locations, the same 35 src/raw_table.rs "
                "/ 20 src/swiss_table.rs split, the same seven-function breakdown "
                "(insert 19, find 12, clear 7, resize 7, contains 5, erase 4, new_seq "
                "1), and the probe the same 10 verified / 4 errors. The abort at 55 is "
                "Verus's own, not the budget's. So the counts were always complete and "
                "the suppliers were always error-free -- but the evidence did not show "
                "it, which is the part that mattered. HISTORICAL: those are attempt "
                "15's numbers. The current capture reads " + CRATE_OUT + ", and the "
                "probe's verified count has since risen from 10 to " + str(PROBE_OK) +
                " with its four deliberate negative errors unchanged."),
        workaround=("`run-verus.sh` now captures at `--multiple-errors 200` "
                    "(`VERUS_ERROR_BUDGET` overrides), and the README reports 35/20 with "
                    "the total on its own line. The ledger writer never hardcoded the "
                    "split -- it derives every count from the transcript at write time "
                    "-- so no findings row carried the wrong number."),
        severity="friction",
        revisit_trigger=("none -- measured and corrected in attempt 15. Kept because "
                         "fourteen posted comments carry the misattributed `55  src/"
                         "raw_table.rs` line and should be readable with the correction "
                         "in view."),
    ),
dict(
        id="swisstable-verus-025",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command="grep -n 'lemma_usize_max_is_one_of_two' -A 6 rust/swisstable-verus-core/verif/lemmas.rs",
        tool="verus",
        chain="new",
        symptom=("Verus 0.2026.05.24 will not name `usize::MAX`. The probe function "
                 "`lemma_usize_max_is_one_of_two() -> (r: u64)` with "
                 "`ensures r == 0xFFFF_FFFFu64 || r == 0xFFFF_FFFF_FFFF_FFFFu64` and "
                 "body `usize::MAX as u64` verifies, so the maximum is nameable only as "
                 "a disjunction over candidate widths. Nothing discharges from it: a "
                 "`requires` clause written as `x + 1 <= usize::MAX` is unsatisfiable, "
                 "which is why every upper bound in the port is a literal."),
        repro_cmd=("sed -n '/lemma_usize_max_is_one_of_two/,/^}/p' "
                   "rust/swisstable-verus-core/verif/lemmas.rs ; "
                   "bash analysis/verus/run-verus.sh"),
        exit_code=CRATE_EXIT,
        expected="`usize::MAX` usable as an arithmetic bound.",
        actual=("The disjunction verifies; the arithmetic use does not. Every bound in "
                "the port is the literal `0x7FFF_FFFF`, which is already implied by the "
                "pinned `capacity_bits <= 31`, so nothing is given up -- but it is a "
                "named figure the reader has to be told about rather than a type "
                "maximum. Crate capture: " + CRATE_OUT + "."),
        workaround=("State every upper bound as the literal `0x7FFF_FFFF`; "
                    "`ControlBytes::well_formed` carries it as an invariant so it is "
                    "available everywhere the capacity is used."),
        severity="friction",
        revisit_trigger="A Verus release that makes `usize::MAX` usable in arithmetic.",
    ),
    dict(
        id="swisstable-verus-028",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=("sed -n '/pub open spec fn is_empty_or_deleted_in/,/^}/p' "
                 "rust/swisstable-verus-core/src/control_bytes.rs"),
        tool="verus",
        chain="new",
        symptom=("Verus leaves `i as usize` opaque in BOTH directions, so a "
                 "`usize`-quantified invariant is not a usable premise for an "
                 "`int`-quantified one, and the counting lemmas cannot produce the "
                 "`usize` form of their own conclusions. An earlier revision of the two "
                 "linear scans in `claim_first_free` therefore carried a duplicated pair "
                 "of lemmas whose only job was to cross the cast."),
        repro_cmd=("sed -n '/pub(crate) fn claim_first_free/,/^}/p' "
                   "rust/swisstable-verus-core/src/raw_table.rs"),
        exit_code=CRATE_EXIT,
        expected="One index vocabulary usable in both the executable code and the specs.",
        actual=("State the scans' invariants in the `int` form and cast once, on the "
                "bound, not on the predicate; the duplicated cross-the-cast lemmas are "
                "gone. Crate capture: " + CRATE_OUT + "."),
        workaround=("`int`-quantified loop invariants throughout `claim_first_free`, "
                    "with the scan cursor cast once."),
        severity="friction",
        revisit_trigger="A Verus release that makes `int as usize` an equivalence.",
    ),
    dict(
        id="swisstable-verus-029",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=("sed -n '/pub proof fn lemma_scan_contradiction/,/^}/p' "
                 "rust/swisstable-verus-core/verif/lemmas.rs"),
        tool="verus",
        chain="new",
        symptom=("Verus 0.2026.05.24 does not let `assert forall ... by { }` assume "
                 "the antecedent of its outermost implication; it warns about this and "
                 "links its own upstream issue, \"Don't always make assert forall "
                 "assume the antecedent\". The contradiction `claim_first_free` needs "
                 "-- two linear scans found nothing, so nothing is free -- is therefore "
                 "unprovable in an assertion at the call site, because inside `by { }` "
                 "the scan invariants' premises are not available as antecedents."),
        repro_cmd=("grep -c 'assert forall' rust/swisstable-verus-core/src/*.rs ; "
                   "bash analysis/verus/run-verus.sh"),
        exit_code=CRATE_EXIT,
        expected=("The contradiction provable in an `assert forall ... by { }` at the "
                  "call site."),
        actual=("It is provable as a `proof fn` whose `requires` restates the premises, "
                "because a proof function's own recursive body is not under that "
                "restriction. An earlier revision of the lemma left the existential out "
                "of its `requires`, which made both the lemma and its `!exists` "
                "postcondition vacuous -- the `if` body was unreachable from the "
                "premises alone -- and `claim_first_free` was then unable to claim it "
                "always finds a slot. Crate capture: " + CRATE_OUT + "."),
        workaround=("`lemma_scan_contradiction` carries the existential in its "
                    "`requires`, and its postcondition is `false` rather than `!exists`, "
                    "so `claim_first_free` gets the completeness half it needs."),
        severity="friction",
        revisit_trigger="A Verus release that assumes the antecedent of `assert forall`.",
    ),
    dict(
        id="swisstable-verus-030",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=("sed -n '/pub open spec fn was_never_full_in/,/^}/p' "
                 "rust/swisstable-verus-core/src/control_bytes.rs"),
        tool="verus",
        chain="new",
        symptom=("`RawTable::erase` chooses `kEmpty` vs `kDeleted` from upstream's "
                 "`WasNeverFull` (raw_hash_set.cc L708-L724), which is `fwd + bwd < "
                 "kWidth` where `fwd`/`bwd` are the two `MaskEmpty` window counts capped "
                 "at `kWidth` (hashtable_control_bytes.h L100-L104). An earlier revision "
                 "transcribed the test as `fwd < 16 && bwd < 16 && fwd <= bwd` and "
                 "carried the derivation error as prose (`fwd + (15 - bwd) < 16`). Both "
                 "readings are wrong in opposite directions on reachable states: with 16 "
                 "consecutive full slots around the index (`fwd == 1`, `bwd == 15`) "
                 "upstream sums to `kWidth` and writes `kDeleted` while `1 <= 15` says "
                 "`kEmpty`; with `fwd == 3`, `bwd == 1` upstream writes `kEmpty` while "
                 "`3 <= 1` says `kDeleted`."),
        repro_cmd=("sed -n '/pub proof fn lemma_was_never_full_boundary_cases/,/^}/p' "
                   "rust/swisstable-verus-core/verif/reachability_probe.rs ; "
                   "sed -n '708,724p' upstream/abseil-cpp/absl/container/internal/"
                   "raw_hash_set.cc"),
        exit_code=PROBE_EXIT,
        expected="`fwd + bwd < kWidth`, matching raw_hash_set.cc L708-L724.",
        actual=("`was_never_full_in` states the sum, and "
                "`lemma_was_never_full_boundary_cases` in the standalone probe pins both "
                "reachable disagreements so the transcription cannot come back. Neither "
                "state needs a sentinel or any byte the port cannot produce, so the "
                "divergence was observable through `count_empty`, not a corner. Crate "
                "capture: " + CRATE_OUT + "; probe: " + PROBE_OUT + "."),
        workaround="None: the reference's rule is implemented and both boundary cases "
                   "are verified in the probe.",
        severity="friction",
        revisit_trigger="#32's differential oracle finds a remaining control-byte "
                        "mismatch after erase.",
    ),
    dict(
        id="swisstable-verus-031",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=("sed -n '/pub open spec fn reclaiming_model/,/^    }/p' "
                 "rust/swisstable-verus-core/src/raw_table.rs"),
        tool="verus",
        chain="new",
        symptom=("Two defects in `RawTable::resize`, both mine. (1) `reclaiming_model`'s "
                 "first quantified clause read `is_full_spec(i) <==> before[i] <= 0x7F`, "
                 "justified in a comment by \"`clear_dead` never promotes a free byte\". "
                 "That is false, and false in the direction that matters: `clear_dead` "
                 "writes `kDeleted` (0xFE) over every full byte, so after the reclaim NO "
                 "slot is full while `before[i] <= 0x7F` holds for exactly the live "
                 "ones. The clause says `is_full <==> is_live` where it must say "
                 "`is_dead <==> is_live`; all three clauses in that predicate phrased "
                 "over `is_full_spec` in the reclaim window had the same defect. This is "
                 "the third instance of the same class after -019 (a false `resize` "
                 "invariant) and -020 (a false `erase` comment). (2) The move loop "
                 "carried the two survival directions as `exists`-inside-`forall` loop "
                 "invariants -- five clauses of that shape, plus a distinctness clause "
                 "and an H2-tag clause -- and Verus reported `note: while loop: Resource "
                 "limit (rlimit) exceeded` on the loop itself; nine of its invariants did "
                 "not close and 15 primary error locations remained."),
        repro_cmd=("python3 analysis/verus/err-summary.py ; "
                   "grep -n 'dest\\[i\\]\\|owner\\[a\\]' rust/swisstable-verus-core/"
                   "src/raw_table.rs"),
        exit_code=CRATE_EXIT,
        expected=("The reclaim window stated over `is_dead_spec`, and a move loop whose "
                  "invariants the solver can carry."),
        actual=("(1) is fixed in place, with the reasoning recorded at the predicate. "
                "(2) The loop records the placement in two ghost `Seq`s -- `dest` "
                "indexed by the source slot, `owner` indexed by the destination slot -- "
                "which turns both survival directions into pointwise facts about a "
                "single index, and the transfer reuses the already-verified `insert` "
                "instead of re-deriving find-or-open. The rlimit note is gone and "
                "the crate reports " + CRATE_OUT + " with zero primary error "
                "locations. "
                "Behaviour is unchanged: the live keys live again at probe-chosen "
                "positions, and the contract is the same two survival directions. "
                "The verified count is " + str(CRATE_OK) + ": one lower than the "
                "150 immediately before this pass, because the counting lemma that "
                "routed the reclaim's element count through two recursive prefix "
                "counts (`lemma_dead_count_eq_full_count` and its `dead_iff_full` "
                "spec function) lost its last caller and was deleted -- the new "
                "counting invariant counts full bytes of the *pre-reclaim* "
                "snapshot, where they are still countable, so the transfer is not "
                "needed."),
        workaround=("Recorded rather than worked around: (1) is a correction, (2) is a "
                    "restructuring that kept the same contract."),
        severity="friction",
        revisit_trigger=("A future contract that needs a genuinely existential per-slot "
                         "statement will hit the rlimit again; put the witness in a "
                         "ghost `Seq` rather than in an `exists`."),
    ),
    dict(
        id="swisstable-spec-001",
        pilot="swisstable-verus",
        stage="stage0-3-draft-review",
        command="cat rust/swisstable-verus-core/specs/control_bytes.json.draft (constraint C006)",
        tool="ligature",
        chain="new",
        symptom=("The staged ControlBytes.C006 has three clauses: full bytes become "
                 "deleted, empty bytes stay empty, and \"never turns a deleted byte into "
                 "an empty one\". The third clause contradicts both the reference "
                 "(raw_hash_set.cc L434-L447 `ConvertDeletedToEmptyAndFullToDeleted`, one "
                 "saturating subtract that maps kDeleted to kEmpty; asserted again in "
                 "raw_hash_set_test.cc L960) and the concept's own command text for "
                 "`clear_dead`, \"reclaim every deleted slot as empty and every full slot "
                 "as deleted\". It is also load-bearing in the wrong direction: "
                 "RawTable::resize's whole design is that after the reclaim, `kDeleted` "
                 "marks a live element and `kEmpty` marks a reusable slot."),
        repro_cmd=("sed -n '434,447p' upstream/abseil-cpp/absl/container/internal/"
                   "raw_hash_set.cc"),
        exit_code=0,
        expected="C006's clauses should match the reference's byte-for-byte rewrite.",
        actual=("Clause 3 denies a conversion the reference performs and that resize "
                "depends on. The port implements the reference and documents the "
                "divergence at ControlBytes::clear_dead."),
        workaround="Reference behaviour implemented; the staged clause is recorded here "
                   "rather than silently honoured.",
        severity="blocker",
        revisit_trigger=("the operator's Stage 4 batch: either C006's third clause is "
                         "dropped or the concept is re-drafted before approval, because "
                         "the drafts are still staged .draft and unapproved."),
    ),
    dict(
        id="swisstable-spec-002",
        pilot="swisstable-verus",
        stage="stage0-3-draft-review",
        command=("cat rust/swisstable-verus-core/specs/group_probe.json.draft "
                 "(constraints C001, C004)"),
        tool="ligature",
        chain="new",
        symptom=("GroupProbe.C001 and C004 state the group window bound as "
                 "`base + 16 <= capacity`, and C004 as \"a group never covers the "
                 "sentinel byte at index capacity\". That is unreachable for the probe "
                 "offsets the reference produces: `probe_seq` wraps inside `[0, "
                 "capacity]` and the sentinel sits at index `capacity`, so offsets in "
                 "`[capacity - 15, capacity]` load windows containing the sentinel and "
                 "the padding -- which is exactly what makes the last group readable and "
                 "the sentinel a usable stop condition. It is also inconsistent with "
                 "RawTable.C001 (`capacity + 1 == 1 << capacity_bits`), which makes "
                 "capacity odd and therefore never a multiple of 16, so no group-aligned "
                 "base can satisfy `base + 16 <= capacity` for the last group of any "
                 "table."),
        repro_cmd=("sed -n '1770,1810p' upstream/abseil-cpp/absl/container/internal/"
                   "raw_hash_set.h"),
        exit_code=0,
        expected="The window bound should be the reference's `base + 16 <= byte_len()`.",
        actual=("The port implements `base + GROUP_WIDTH <= ctrl.bytes@.len()`, which "
                "holds for every offset in `[0, capacity]` because "
                "`byte_len() == capacity + 1 + PAD_BYTES`. C004's sentinel claim is not "
                "restated, because it is false of the reference."),
        workaround="Byte-array bound implemented; documented at GroupProbe::load.",
        severity="blocker",
        revisit_trigger=("the operator's Stage 4 batch, together with swisstable-spec-001 "
                         "and swisstable-spec-003: the probing cluster's constraint set "
                         "needs re-drafting before it can be approved as written."),
    ),
    dict(
        id="swisstable-spec-003",
        pilot="swisstable-verus",
        stage="stage0-3-draft-review",
        command=("cat rust/swisstable-verus-core/specs/probe_seq.json.draft "
                 "(constraint C001)"),
        tool="ligature",
        chain="new",
        symptom=("ProbeSeq.C001 reads `capacity_mask + 1 == (1 << capacity_bits) && "
                 "capacity_bits >= 4`. It has no upper bound on `capacity_bits`, so "
                 "`offset_ + index_` can overflow the state words and an offset need not "
                 "fit in a `usize`. The reference has no such bound because its `size_t` "
                 "arithmetic is unchecked and it relies on allocation failing first."),
        repro_cmd=("grep -n 'capacity_bits <= 62' rust/swisstable-verus-core/src/"
                   "probe_seq.rs"),
        exit_code=0,
        expected="The clause should state the bound the arithmetic needs.",
        actual=("The port adds `capacity_bits <= 62` on top of the drafted clause and says "
                "so at the constructor. It is a strictly stronger precondition, so "
                "nothing the clause asks for is given up. A second consequence showed up "
                "while proving it: C003's `index_ <= capacity_mask + 1` is not an "
                "invariant of ProbeSeq at all -- upstream's `index_ += Width` is "
                "uncapped, and it is the caller's group-count loop that keeps a live "
                "sequence inside the table. The port states that half of C003 as a "
                "precondition of `index()` and says so."),
        workaround="Extra precondition `capacity_bits <= 62`; C003's upper bound "
                   "promoted from invariant to precondition. Both documented in code.",
        severity="friction",
        revisit_trigger="the operator's Stage 4 batch adds the upper bound to C001 and "
                        "makes C003's two halves explicit.",
    ),
    dict(
        id="swisstable-spec-004",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("ProbeSeq's wrap is written `% capacity_size` where the reference "
                 "writes `& capacity_mask`. Attempt 1 chose that on the strength of "
                 "swisstable-verus-012, which was wrong (see swisstable-verus-014)."),
        repro_cmd=VERIFY,
        exit_code=1,
        expected="`offset(i) == (offset_ + i) & capacity_mask`, as C004 is written.",
        actual=("Reverted in attempt 2: `offset_at` and `advance` use the reference's "
                "`& capacity_mask`, and ProbeSeq.C004 is stated with `&`. The "
                "`capacity_size` field survives only as the overflow bound that keeps "
                "`offset_ + index_` inside `u64`; it is not what wraps the offset."),
        workaround="None needed.",
        severity="friction",
        revisit_trigger="n/a -- substitution withdrawn.",
    ),
    dict(
        id="swisstable-spec-005",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("GroupProbe's answers were replaced by a 16-element boolean vector in "
                 "attempt 1, on the claim that nothing about a `u16` mask is provable. "
                 "That claim was wrong (see swisstable-verus-014)."),
        repro_cmd=VERIFY,
        exit_code=1,
        expected="`fn match_full(&self, h2: u8) -> u16`, with C002/C003 stated over its bits.",
        actual=("Reverted in attempt 2: `match_full` and `match_empty_or_deleted` return "
                "`u16` masks again, built one bit at a time with "
                "`mask | (1u16 << i)`, and GroupProbe.C002/C003 are stated over those "
                "bits exactly as the concept spec does. The three bit-vector lemmas that "
                "make it work are in verif/lemmas.rs."),
        workaround="None needed.",
        severity="friction",
        revisit_trigger="n/a -- substitution withdrawn.",
    ),
    dict(
        id="swisstable-spec-006",
        pilot="swisstable-verus",
        stage="stage5-rust-port",
        command=VERIFY,
        tool="verus",
        chain="new",
        symptom=("HashMix.C003 was implemented as `hash / 2^57` in attempt 1, on the "
                 "claim that Verus cannot rule out `hash >> 57 < 128`. That claim was "
                 "wrong (see swisstable-verus-014)."),
        repro_cmd=VERIFY,
        exit_code=1,
        expected="`h2 as u64 == hash >> 57`.",
        actual=("Reverted in attempt 2: `h2` is `self.hash >> 57`, cast to `u8`, with "
                "HashMix.C003 stated over the shift. `lemma_shr57` supplies both the "
                "`< 128` bound the truncation needs and the `== x / 2^57` fact, so both "
                "forms are proved equal in the proof -- the differential oracle (#32) "
                "does not have to carry that equivalence."),
        workaround="None needed.",
        severity="friction",
        revisit_trigger="n/a -- substitution withdrawn.",
    ),
]


def main():
    # Every row whose id this script owns is *replaced*, not appended, so attempt 2
    # could correct attempt 1's text without leaving both versions in the ledger.
    owned = {r["id"] for r in ROWS}
    lines = LEDGER.read_text().splitlines() if LEDGER.exists() else []
    kept, replaced = [], 0
    for line in lines:
        if not line.strip():
            continue
        row = json.loads(line)
        if row["id"] in owned:
            replaced += 1
            continue
        kept.append(row)
    for row in ROWS:
        path, version = TOOL_ENV[row["tool"]]
        row["pyz_sha256"] = PYZ
        row["tool_path"] = str(path)
        row["tool_version"] = version
    kept.extend(ROWS)
    LEDGER.write_text("".join(json.dumps(r, sort_keys=False) + "\n" for r in kept))
    print(f"ledger now has {len(kept)} rows ({replaced} replaced by this script, "
          f"{len(ROWS) - replaced} added), {LEDGER}")


if __name__ == "__main__":
    main()
