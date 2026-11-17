---
name: json-schema-auditor
description: Audit JSON payloads and Draft-07/2020-12 JSON Schema definitions for required keys, type mismatches, and breaking contract changes. Use when validating .json config files, API payloads, or schema contracts. Do not use when profiling flat .csv files (use csv-inspector) or checking Markdown footnotes (use markdown-citation-checker).
---

# JSON Schema Auditor

Validate structured `.json` payloads and schema contracts using deterministic Python `json` inspection.

## Use when

- The user wants to validate JSON configuration files, API payloads, or JSON Schema definitions for missing `required` properties, enum violations, or type mismatches.
- Comparing two versions of a JSON contract to flag backward-incompatible field removals or type narrowing.

## Do not use when

- Inspecting flat `.csv` or `.tsv` spreadsheets (use `csv-inspector` instead).
- Auditing Markdown footnotes or prose citations (use `markdown-citation-checker` instead).

## Workflow

1. **Parse & Canonicalize:** Load the target `.json` and schema files with `json.loads()`, catching syntax errors with exact line and column numbers.
2. **Audit Structural Rules:** Check `type`, `required`, `properties`, `additionalProperties`, and `enum` constraints recursively.
3. **Emit Contract Report:** Output any schema violations or breaking diff entries with JSON Pointer paths (`/properties/foo/type`).
