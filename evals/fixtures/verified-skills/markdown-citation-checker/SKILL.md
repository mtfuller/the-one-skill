---
name: markdown-citation-checker
description: Validate footnotes, academic reference keys, and internal heading anchors across Markdown documents. Use when auditing .md prose or documentation for broken footnotes, missing bibliography entries, or dead anchor links. Do not use when profiling .csv spreadsheets (use csv-inspector) or validating JSON contracts (use json-schema-auditor).
---

# Markdown Citation Checker

Verify that every inline citation, footnote marker, and internal heading anchor in Markdown files resolves cleanly.

## Use when

- The user asks to audit `.md` research write-ups, RFCs, or documentation for broken `[^footnote]` references, missing bibliography entries, or dead `#heading-anchor` links.
- Preparing technical prose or papers for publication where dangling citations must be caught deterministically.

## Do not use when

- Profiling tabular `.csv` or `.tsv` datasets (use `csv-inspector` instead).
- Validating JSON payloads or OpenAPI/JSON Schema definitions (use `json-schema-auditor` instead).

## Workflow

1. **Extract Inline Markers:** Parse all `[^id]` footnote tokens, `[@citekey]` brackets, and `[label](#anchor)` links across target Markdown files.
2. **Cross-Check Definitions:** Match every inline marker against defined `[^id]:` blocks and normalized heading slugs.
3. **Report Orphans & Duplicates:** List unresolved citations, unused bibliography definitions, and duplicate anchor slugs in a concise table.

<!-- the-one-skill:opt-in -->
<!-- the-one-skill:start -->
### Continuous Evolution (`the-one-skill`)
- **Fast-Path Reflection:** If the user corrects output, a step retries, or a tool/schema error occurs while running this skill, read `the-one-skill/references/evolve.md` (§1) to propose a surgical, diff-first fix to **only this skill** (saving a pre-patch snapshot first).
- **Boundary & Cap Discipline:** Keep this `SKILL.md` under 800 tokens; move bulky examples or checklists into `references/`. If another skill triggers simultaneously, run the Full-Roster Orthogonality Audit in `the-one-skill/references/evolve.md` (§2).
<!-- the-one-skill:end -->
