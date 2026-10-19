# crypto-mixed: Stage 7 manifests regenerated for Ligature 1.4.2 (#134, 2026-10-19)

Ligature 1.4.2 (bundle SHA-256
`c4d989f3c72f7c9439cefb9a787b5ce23ad8467204fd61d9e00b761675c5b184`, attested)
changed two gate-pinned managed resources, so both crypto-mixed work-package
manifests failed G13 after the upgrade (crypto-mixed commit `f4ca347`):

| Resource | Pinned (1.4.1) | Actual (1.4.2) |
|---|---|---|
| `.codex/skills/ligature/SKILL.md` | `sha256:6b3c3ae7…6216` | `sha256:431a8179…588a` |
| `.ligature/schemas/project-state.schema.json` | `sha256:f38a526b…64bd` | `sha256:f5f974e4…5371` |

## Regeneration

The user issued two exact one-shot human grants under #134 (issuer
`roger-codex-luna6`, TTL 3600 s): `GW-a661e31b5e00` for
`ci/manifest/WP-CRYPTO-MIXED-PRIMITIVES-001.json` and `GW-3442634160e8` for
`ci/manifest/WP-CRYPTO-MIXED-AEAD-001.json`. The agent did not issue grants.

Inputs were the rebuilt Stage 7 plans already used on 2026-10-18
(`../../ligature-1.4.1-final-2026-10-17/crypto-mixed-stage7-plans/`; SHA-256
re-checked: PRIMITIVES `8d97bcb8…7712`, AEAD `34a14847…9b72`). Each live
manifest matched its previous grant-backed generation event before the run.

```sh
python3 -I tools/ligature/ligature.pyz generate-work-package --plan <plan> --issue 134 \
  --toolchain 1.95.0-x86_64-unknown-linux-gnu --target x86_64-unknown-linux-gnu \
  --feature default --grant-id <grant> --regenerate --json
```

| Package | Exit | Result | Before → after |
|---|---|---|---|
| PRIMITIVES | 0 | regenerated | `3a7270e4…5aff` → `445326e1…6353` |
| AEAD | 0 | regenerated | `cd4da083…4fa6` → `e309f9fb…517c` |

Each manifest diff is exactly three lines: the two `gate_integrity` hashes
above and `provenance.base_commit` `13e6021` → `f4ca347`. Functions,
obligations, assurance scopes, gates and write policy are unchanged. Pre-run
copies: `WP-CRYPTO-MIXED-*-001.before.json`; generation events:
`generate-*.json` (also appended to `ci/results/protected-writes.jsonl`).

## Validation after regeneration

| Command | Exit | Result | File |
|---|---|---|---|
| `validate-work-package` PRIMITIVES | 0 | passes G1a and §10.1 (2 info) | `validate-wp-primitives.out` |
| `validate-work-package` AEAD | 0 | passes G1a and §10.1 (2 info) | `validate-wp-aead.out` |
| `write-set-check --issue 134 --json` | 0 | no violations | `write-set-check-134.json` |
| `write-set-check --json` | 0 | no violations | `write-set-check.json` |
| `validate-closure` | 0 | G1a/G1b and G17 consistency (2 discovered) | `validate-closure.out` |
| `doctor` | 0 | current | `doctor.out` |
| `gate-g9` | 0 | both bridges pass | `gate-g9.out` |
| `gate-r1-g16 --json` | 1 | blocked: 16 discovered, 9 checked, 4 unresolved, 3 undeclared blocking | `gate-r1-g16.json` |
| `gate-g14 --json` | 1 | `crypto-kani` blocked (bounded); 137.5 s, peak RSS ≈ 7.3 GB; 3 Kani obligations and 2 bridge records re-evaluated | `gate-g14.json` |

G14's only blocking findings are the call-site ones: WP-AEAD
`all-discovered-resolved` fails for both required bridges (4 unresolved), and
`unresolved_indirect_calls_at_or_above_medium` is declared 0 but computed 4.
CG3 (`generic_callees_type_universal_or_creusot_owned`) stays `degraded` at
the accepted per-instantiation ceiling. No G13 or assurance-record finding
remains.

G13 is cleared for both packages. The remaining #134 blockers are the Stage 8A
call-site items (#47): possible-dispatch sites CS-CHACHA20POLY1305-ENCRYPT-003,
-ENCRYPT-004, -DECRYPT-003 and CS-POLY1305-UPDATE-001, and the undeclared
direct calls CS-CHACHA20POLY1305-ENCRYPT-002 / -DECRYPT-002 (→
`ChaCha20.with_counter`) and CS-POLY1305-SET-KEY-001 (→ `Poly1305State.new`).
