---
name: csv-inspector
description: Inspect CSV headers, delimiter consistency, null rates, and column data types using pure Python stdlib.
---

# CSV Inspector

Deterministic profiling of tabular `.csv` and `.tsv` datasets without third-party dependencies.

## Use when

- The user uploads or references a `.csv` or `.tsv` file and wants column summaries, row counts, delimiter validation, or missing-value statistics.
- A data pipeline needs schema inference or malformed-row detection on tabular flat files.

## Do not use when

- The input is a nested JSON document or JSON Schema file (use `json-schema-auditor` instead).
- The user wants Markdown bibliography or link citation checking (use `markdown-citation-checker` instead).

## Workflow

1. **Detect Dialect & Header:** Use Python's `csv.Sniffer` and `csv.reader` on the first 100 rows to confirm delimiter and quote characters.
2. **Scan Row Integrity:** Count total rows, flag rows whose column count differs from the header length, and compute per-column null/empty percentages.
3. **Summarize Types:** Classify each column as integer, float, ISO-8601 date, boolean, or free-text string and output a compact Markdown report to `artifacts/`.

<!-- the-one-skill:opt-in -->
<!-- the-one-skill:start -->
### Continuous Evolution (`the-one-skill`)
- **Fast-Path Reflection:** If the user corrects output, a step retries, or a tool/schema error occurs while running this skill, read `the-one-skill/references/reflect.md` (Fast-Path) to propose a surgical, diff-first fix to **only this skill** (saving a pre-patch snapshot first).
- **Boundary & Cap Discipline:** Keep this `SKILL.md` under 800 tokens; move bulky examples or checklists into `references/`. If another skill triggers simultaneously, invoke the Full-Roster Orthogonality Audit in `the-one-skill/references/reflect.md`.
<!-- the-one-skill:end -->
