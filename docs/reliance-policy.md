# Reliance policy — `crypto-mixed`

This is standing governance for the `crypto-mixed` port, at the path declared
by `compatibility_policy.reliance_policy_path` in the project descriptor.
Changes to this policy go through the human-authority checkpoint in plan.md
§7.2 and are versioned as described below.

Schema version this policy targets: 1.0.
Owner: Crypto Mixed P3 port maintainer.
Policy version: `reliance-policy@0.1`

`ligature accept-promotion` parses the `Policy version:` line to compute a
promotion receipt's `policy_version` field (chainlink #45), and refuses to
generate a receipt if the line is missing or malformed. The acceptance
command below stamps this marker and records the reviewed policy content.

For this initial adoption, the selected version is `reliance-policy@0.1`:

```
ligature accept-policy --reviewer roger-codex-luna6 --version reliance-policy@0.1
```

`accept-policy` is a human checkpoint (chainlink #113). Bump the version through
the same command for every substantive change to the resolution rule or this
project's additions below.

## Resolution rule (fixed — do not override)

This table resolves the schema-prose vs. G2+ conflict (plan.md §2) and is
identical across every project using this pipeline. It is not a
project-specific choice:

| Source in the concept spec | Lands in the boundary artifact as |
|---|---|
| callee **precondition** | `callee_guarantees`, recorded as the obligation the **caller** must establish before the call — not a guarantee the callee provides — and discharged by the bridge specification (plan.md §8.2). A bridge's `callee_requirement` must be one of the boundary's own `callee_guarantees` entries (G2), so an obligation recorded nowhere there is one no bridge can discharge |
| callee **postcondition** / **invariant** relied on | `callee_guarantees` |
| adversary case (`A*`) | evidence / test seed — **never** a guarantee, never eligible for `callee_guarantees` |
| the **caller's own** precondition / invariant | the caller's own contract — never a `callee_guarantees` entry; a bridge cites it in `available_contract_facts` |

G2+ (role safety, plan.md §12) enforces the third row mechanically: an
adversary-case id inside `callee_guarantees` is a hard error, not a style
warning. It also reads each entry's own `kind` and reports a `precondition`
entry as the caller obligation of the first row rather than letting the
field name imply the second — one definition
(`scripts/validate_boundary_contracts.py`'s `callee_obligation_role()`),
read by the gate that reports the role, so "is this a guarantee or an
obligation?" is answered from the artifacts and not from a reader's memory.
An **empty** `callee_guarantees` is therefore a claim, not an omission: it
declares that this call depends on nothing of the callee's and has no
precondition to establish.

## Project-specific additions

Everything below this line is this project's own governance, additive to
the fixed rule above — it can narrow or clarify, but never contradict or
weaken the resolution table.

- **Domain-specific evidence sources.** Use Botan 3.13.0 at the pinned commit
  recorded in `upstream/upstream-pin.json` as the reference implementation
  for differential cases. Record the source commit, build configuration,
  inputs, and random seed with each result. Use RFC 8439's algorithm
  descriptions and test vectors for ChaCha20, Poly1305, and
  ChaCha20-Poly1305. If BLAKE2b is included in the adopted P3 scope, use RFC
  7693's algorithm description, worked example, and self-test; that RFC does
  not provide a full test-vector set. Botan agreement and test-vector matches
  are testing evidence, not proofs. P3 proof claims use Kani results tied to
  their harnesses, bounds, and assumptions. Functional tests and Kani results
  do not establish constant-time behavior; any such claim needs separate
  timing evidence for a stated target and configuration.
- **Additional role-safety checks.** Apply the fixed resolution table above
  without project-specific exceptions. For every non-empty
  `callee_guarantees` entry, cite the upstream function and distinguish its
  behavior from caller obligations. Treat adversarial inputs as evidence or
  test seeds, never as callee guarantees. Keep an artifact with an unresolved
  role interpretation unapproved.
- **Escalation path.** When Botan behavior, published algorithm references,
  or test results disagree, record the case as an open finding with the source
  location, exact input or seed, and configuration; leave the affected
  artifact unapproved. The Crypto Mixed P3 port maintainer resolves
  project-specific interpretations. If the dispute concerns shared Ligature
  rules or validation, escalate it to the Ligature maintainers rather than
  adding a local exception. Update this policy through the human
  policy-acceptance checkpoint when a resolution changes its rules.

## Change history

| Version | Date | Reviewer | Change |
|---|---|---|---|
| `0.1` | `2026-10-12` | `roger-codex-luna6` | Initial adoption for the Kani-bounded Crypto Mixed P3 port |
