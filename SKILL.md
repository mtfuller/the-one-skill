---
name: the-one-skill
description: Personal-first skill manager for Gemini Web, Claude Code, and OpenAI Codex. Use when discovering or creating a missing skill, refining a skill after friction or retries, reverting or reapplying a refinement, or auditing roster overlap when multiple skills trigger together. Do not use when executing a normal domain task covered cleanly by one skill with zero friction, or to change any skill the user has locked.
---

# `the-one-skill` — Control Plane

> **One skill to discover, evolve, and tailor them all.**

Manage your skill library with standard Agent Skills folders. Load **only the single reference file** matching the active pillar.

## Use when

- A task has no matching skill or repeats across sessions (**Discover**).
- Checking skill status, locking skills, reverting, reapplying, retiring, or exporting (**Configure**).
- Friction, corrections, or retries occur in one skill (**Evolve — Fast-Path**).
- 2+ skills trigger together or overlap/bloat is reported (**Evolve — Full-Roster Audit**).

## Do not use when

- Executing a normal domain task covered cleanly by one skill with zero friction.
- Changing a locked skill (unless the user asks to unlock it).

## Core Rule: Originals Are Never Edited

- The first refinement of a skill saves the original untouched and installs **one working copy** in its place; later refinements edit only that copy. Revert = put the original back; reapply = swap the copy back in.
- A disabled version is **out of the host's skills folder** (Claude Code / Codex) or **disabled in the host** (Gemini Web), never just marked.
- Every change needs a shown diff and the user's approval. If an operation is not possible, stop and ask; never substitute another action.
- Claude Code / Codex: always use `python3 scripts/skillctl.py --root <skills_root> ...`; never move or edit skill folders by hand.
- **Check before running scripts:** run `python3 scripts/lint_skills.py --self-check` once per session before any script (on Gemini Web, copy the scripts into the sandbox first; see its adapter). If no code can run (e.g. Gemini Web Chat mode), follow the no-code-execution rules in the reference you loaded and tell the user which checks were skipped.

## Three Pillars (Load 1 Reference on Demand)

1. **Discover (`references/discover.md`)** — Search trusted catalogs, check overlap with installed skills, verify with `scripts/lint_skills.py`, install with `skillctl.py install`.
2. **Configure (`references/configure.md`)** — `status`, `lock`/`unlock`, `revert`/`reapply`, `retire`/`unretire`, `accept`, `prune`, and `export`.
3. **Evolve (`references/evolve.md`)** — §1 Fast-Path refinement of one skill; §2 Full-Roster audit (sharpen, merge, split); §3 Safe Refinement Protocol.

## Host Adapters

Read `vendors/claude-code.md`, `vendors/codex.md`, or `vendors/gemini-web.md` for skill paths, how disabling works, and restart rules.
