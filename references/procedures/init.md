# Procedure: Onboarding & Consent (`init`)

Use this reference when the user asks to initialize `the-one-skill`, onboard existing skills, review consent status, or resolve initial trigger collisions.

## 1. Discover Installed Skills

1. Identify the host environment and load the matching adapter (`vendors/gemini-web.md`, `vendors/claude-code.md`, or `vendors/codex.md`).
2. On **Gemini Web**, check Memory first for an existing `the-one-skill` consent roster (`opt-in` / `ignore` list) to avoid unnecessary file reads, then inspect any newly uploaded skills.
3. On **Claude Code** or **Codex**, scan the workspace and user skill directories for `SKILL.md` files (excluding `the-one-skill` itself).

## 2. Run Deterministic Lint & Overlap Analysis

Execute the linter across the discovered skills directory:

```bash
python3 scripts/lint_skills.py <skills_root_dir>
```

Review the report for:
- **Consent Status:** `opt-in` (`<!-- the-one-skill:opt-in -->`), `ignore` (`<!-- the-one-skill:ignore -->`), or `unmanaged` (no marker).
- **Token Budget Violations:** Any `SKILL.md` exceeding the **800-token ceiling**.
- **Frontmatter & Boundary Gaps:** Missing YAML `name`/`description` (including explicit `"Use when..."` / `"Do not use when..."` guidance in the frontmatter description) or missing `## Use when` / `## Do not use when` sections.
- **Trigger Overlaps:** Pairs of skills with overlapping trigger keywords or high Jaccard similarity.

## 3. Per-Skill Consent Prompt

Present a concise summary table of all unmanaged skills and ask the user to choose one option per skill (or in batch):

| Choice | Marker Written | Behavior |
| :--- | :--- | :--- |
| **Opt-In** | `<!-- the-one-skill:opt-in -->` + delimited block | Eligible for Fast-Path reflection, orthogonality audits, and diff-first evolution. |
| **Opt-Out (`ignore`)** | `<!-- the-one-skill:ignore -->` | Locked. `the-one-skill` will never read for evolution or propose edits unless explicitly unlocked. |
| **Ask Later** | *(No marker added)* | Remains unmanaged for this session; prompted again only on explicit `/init`. |

## 4. Delimited Mounting

Follow `references/skill-modification/modification-guide.md` to snapshot each opted-in skill, verify token headroom (`<= 800` tokens after adding `templates/integration-block.md`), present a diff for user approval, and mirror the consent state in Gemini Memory if running on Gemini Web.
