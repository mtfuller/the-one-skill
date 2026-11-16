---
name: the-one-skill
description: Personal-first skill manager for Gemini Web, Claude Code, and OpenAI Codex. Use when discovering or creating a missing skill, configuring skill consent/rollbacks/exports, fixing friction or retries in an opted-in skill, or auditing roster overlap when multiple skills trigger together. Do not use when executing a normal domain task covered cleanly by one skill with zero friction, or to modify any skill marked with the-one-skill:ignore.
---

# `the-one-skill` — Control Plane

> **One skill to discover, evolve, and tailor them all.**

Manage your skill library using standard Agent Skills files (`SKILL.md`, `references/`, `scripts/`, `artifacts/`). Load **only the single reference file** matching the active pillar (`discover`, `configure`, or `evolve`).

## Use when

- A task has no matching skill or repeats across sessions (**Discover**).
- Onboarding skills, setting opt-in/ignore consent, reverting edits, stripping blocks, or exporting PR diffs (**Configure**).
- Friction, corrections, or retries occur in 1 active opted-in skill (**Evolve — Fast-Path Single-Skill Audit**).
- 2+ skills trigger together, a workflow chains 3+ skills, or overlap/bloat is reported (**Evolve — Full-Roster Orthogonality Audit**).

## Do not use when

- Executing a normal domain task covered cleanly by one skill with zero friction.
- Modifying any skill locked with `the-one-skill:ignore` (unless asked to change its consent).

## Three Orthogonal Pillars (Load 1 Reference on Demand)

Infer intent naturally from context (or optional `/discover`, `/configure`, `/evolve`, `/init`, `/reflect`, `/revert`, `/uninstall`, `/export` shortcuts):

1. **Discover (`references/discover.md`) — Add Missing Capabilities**
   - Search trusted catalogs (`anthropics/skills`, `openai/skills`, `google-gemini/gemini-skills`), verify with `python3 scripts/lint_skills.py --check-source-url <url>` and `python3 scripts/lint_skills.py <staged_dir>`, or scaffold a custom skill from the canonical template.
2. **Configure (`references/configure.md`) — Consent, Rollback & Export**
   - Onboard skills (`init`: **Opt-In**, **Ignore**, **Ask Later**), mount or strip the integration block (`uninstall`), restore backups from `artifacts/snapshots/` (`revert`), or export sanitized PR patches via `python3 scripts/export_diff.py` (`export`).
3. **Evolve (`references/evolve.md`) — Fix Friction & Enforce Orthogonality**
   - **§1 Fast-Path Single-Skill Audit (Default on Friction):** Inspect **only that active opted-in skill** and propose a surgical diff. Never scan other skills.
   - **§2 Full-Roster Orthogonality Audit (On Overlap / Bloat):** Audit all opted-in skills for the smallest non-overlapping set; merge duplicates, sharpen boundaries, or split monoliths.
   - **§3 Safe Modification Protocol:** Require `the-one-skill:opt-in`, pre-patch snapshots, `lint_skills.py` (`<= 800` tokens), and diff approval.

## Host Adapters

Read `vendors/gemini-web.md`, `vendors/claude-code.md`, or `vendors/codex.md` for host-specific paths and persistence.
