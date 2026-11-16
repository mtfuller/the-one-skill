---
name: json-schema-auditor
description: Audit JSON payloads and Draft-07/2020-12 JSON Schema definitions for required keys, type mismatches, and breaking contract changes.
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

<!-- the-one-skill:opt-in -->
<!-- the-one-skill:start -->
### Continuous Evolution (`the-one-skill`)
- **Fast-Path Reflection:** If the user corrects output, a step retries, or a tool/schema error occurs while running this skill, read `the-one-skill/references/reflect.md` (Fast-Path) to propose a surgical, diff-first fix to **only this skill** (saving a pre-patch snapshot first).
- **Boundary & Cap Discipline:** Keep this `SKILL.md` under 800 tokens; move bulky examples or checklists into `references/`. If another skill triggers simultaneously, invoke the Full-Roster Orthogonality Audit in `the-one-skill/references/reflect.md`.
<!-- the-one-skill:end -->
