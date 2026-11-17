---
name: csv-inspector
description: Inspect CSV headers, delimiter consistency, null rates, and column data types using pure Python stdlib. Use when profiling .csv or .tsv tabular datasets or diagnosing malformed rows. Do not use when validating JSON schemas (use json-schema-auditor) or checking Markdown citations (use markdown-citation-checker).
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
