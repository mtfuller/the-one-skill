# Host Adapter: OpenAI Codex (`codex`)

This guide defines how `the-one-skill` operates inside **OpenAI Codex** (CLI and cloud agent environments).

## 1. Skill Paths & `AGENTS.md` Conventions

Codex discovers skills and instructions from:
- **Workspace Skills:** `.codex/skills/<skill-name>/SKILL.md` (or `.agents/skills/<skill-name>/SKILL.md`)
- **User Global Skills:** `~/.codex/skills/<skill-name>/SKILL.md`
- **Agent Instructions:** `AGENTS.md`

When onboarding (`init`), scan the workspace skill directory and check `AGENTS.md` for any overlapping trigger rules.

## 2. Sandbox & Verification Execution

- **Deterministic Verification:** Run `python3 scripts/verify_hash.py`, `python3 scripts/lint_skills.py`, and `python3 scripts/export_diff.py` directly in the Codex terminal environment.
- **Network-Restricted Sandboxes:** When running in a Codex environment with outbound network disabled after setup, rely on local git clones or cached registry snapshots for `discover` and `export`, and always enforce the `verify_hash.py` `PASS` gate before installing any staged skill.
