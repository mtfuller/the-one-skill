# `the-one-skill`

> **One skill to discover, evolve, and tailor them all.**
>
> License: MIT · Targets: **Gemini Web**, **Claude Code**, **OpenAI Codex**

`the-one-skill` is a personal-first, open-source skill manager and control plane that runs inside your existing AI hosts without requiring a custom runtime or background daemon. Using standard Agent Skills files (`SKILL.md`, `references/`, `scripts/`, `artifacts/`), it helps you **discover**, **configure**, and **evolve** your skill library safely over time.

---

## Core Design Principles

1. **Three Orthogonal Pillars (`Discover`, `Configure`, `Evolve`):** Every control-plane action maps cleanly to a single reference file so the agent never loads redundant instructions:
   - **Discover (`references/discover.md`):** Search verified official catalogs (`anthropics/skills`, `openai/skills`, `google-gemini/gemini-skills`) or scaffold a custom skill from the canonical template.
   - **Configure (`references/configure.md`):** Manage onboarding consent (`opt-in` vs. `ignore`), mount or strip integration blocks (`uninstall`), restore backups (`revert`), and export sanitized PR patches (`export`).
   - **Evolve (`references/evolve.md`):** Run a **Fast-Path Single-Skill Audit** on active-skill friction or a **Full-Roster Orthogonality Audit** when 2+ skills collide, backed by snapshots and diff-first approval.
2. **Explicit Consent & Clean Reversibility:** `the-one-skill` never modifies an existing skill without `<!-- the-one-skill:opt-in -->` and never touches `<!-- the-one-skill:ignore -->`. Every edit saves a pre-patch snapshot (`artifacts/snapshots/`) and requires user diff approval.
3. **Progressive Disclosure & 800-Token Discipline:** Every `SKILL.md` is strictly capped at **800 tokens**, and every YAML frontmatter `description:` explicitly declares both `Use when ...` and `Do not use when ...` routing triggers.
4. **Pure Python 3 Standard Library Scripts:** Because Gemini Web only executes Python in its sandbox (and has no outbound VM internet), all scripts in `scripts/` use **pure Python 3 standard library** with zero external config dependencies.

---

## Quickstart

### 1. Install `the-one-skill`
- **Gemini Web:** Upload the `the-one-skill` folder as a custom skill. Uploaded skills persist across sessions and can be updated in place.
- **Claude Code:** Clone into `.claude/skills/the-one-skill` (workspace) or `~/.claude/skills/the-one-skill` (global).
- **OpenAI Codex:** Clone into `.codex/skills/the-one-skill` (workspace) or `~/.codex/skills/the-one-skill` (global).

### 2. Talk Naturally (No Rigid `/` Commands Required)
`the-one-skill` infers intent from conversation context while also supporting optional `/discover`, `/configure`, `/evolve`, `/init`, `/reflect`, `/revert`, `/uninstall`, and `/export` shortcuts:

| Pillar | Natural Prompt or Signal | Reference Loaded |
| :--- | :--- | :--- |
| **Discover** | Repeatable unmatched task or *"find/create a skill for CSVs"* | `references/discover.md` |
| **Configure** | *"Set up `the-one-skill` on my skills"*, *"undo that last skill edit"*, *"remove integration blocks"*, or *"export a PR diff"* | `references/configure.md` |
| **Evolve (§1 Fast-Path)** | Correction, retry loop, or error in 1 active opted-in skill (reads **only** that active skill) | `references/evolve.md` (§1 & §3) |
| **Evolve (§2 Full-Roster)** | 2+ skills fire together, 3+ skill chain, or *"audit my skill overlaps"* | `references/evolve.md` (§2 & §3) |

---

## Deterministic CLI Utilities (Pure Python 3 Stdlib)

All scripts are self-contained and run with zero third-party packages:

```bash
# 1. Lint skills for the 800-token cap, explicit frontmatter Use when / Do not use when,
#    trigger keyword overlaps, and built-in security traps (SEC-001..SEC-005):
python3 scripts/lint_skills.py --verify-repo

# 2. Verify whether a candidate skill URL comes from a trusted upstream source:
python3 scripts/lint_skills.py --check-source-url https://github.com/anthropics/skills/tree/main/skills/pdf

# 3. Export a sanitized unified diff and PR summary against upstream:
python3 scripts/export_diff.py <upstream_dir> <local_dir> artifacts/the-one-skill-changes.patch

# 4. Run the full deterministic unit & round-trip lifecycle test suite:
python3 scripts/test_lifecycle.py
```
