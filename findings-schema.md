# Limitations schema

Each `limitations.jsonl` line is one JSON object with these fields: `id`, `pilot`, `stage`, `command`, `tool`, `chain`, `symptom`, `repro_cmd`, `exit_code`, `expected`, `actual`, `workaround`, `severity`, `revisit_trigger`, `pyz_sha256`, `tool_path`, and `tool_version`.

`tool` is one of `ligature`, `creusot`, `verus`, `kani`, `nextest`, `rdb`, `mcp`, or `oracle`. `chain` is `A.x`, `B.x`, `C.n`, or `new`. `exit_code` is an integer, and `severity` is `blocker`, `scope-cut`, or `friction`. `tool_path` records the resolved executable path and `tool_version` records the output used for the finding.

Example line:

```json
{"id":"pilot-001","pilot":"date-creusot","stage":"gate-g14","command":"cargo creusot prove","tool":"creusot","chain":"A.1","symptom":"example recorded limitation","repro_cmd":"cargo creusot prove","exit_code":1,"expected":"clean exit","actual":"limitation reproduced","workaround":"record and continue","severity":"friction","revisit_trigger":"next pilot setup","pyz_sha256":"0ffe6e0eeba3cf329228b9ce3e8f0d576458b6b2a9aec48e43f60a016f9afc4f","tool_path":"/path/to/creusot","tool_version":"0.12.0-dev"}
```
