"""Derive a Stage 7 plan from an existing generated work-package manifest.

Every field is copied mechanically from the manifest (plus the closure cluster
name); nothing is chosen. Usage: reconstruct_plan.py MANIFEST CLUSTER OUT
"""
import json, sys

manifest_path, cluster, out = sys.argv[1:4]
m = json.load(open(manifest_path))
dod = m["definition_of_done"]
provided = [g["obligation_id"] for g in dod["provided_guarantees"]]
plan = {
    "work_package": m["work_package"],
    "issue": m["issue"],
    "cluster": cluster,
    "functions": m["functions"],
    "depends_on": m["depends_on"],
    "coupling_notes": m["coupling_notes"],
    "provided_obligations": provided,
    "required_obligations": [g["obligation_id"] for g in dod["required_guarantees"]],
    "bridges": [p["bridge_id"] for p in dod["required_preconditions_to_establish"]],
    "assumptions": dod["trusted_assumptions"],
    "harnesses": {g["obligation_id"]: g["harness"] for g in dod["provided_guarantees"]},
    "gates": m["gates"],
    "scheduling_rule": m["scheduling_rule"],
    "allowed_write_set": m["write_policy"]["allowed_write_set"],
    "protected_write_set": m["write_policy"]["protected_write_set"],
}
assert sorted(provided) == sorted(m["obligations"]) or not provided, "obligations mismatch"
with open(out, "w") as f:
    json.dump(plan, f, indent=2)
    f.write("\n")
