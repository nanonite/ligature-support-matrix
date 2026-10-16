# Codesight-mcp P1 Analysis

Repository: `local/date-c96cc248007d`
Source: `upstream/date` at tag `v3.0.5`, SHA `179a6b921ccd6179b5b04dce812a89f71a51b4df`
Index storage: `analysis/codesight/index`
Allowed roots: this root's `upstream/` and `rust/` only

## Index

`get-status.json` records one indexed repository, 122 files, 416 symbols, C++/C and other source languages, and index version 2. The index was created with the registered project configuration and `--no-ai`; no path outside the allowed roots was used.

`get-file-outline-date.json` and `get-file-outline-iso-week.json` preserve the direct header-outline evidence. `date.h` is reported as language `c` with only seven symbols, while `iso_week.h` is reported as language `c` with only its module symbol. The requested civil-calendar, weekday, year-month-day, and ISO-week definitions are not present as resolved symbols in these outlines.

## Operation outputs

- `get-callers-days_from_civil.json`, `get-callees-days_from_civil.json`, `get-callers-civil_from_days.json`, and `get-callees-civil_from_days.json` cover the two civil conversion areas. All four return `Symbol not found` for the deterministic source-derived IDs.
- `get-callers-weekday.json` and `get-callees-weekday.json` cover the date weekday area. Both return `Symbol not found` for `include/date/date.h::weekday#type`.
- `get-callers-year_month_day.json` and `get-callees-year_month_day.json` cover year-month-day validity and calendar composition. Both return `Symbol not found` for `include/date/date.h::year_month_day#type`.
- `get-callers-iso-week.json` and `get-callees-iso-week.json` cover the ISO-week area. Both return `Symbol not found` for `include/date/iso_week.h::weekday#type`.
- `get-type-hierarchy-year_month_day.json` and `get-type-hierarchy-weekday.json` cover the requested date types. `get-type-hierarchy-iso-week-year.json`, `get-type-hierarchy-iso-week-weeknum.json`, and `get-type-hierarchy-iso-week-weekday.json` cover ISO-week types. All five return `Symbol not found`; no inheritance or operator/CRTP relationship is reported because the types were not extracted.
- `get-imports-date.json` contains 23 imports from `date.h`, primarily standard headers. `get-imports-iso-week.json` contains `climits` and `date.h`, successfully showing the ISO-week header's dependency on the date header. `get-imports-date-importers.json` unexpectedly reports zero importers even though the iso-week imports output resolves `date.h`; reverse import lookup is therefore incomplete.
- `get-impact-days_from_civil.json` and `get-impact-civil_from_days.json` cover the core conversion impact queries. Both return `Symbol not found`.
- `get-call-chain-year_month_day-to-days.json` attempts the plausible year-month-day to days-from-civil chain. It returns `Symbol not found` for the year-month-day source ID and does not fabricate a path.
- `get-diagram-imports-date.json` is a successful Mermaid import diagram with 24 nodes and 23 edges. `get-diagram-call-graph-days.json` attempts a call graph centered on `days_from_civil` but returns `Symbol not found`.
- `get-status.json`, `get-file-outline-date.json`, and `get-file-outline-iso-week.json` provide the index health and header-extraction evidence for the operation results. `get-imports-date-importers.json` is the reverse-direction import probe.

## Subset interpretation

The analysis request covers `days_from_civil`, `civil_from_days`, `weekday`, `year_month_day` validity, and ISO week. The successful import evidence confirms the expected header dependency `iso_week.h -> date.h`. The graph operations cannot establish call, impact, type, or call-chain edges for the target definitions because the C++ header parser did not extract them. This is recorded as an MCP limitation rather than interpreted as evidence that the C++ relationships do not exist.
