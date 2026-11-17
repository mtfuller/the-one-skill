# Discover: Trusted Lookup & Skill Creation (`references/discover.md`)

Use this reference when a task has no matching installed skill, when a multi-step workflow repeats across sessions, or when the user asks to find or create a skill.

**Prefer fewer skills.** Before proposing a new skill, check whether refining an installed skill would cover the task. Propose a new skill only for a workflow the user is likely to repeat, and never install one without explicit approval.

---

## 1. Check Trusted Skill Sources First

Always search verified official organization catalogs before authoring a skill from scratch:
- **Anthropic Official Skills:** `anthropics/skills` (`https://github.com/anthropics/skills`)
- **OpenAI Official Skills:** `openai/skills` (`https://github.com/openai/skills`)
- **Google Gemini Official Skills:** `google-gemini/gemini-skills` (`https://github.com/google-gemini/gemini-skills`)

### Lookup & Verification Steps
0. **Code execution required.** Steps 2–5 need `python3 scripts/lint_skills.py --self-check` to pass (on Gemini Web, after staging the scripts in Task mode; see `vendors/gemini-web.md` §1). If it cannot run (Gemini Web Chat mode), stop before installing anything from outside: explain that the security check cannot run and ask the user to switch to Gemini **Task** mode. Proceed without it only if the user explicitly accepts the skipped check, and then read every file and list anything that fetches URLs, reads credentials, runs encoded or dynamic code, or tells the agent to ignore instructions.
1. Search or browse the trusted catalogs above for a skill matching the user's task domain:
   - **Claude Code / Codex:** Use git/GitHub CLI or web search restricted to those repositories.
   - **Gemini Web:** Use Gemini's built-in web browsing tool to inspect `github.com/anthropics/skills`, `github.com/openai/skills`, or `github.com/google-gemini/gemini-skills`.
2. Verify the candidate URL belongs to an approved trusted source:
   ```bash
   python3 scripts/lint_skills.py --check-source-url <candidate_url>
   ```
3. Stage the fetched files **outside the skills root** (e.g., `/tmp/staged-skill/<skill-name>/`) and run the deterministic security & lint gate:
   ```bash
   python3 scripts/lint_skills.py <staged_dir>
   ```
   - Blocks prompt injection (`SEC-001`), network exfiltration (`SEC-002`), credential harvesting (`SEC-003`), opaque `eval`/`exec`/`base64` payloads (`SEC-004`), and marker tampering (`SEC-005`). These checks are pattern-based and miss a lot: also read every staged file before installing.
   - If the upstream skill exceeds **800 tokens** or lacks explicit `Use when / Do not use when` frontmatter guidance, tailor it in the staging folder before installation.
4. **Roster Overlap Check:** Lint the staged skill together with the installed roster so trigger collisions are reported before anything is installed:
   ```bash
   python3 scripts/lint_skills.py <skills_root> <staged_dir>
   ```
   If it overlaps an installed skill, propose refining that skill instead (`references/evolve.md`), or install with `--replaces` to merge.
5. Present a concise discovery card (`<name>`, `<provider>:<repo>`, `lint_skills.py: PASS`, token count, overlaps) and install only after the user approves:
   ```bash
   python3 scripts/skillctl.py --root <skills_root> install <staged_dir>
   ```
   On Gemini Web, create the skill through Gemini's own skill tools instead (`vendors/gemini-web.md`).

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

```

Validate the draft with `python3 scripts/lint_skills.py <skills_root> <staged_skill_dir>` (lint + overlap check), get user approval, then install with `python3 scripts/skillctl.py --root <skills_root> install <staged_skill_dir>`.
