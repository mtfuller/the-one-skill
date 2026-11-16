---
name: the-one-skill
description: Personal-first skill manager for Gemini Web, Claude Code, and OpenAI Codex. Use when onboarding or auditing skills, fixing friction or retries in an opted-in skill, resolving overlap when multiple skills trigger together, discovering or creating a missing skill, reverting edits, or exporting diffs for PRs. Do not use when executing a normal domain task covered cleanly by one skill with zero friction, or to modify any skill marked with the-one-skill:ignore.
---

# `the-one-skill` — Control Plane

> **One skill to discover, evolve, and tailor them all.**

Manage your skill library using standard Agent Skills files (`SKILL.md`, `references/`, `scripts/`, `artifacts/`). Load only the reference file needed for the active intent.

## Use when

- Onboarding or auditing a skill library (`init`, opt-in or ignore consent).
- Friction, corrections, or retries occur in an opted-in skill (**Fast-Path Single-Skill Audit**).
- Multiple skills trigger together, a workflow spans 3+ skills, or overlap/bloat is reported (**Full-Roster Orthogonality Audit**).
- A task has no matching skill or repeats across sessions (`discover` or create).
- Reverting a skill edit, stripping integration blocks, or exporting diffs (`revert`, `uninstall`, `export`).

## Do not use when

- Executing a normal domain task covered cleanly by a single skill with zero friction.
- Modifying any skill locked with `the-one-skill:ignore` (unless asked to change its consent).

## Intent Routing (Load Reference on Demand)

Infer intent naturally from context (or optional `/init`, `/discover`, `/reflect`, `/revert`, `/uninstall`, `/export` shortcuts):

1. **Friction in 1 Opted-In Skill → Fast-Path Single-Skill Audit**
   - Read `references/procedures/reflect.md` (§1) and `references/skill-modification/modification-guide.md`. Inspect **only that active skill** and propose a surgical diff.
2. **Trigger Collisions, 3+ Skill Chains, or Roster Review → Full-Roster Orthogonality Audit**
   - Read `references/procedures/reflect.md` (§2) and `references/skill-modification/modification-guide.md`. Audit all opted-in skills for the smallest non-overlapping set.
3. **Unmatched Repeatable Task → Trusted Discovery or Skill Creation**
   - Read `references/procedures/discover.md` (`config/trusted-sources.json` + `scripts/lint_skills.py`) or `references/skill-creation/authoring-guide.md`.
4. **Onboarding & Consent → Init**
   - Read `references/procedures/init.md` (`scripts/lint_skills.py`, Opt-In / Ignore / Ask Later).
5. **Rollback or Removal → Revert / Uninstall**
   - Read `references/procedures/revert.md` (`artifacts/snapshots/`, block stripping).
6. **Contribute Upstream → Export PR Diff**
   - Read `references/procedures/export.md` (`scripts/export_diff.py`).

## Host Guides & Invariants

- **Hosts:** Read `vendors/gemini-web.md`, `vendors/claude-code.md`, or `vendors/codex.md`.
- **Invariants:** Follow `references/skill-modification/modification-guide.md` (`the-one-skill:opt-in`, snapshots, diff approval, `SKILL.md <= 800` tokens).
