# Host Adapter: OpenAI Codex (`codex`)

This guide defines how `the-one-skill` operates inside **OpenAI Codex** (CLI and cloud agent environments).

## 1. Skill Paths & `AGENTS.md` Conventions

Codex discovers skills and instructions from:
- **Workspace Skills:** `.codex/skills/<skill-name>/SKILL.md` (or `.agents/skills/<skill-name>/SKILL.md`)
- **User Global Skills:** `~/.codex/skills/<skill-name>/SKILL.md`
- **Agent Instructions:** `AGENTS.md`

When onboarding (`init`), scan the workspace skill directory and check `AGENTS.md` for any overlapping trigger rules.

## 2. Sandbox & Verification Execution

- **Deterministic Verification:** Run `python3 scripts/lint_skills.py` and `python3 scripts/export_diff.py` directly in the Codex terminal environment.
- **Trusted Skill Sources:** When discovering skills (`references/discover.md`), verify candidate URLs (`python3 scripts/lint_skills.py --check-source-url <url>`) and run `python3 scripts/lint_skills.py <staged_dir>` before installing any staged skill.
