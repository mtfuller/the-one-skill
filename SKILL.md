---
name: the-one-skill
description: Personal-first skill manager and control plane to discover, evolve, audit, and tailor Agent Skills across Gemini Web, Claude Code, and OpenAI Codex.
---

# `the-one-skill` — Control Plane

> **One skill to discover, evolve, and tailor them all.**

Manage your skill library safely using standard Agent Skills files (`SKILL.md`, `references/`, `scripts/`, `artifacts/`). Load only the reference file needed for the active intent.

## Use when

- Onboarding or auditing an existing skill library (`init`, opt-in or ignore consent).
- Friction, user corrections, or retry loops occur in an opted-in skill (**Fast-Path Single-Skill Audit**).
- Multiple skills trigger on one prompt, a workflow spans 3+ skills, or the user mentions overlap or bloat (**Full-Roster Orthogonality Audit**).
- A task has no matching skill or repeats across sessions (`discover`).
- Rolling back a skill edit, stripping integration blocks, or exporting local diffs for PRs (`revert`, `uninstall`, `export`).

## Do not use when

- Executing a normal domain task covered cleanly by a single skill with zero friction.
- Modifying any skill locked with `the-one-skill:ignore` (unless asked to change its consent state).

## Intent Routing (Load Reference on Demand)

Infer intent naturally from conversation (or optional `/init`, `/discover`, `/reflect`, `/revert`, `/uninstall`, `/export` shortcuts):

1. **Friction in 1 Opted-In Skill → Fast-Path Single-Skill Audit**
   - Read `references/reflect.md` (§1). Inspect **only that active skill**; propose a surgical diff or move detail to `references/`. Never scan other skills.
2. **Trigger Collisions, 3+ Skill Chains, or Roster Review → Full-Roster Orthogonality Audit**
   - Read `references/reflect.md` (§2). Audit all opted-in skills for the smallest necessary non-overlapping set; split monoliths and merge or sharpen `"Do not use when"` boundaries.
3. **Unmatched Repeatable Task → Verified Discovery**
   - Read `references/discover.md`. Check `registry.json` first, stage files, require `python3 scripts/verify_hash.py <staged_dir> <expected_sha256>` (`PASS`), scan `config/security-policy.json`, or draft from `templates/skill-template.md`.
4. **Onboarding & Consent → Init**
   - Read `references/init.md`. Run `python3 scripts/lint_skills.py`, prompt per skill (**Opt-In**, **Ignore**, **Ask Later**), and mount `templates/integration-block.md` on opted-in skills.
5. **Rollback or Removal → Revert / Uninstall**
   - Read `references/revert.md`. Save snapshots to `artifacts/snapshots/`, restore backups, or strip integration blocks to vanilla.
6. **Contribute Upstream → Export PR Diff**
   - Read `references/export.md` and run `python3 scripts/export_diff.py`.

## Host Guides & Invariants

- **Hosts:** Read `vendors/gemini-web.md`, `vendors/claude-code.md`, or `vendors/codex.md`.
- **Invariants:** Require `the-one-skill:opt-in` consent, pre-patch snapshots, diff approval, `verify_hash.py` `PASS`, and `SKILL.md <= 800` tokens.
