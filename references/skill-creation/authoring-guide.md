# Skill Creation Guide (`references/skill-creation`)

Use this guide whenever authoring a new skill from `templates/skill-template.md` or adapting an upstream skill to `the-one-skill` standards.

---

## 1. Writing High-Signal Frontmatter (`name` & `description`)

In Gemini Web, Claude Code, and OpenAI Codex, the YAML frontmatter `description:` is the **primary routing signal** the AI host reads *before* loading `SKILL.md`. A vague description causes missed triggers or false-positive collisions.

Every skill's frontmatter `description:` must follow this three-part formula:
1. **What it does:** Concise 1-clause capability summary.
2. **`Use when ...`:** Explicit positive trigger conditions (file types, user intents, domain keywords).
3. **`Do not use when ...`:** Explicit negative boundaries naming adjacent skills or out-of-scope tasks.

### Example Frontmatter
```yaml
---
name: csv-inspector
description: Inspect CSV/TSV headers, delimiter consistency, null rates, and column types using pure Python stdlib. Use when profiling tabular flat files or debugging malformed CSV rows. Do not use when validating JSON schemas (use json-schema-auditor) or checking Markdown citations (use markdown-citation-checker).
---
```

---

## 2. Progressive Disclosure Directory Layout

Keep the entry point (`SKILL.md`) under **800 tokens** by separating concerns across four standard locations:

```text
<skill-name>/
├── SKILL.md            # <= 800 tokens: frontmatter, Use when / Do not use when, concise workflow
├── references/         # Detailed domain guides, edge-case rubrics, schema tables (loaded on demand)
├── scripts/            # Pure Python 3 stdlib scripts for deterministic checks & transformations
└── artifacts/          # Generated outputs, reports, patches, and pre-patch snapshots
```

### What Belongs in `SKILL.md` vs. `references/`
- **Keep in `SKILL.md`:** Frontmatter, `## Use when`, `## Do not use when`, 3–6 high-level workflow steps, and explicit pointers to `references/<topic>.md` and `scripts/<tool>.py`.
- **Move to `references/`:** Multi-page checklists, lookup tables, edge-case catalogs, vendor-specific caveats, and verbose few-shot examples.

---

## 3. Pre-Install Verification Checklist

Before installing any newly created skill:
1. Start from `templates/skill-template.md`.
2. Ensure the skill is orthogonal to existing installed skills (no overlapping triggers).
3. Run deterministic validation:
   ```bash
   python3 scripts/lint_skills.py <staged_skill_dir> --security-policy config/security-policy.json
   ```
4. Present the complete `SKILL.md` preview to the user for approval before saving to the host's skill directory.
