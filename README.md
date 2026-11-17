# `the-one-skill`

> **One skill to discover, evolve, and tailor them all.**
>
> License: MIT · Targets: **Gemini Web**, **Claude Code**, **OpenAI Codex**

`the-one-skill` is a personal-first, open-source skill manager and control plane that runs inside your existing AI hosts without requiring a custom runtime or background daemon. Using standard Agent Skills files (`SKILL.md`, `references/`, `scripts/`, `artifacts/`), it helps you **discover**, **configure**, and **evolve** your skill library safely over time.

---

## Core Design Principles

1. **Three Orthogonal Pillars (`Discover`, `Configure`, `Evolve`):** Every control-plane action maps cleanly to a single reference file so the agent never loads redundant instructions:
   - **Discover (`references/discover.md`):** Search verified official catalogs (`anthropics/skills`, `openai/skills`, `google-gemini/gemini-skills`) or scaffold a custom skill from the canonical template.
   - **Configure (`references/configure.md`):** Check skill status, lock skills, revert or reapply refinements, retire skills, and export sanitized PR patches (`export`).
   - **Evolve (`references/evolve.md`):** Run a **Fast-Path Single-Skill Refinement** on active-skill friction or a **Full-Roster Orthogonality Audit** when 2+ skills collide, always diff-first with user approval.
2. **Originals Are Never Edited (Swap Model):** The first refinement of a skill saves the original untouched and installs **one working copy** in its place; later refinements edit that copy. A disabled version lives outside the host's skills folder (Claude Code / Codex) or is disabled in the host (Gemini Web), so the number of installed skills never grows. **Revert** puts the original back byte-for-byte; **reapply** swaps the working copy back in; **undo** steps back one refinement. Swaps refuse to run if a skill was edited by hand outside `the-one-skill`, and locked skills are never touched. Every change requires user diff approval.
3. **Progressive Disclosure & 800-Token Discipline:** Every `SKILL.md` is strictly capped at **800 tokens**, and every YAML frontmatter `description:` explicitly declares both `Use when ...` and `Do not use when ...` routing triggers.
4. **Pure Python 3 Standard Library Scripts:** Because Gemini Web only executes Python in its sandbox (and has no outbound VM internet), all scripts in `scripts/` use **pure Python 3 standard library** with zero external config dependencies.

---

## Quickstart

### 1. Install `the-one-skill`
- **Gemini Web:** Upload the `the-one-skill` folder as a custom skill. Uploaded skills persist across sessions and can be updated in place.
- **Claude Code:** Clone into `.claude/skills/the-one-skill` (workspace) or `~/.claude/skills/the-one-skill` (global).
- **OpenAI Codex:** Clone into `.codex/skills/the-one-skill` (workspace) or `~/.codex/skills/the-one-skill` (global).

### 2. Talk Naturally (No Rigid `/` Commands Required)
`the-one-skill` infers intent from conversation context:

| Pillar | Natural Prompt or Signal | Reference Loaded |
| :--- | :--- | :--- |
| **Discover** | Repeatable unmatched task or *"find/create a skill for CSVs"* | `references/discover.md` |
| **Configure** | *"Show my skills"*, *"never touch skill X"*, *"put that skill back how it was"*, or *"export a PR diff"* | `references/configure.md` |
| **Evolve (§1 Fast-Path)** | Correction, retry loop, or error in 1 active skill (reads **only** that active skill) | `references/evolve.md` (§1 & §3) |
| **Evolve (§2 Full-Roster)** | 2+ skills fire together, 3+ skill chain, or *"audit my skill overlaps"* | `references/evolve.md` (§2 & §3) |

---

## Deterministic CLI Utilities (Pure Python 3 Stdlib)

All scripts are self-contained and run with zero third-party packages:

```bash
# 0. Manage skills with the swap model (Claude Code / Codex; see vendors/ for --root):
python3 scripts/skillctl.py --root ~/.claude/skills status
python3 scripts/skillctl.py --root ~/.claude/skills refine-start csv-inspector   # edit the printed draft
python3 scripts/skillctl.py --root ~/.claude/skills diff csv-inspector
python3 scripts/skillctl.py --root ~/.claude/skills commit csv-inspector --reason "handle ; delimiters"
python3 scripts/skillctl.py --root ~/.claude/skills revert csv-inspector          # back to the original
python3 scripts/skillctl.py --root ~/.claude/skills reapply csv-inspector         # swap the working copy back

# 1. Lint skills for the 800-token cap, explicit frontmatter Use when / Do not use when,
#    trigger keyword overlaps, and built-in security traps (SEC-001..SEC-005):
python3 scripts/lint_skills.py --verify-repo

# 2. Verify whether a candidate skill URL comes from a trusted upstream source:
python3 scripts/lint_skills.py --check-source-url https://github.com/anthropics/skills/tree/main/skills/pdf

# 3. Export a sanitized unified diff and PR summary against upstream:
python3 scripts/export_diff.py <upstream_dir> <local_dir> artifacts/the-one-skill-changes.patch

# 4. Run the full deterministic unit & swap round-trip test suite:
python3 scripts/test_lifecycle.py
```
