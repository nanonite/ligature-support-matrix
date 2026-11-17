# P4-5 Q1: Verus-only CG3 probe

**2026-10-25 update:** local #175 is verified resolved in Ligature 1.4.3.
The same one-obligation scratch slice now passes G14 with CG3 VERIFIED and
the cluster closes. See [1.4.3 verification](../verification/ligature-1.4.3-2026-10-25/issue175/README.md).
The results below preserve the original 1.4.2 failure.

## Result

**No.** Ligature 1.4.2 does not report CG3 VERIFIED for a Verus-only deductive closure. `gate-g14 --json` exits 1 and blocks `date-creusot-core` on `generic_callees_type_universal_or_creusot_owned`. The gate reports no workspace-level findings and exactly one cluster finding: CG3.

The gate diagnostic says the achieved record is `verus-deductive-check`; it says Creusot ownership must be established positively and that the `type_universal` disjunct needs type information no artifact in the pipeline carries. The closure is otherwise reported as `deductive`, its owner is Verus, and the one recorded obligation is accepted and rechecked.

This contradicts the expected D outcome for Q1 in `VERIFIER-MATRIX.md`, which defines the deductive verifier set to include Verus.
## Probe scope

This is a **one-obligation P1 gate-classification slice**, not the nine-obligation A2 port. It uses P1's `Month.C001`, with one real Verus proof and no other achieved records. The scratch descriptor selects Verus; the closure declares `deductive`, `owning_verifier: verus`, and CG3 true; `expected_obligations` pins only `Month.C001`.

The Verus proof expresses the P1 month predicate directly and carries the required proof note. Verus reports whole-crate success, one verified goal, zero errors, and the exact note `ligature:Month.C001`. `record-assurance` accepts the report as `verus-deductive-check`. `validate-closure` and `validate-promotion` both pass. The accepted P1 concept specification and promotion receipt were left intact; this probe tests G14's verifier classification, not a re-authored P1 spec or full port.

## Environment

- Seed: `date-creusot` commit `535b5a536114a06c5eb1606834041b92cc2ae8986`
- Ligature: 1.4.2, bundle SHA-256 `c4d989f3c72f7c9439cefb9a787b5ce23ad8467204fd61d9e00b761675c5b184`
- Verus: 0.2026.05.24.ecee80a, Rust toolchain 1.95.0

## Replay commands and outcomes

Run from the scratch workspace root. Verus is available at `/nix/store/57l94534x07sysi7gjf4zkkpai6cw6vc-verus-tools/bin`; add the pinned Z3 directory to `PATH` as in the recorded command.

| Command | Exit | Evidence |
|---|---:|---|
| `verus --crate-type=lib --multiple-errors 200 --output-json analysis/p4-5-q1/verus_month.rs > analysis/p4-5-q1/verus-month.json 2> analysis/p4-5-q1/verus-month.stderr.txt` | 0 | `verus-month.json` |
| `python3 tools/ligature/ligature.pyz record-assurance WP-DATE-VERUS --verus-json analysis/p4-5-q1/verus-month.json --verus-function Month.C001=verus_month::month_ok` | 0 | `record-assurance.stdout.txt` |
| `python3 tools/ligature/ligature.pyz validate-closure` | 0 | `validate-closure.stdout.txt` |
| `python3 tools/ligature/ligature.pyz validate-promotion specs/_promotions/date-creusot-core.json` | 0 | `validate-promotion.stdout.txt` |
| `python3 tools/ligature/ligature.pyz gate-g14 --json` | 1 | `gate-g14.json` |

**2026-11-17 archive note:** the untracked `scratch-inputs/` fixture was
archived to `analysis/p4-5-q1/scratch-inputs-archive-2026-11-17.tar.gz`
because Ligature 1.5.1's G1b scans the live pilot for closure artifacts
outside `specs/_closure/`. See
[`scratch-inputs-archive.md`](scratch-inputs-archive.md) for the member
mapping, hashes, and replay location. Extract it outside the pilot tree when
replaying; nothing in the probe result changed.

The proof, configuration changes, and G14 run were made in the scratch copy under `/tmp`. The only change in the P1 checkout is this evidence directory under its declared `analysis/**` write root; no code or `write_set` declaration changed. `write-set-check --issue 159 --json` still reports the two known out-of-set files, `.gitignore` and `PORT-GAPS.md`; this evidence directory is not a violation. The check output is saved as `write-set-check.json`.

This probe does not complete A2, run the P1 oracle, or establish the nine-obligation P1-Verus row.

## Process note

An earlier troubleshooting step consulted the prohibited Ligature source checkout. Those observations and any source-derived claims are excluded; the result above is based on the pinned binary CLI outputs.
