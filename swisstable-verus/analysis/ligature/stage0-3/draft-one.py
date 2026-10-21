#!/usr/bin/env python3
"""Stage exactly one draft of one kind, so its own validator can be measured alone.

Reuses the artifact definitions in artifacts.py rather than duplicating them, so
what gets measured is the same body the pilot actually ships. Kinds that the
shipped set contains no artifact for (exemption) are measured with a minimal
schema-valid body, which is enough: the question is only whether the validator
collects a staged `.draft` of its own kind, not whether the body is meaningful.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artifacts  # noqa: E402

MINIMAL = {
    "exemption": {
        "schema_version": "1.0",
        "interaction_id": "probe_exemption_edge",
        "rationale": "Measurement probe for the draft-collection table; not a shipped artifact.",
    },
}

TEMPLATE_FOR = {
    "boundary": "boundary-drafting",
    "interaction": "interaction-drafting",
    "bridge": "bridge-drafting",
    "witness": "witness-drafting",
    "exemption": "exemption-drafting",
    "conflict": "conflict-resolution-drafting",
    "concept": "concept-to-code",
}


def main():
    kind = sys.argv[1]
    root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    shipped = next((a for a in artifacts.build() if a["kind"] == kind), None)
    if shipped is not None:
        rc = artifacts.run_one(shipped, root)
        print(f"staged {shipped['target']} exit={rc}")
        return rc
    if kind not in MINIMAL:
        print(f"no artifact of kind {kind}", file=sys.stderr)
        return 2
    target = f"rust/swisstable-verus-core/specs/_exemptions/probe_exemption_edge.json"
    a = {
        "kind": kind, "target": target, "stage": "3",
        "template": TEMPLATE_FOR[kind],
        "vars": {"interaction_id": "probe_exemption_edge", "interaction": "{}",
                 "prior_artifact": "", "finding": ""},
        "body": MINIMAL[kind],
    }
    rc = artifacts.run_one(a, root)
    print(f"staged {target} exit={rc} (minimal probe body)")
    return rc


if __name__ == "__main__":
    sys.exit(main())