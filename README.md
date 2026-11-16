# `the-one-skill`

> **One skill to discover, evolve, and tailor them all.**
>
> License: MIT · Targets: **Gemini Web**, **Claude Code**, **OpenAI Codex**

`the-one-skill` is a personal-first, open-source skill manager and control plane that runs inside your existing AI hosts without requiring a custom runtime or background daemon. Using standard Agent Skills files (`SKILL.md`, `references/`, `scripts/`, `artifacts/`), it helps you **discover**, **evolve**, and **tailor** your skill library safely over time.

---

## Core Design Principles

1. **Explicit Consent & Clean Reversibility:** `the-one-skill` never modifies an existing skill without an explicit opt-in/opt-out decision. Decisions live directly on each skill (`<!-- the-one-skill:opt-in -->` or `<!-- the-one-skill:ignore -->`) and are mirrored in Memory on Gemini Web to avoid redundant reads. Every edit requires diff-first approval and saves a pre-patch snapshot (`artifacts/snapshots/`) for one-step revert or clean uninstall.
2. **Progressive Disclosure & 800-Token Discipline:** Every `SKILL.md` is strictly capped at **800 tokens**, and every YAML frontmatter `description:` explicitly declares both `Use when ...` and `Do not use when ...` routing triggers. Detailed guides live in organized subfolders under `references/` (`procedures/`, `skill-creation/`, `skill-modification/`), deterministic checks live in `scripts/`, and generated outputs go to `artifacts/`.
3. **Trusted Skill Sources (No Fragile Hash Registry Maintenance):** Discovery searches verified official upstream catalogs defined in `config/trusted-sources.json` (`anthropics/skills`, `openai/skills`, `google-gemini/gemini-skills`), then validates staged files with `scripts/lint_skills.py` and `config/security-policy.json` before installation—or drafts custom skills from `templates/skill-template.md`.
4. **Pure Python 3 Standard Library Scripts:** Because Gemini Web only executes Python in its sandbox (and has no outbound VM internet), all scripts in `scripts/` use **pure Python 3 standard library** so they run identically across Gemini Web, Claude Code, and OpenAI Codex.
5. **Two-Tier Reflection (Fast-Path vs. Full-Roster Orthogonality):**
   - **Fast-Path Single-Skill Audit (Default on Friction):** When you correct the agent, hit a retry loop, or encounter a schema/tool error while using one opted-in skill, `the-one-skill` scopes strictly to **only that active skill** and proposes a compact, surgical diff.
   - **Full-Roster Orthogonality Audit:** When 2+ skills trigger on the same prompt, a workflow spans 3+ skills, or you ask for a roster review, `the-one-skill` audits all opted-in skills so work is divided across the **smallest necessary number of non-overlapping skills**—splitting bloated monoliths and merging or sharpening `"Use when / Do not use when"` boundaries.

---

## Quickstart

### 1. Install `the-one-skill`
- **Gemini Web:** Upload the `the-one-skill` folder as a custom skill. Uploaded skills persist across sessions and can be updated in place.
- **Claude Code:** Clone into `.claude/skills/the-one-skill` (workspace) or `~/.claude/skills/the-one-skill` (global).
- **OpenAI Codex:** Clone into `.codex/skills/the-one-skill` (workspace) or `~/.codex/skills/the-one-skill` (global).

### 2. Talk Naturally (No Rigid `/` Commands Required)
`the-one-skill` infers intent from conversation context while also supporting optional `/init`, `/discover`, `/reflect`, `/revert`, `/uninstall`, and `/export` shortcuts:

| Natural Prompt or Signal | Intent Routed | Reference Loaded |
| :--- | :--- | :--- |
| *"Set up `the-one-skill` on my skills"* or `/init` | Onboarding, overlap scan, per-skill Opt-In / Ignore prompt | `references/procedures/init.md` |
| Correction, retry loop, or error in 1 active opted-in skill | **Fast-Path Single-Skill Audit** (reads only the active skill) | `references/procedures/reflect.md` (§1) + `references/skill-modification/modification-guide.md` |
| 2+ skills fire together, 3+ skill chain, or *"audit my skill overlaps"* | **Full-Roster Orthogonality Audit** | `references/procedures/reflect.md` (§2) + `references/skill-modification/modification-guide.md` |
| Repeatable unmatched task or *"find/create a skill for CSVs"* | Trusted source lookup (`config/trusted-sources.json`) or custom skill creation | `references/procedures/discover.md` + `references/skill-creation/authoring-guide.md` |
| *"Undo that last skill edit"* or *"remove `the-one-skill` blocks"* | Snapshot restore (`revert`) or clean block stripping (`uninstall`) | `references/procedures/revert.md` |
| *"Export my local skill improvements for a PR"* | Sanitized unified diff + PR summary via `export_diff.py` | `references/procedures/export.md` |

---

## Deterministic CLI Utilities (Pure Python 3 Stdlib)

All scripts run with zero third-party packages:

```bash
# 1. Lint skills for the 800-token cap, explicit frontmatter Use when / Do not use when,
#    trigger keyword overlaps, and security-policy.json traps:
python3 scripts/lint_skills.py --verify-repo

# 2. Verify whether a candidate skill URL comes from a trusted upstream source:
python3 scripts/lint_skills.py --check-source-url https://github.com/anthropics/skills/tree/main/skills/pdf

# 3. Export a sanitized unified diff and PR summary against upstream:
python3 scripts/export_diff.py <upstream_dir> <local_dir> artifacts/the-one-skill-changes.patch

# 4. Run the full deterministic unit & round-trip lifecycle test suite:
python3 scripts/test_lifecycle.py
```

