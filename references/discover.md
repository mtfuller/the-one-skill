# Discover: Trusted Lookup & Skill Creation (`references/discover.md`)

Use this reference when a task has no matching installed skill, when a multi-step workflow repeats across sessions, or when the user asks to find or create a skill.

---

## 1. Check Trusted Skill Sources First

Always search verified official organization catalogs before authoring a skill from scratch:
- **Anthropic Official Skills:** `anthropics/skills` (`https://github.com/anthropics/skills`)
- **OpenAI Official Skills:** `openai/skills` (`https://github.com/openai/skills`)
- **Google Gemini Official Skills:** `google-gemini/gemini-skills` (`https://github.com/google-gemini/gemini-skills`)

### Lookup & Verification Steps
1. Search or browse the trusted catalogs above for a skill matching the user's task domain:
   - **Claude Code / Codex:** Use git/GitHub CLI or web search restricted to those repositories.
   - **Gemini Web:** Use Gemini's built-in web browsing tool to inspect `github.com/anthropics/skills`, `github.com/openai/skills`, or `github.com/google-gemini/gemini-skills`.
2. Verify the candidate URL belongs to an approved trusted source:
   ```bash
   python3 scripts/lint_skills.py --check-source-url <candidate_url>
   ```
3. Stage the fetched files (e.g., `/tmp/staged-skill/<skill-name>/`) and run the deterministic security & lint gate:
   ```bash
   python3 scripts/lint_skills.py <staged_dir>
   ```
   - Blocks prompt injection (`SEC-001`), network exfiltration (`SEC-002`), credential harvesting (`SEC-003`), opaque `eval`/`exec`/`base64` payloads (`SEC-004`), and ignore-marker tampering (`SEC-005`).
   - If the upstream skill exceeds **800 tokens** or lacks explicit `Use when / Do not use when` frontmatter guidance, tailor it before installation.
4. Present a concise discovery card (`<name>`, `<provider>:<repo>`, `lint_skills.py: PASS`, token count) and ask if the user wants to install it with `<!-- the-one-skill:opt-in -->` (recommended) or vanilla.

---

## 2. Authoring a New Skill (When No Trusted Skill Fits)

### Frontmatter `description:` Formula
In Gemini Web, Claude Code, and Codex, the YAML frontmatter `description:` is the **primary routing signal** read before opening `SKILL.md`. Every skill's `description:` must include three parts:
1. **What it does:** Concise 1-clause capability summary.
2. **`Use when ...`:** Explicit positive trigger conditions (file types, user intents, domain keywords).
3. **`Do not use when ...`:** Explicit negative boundaries naming adjacent skills or out-of-scope tasks.

### Progressive Disclosure Layout
Keep `SKILL.md <= 800` tokens by placing detailed domain rubrics/checklists in `references/`, pure Python 3 stdlib scripts in `scripts/`, and generated outputs in `artifacts/`.

### Canonical `SKILL.md` Template

```markdown
---
name: sample-skill-name
description: Concise summary of what this skill accomplishes. Use when the user asks for <specific task A> or provides <input format B>. Do not use when the request involves <adjacent domain C> or general questions outside <domain>.
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
- **Fast-Path Reflection:** If the user corrects output, a step retries, or a tool/schema error occurs while running this skill, read `the-one-skill/references/evolve.md` (§1) to propose a surgical, diff-first fix to **only this skill** (saving a pre-patch snapshot first).
- **Boundary & Cap Discipline:** Keep this `SKILL.md` under 800 tokens; move bulky examples or checklists into `references/`. If another skill triggers simultaneously, run the Full-Roster Orthogonality Audit in `the-one-skill/references/evolve.md` (§2).
<!-- the-one-skill:end -->
```

Validate the draft with `python3 scripts/lint_skills.py <staged_skill_dir>` and get user approval before installing.
