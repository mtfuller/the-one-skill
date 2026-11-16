---
name: sample-skill-name
description: Concise one-sentence summary of what this skill accomplishes and its domain.
---

# Sample Skill Title

Brief overview of the skill's core responsibility in 1–2 sentences. Keep this `SKILL.md` under **800 tokens**; place detailed domain rubrics in `references/`, deterministic utilities in `scripts/`, and generated outputs in `artifacts/`.

## Use when

- The user asks to perform `<specific task or workflow A>`.
- The input involves `<specific file format, schema, or domain signal B>`.
- A repeatable multi-step process for `<domain C>` is needed.

## Do not use when

- The request is a general question outside `<domain C>` or handled by `<adjacent-skill-name>`.
- The user needs `<out-of-scope capability>` where another specialized skill applies.

## Workflow

1. **Inspect Input:** Validate the target files or parameters before running actions.
2. **Load Reference on Demand:** Read `references/guide.md` only when detailed edge-case rules are required.
3. **Run Deterministic Checks:** Execute `python3 scripts/<helper>.py` (pure Python 3 stdlib) for validation or transformation.
4. **Emit Output:** Write structured reports or diffs to `artifacts/` and present a concise summary.

<!-- the-one-skill:opt-in -->
<!-- the-one-skill:start -->
### Continuous Evolution (`the-one-skill`)
- **Fast-Path Reflection:** If the user corrects output, a step retries, or a tool/schema error occurs while running this skill, read `the-one-skill/references/reflect.md` (Fast-Path) to propose a surgical, diff-first fix to **only this skill** (saving a pre-patch snapshot first).
- **Boundary & Cap Discipline:** Keep this `SKILL.md` under 800 tokens; move bulky examples or checklists into `references/`. If another skill triggers simultaneously, invoke the Full-Roster Orthogonality Audit in `the-one-skill/references/reflect.md`.
<!-- the-one-skill:end -->
