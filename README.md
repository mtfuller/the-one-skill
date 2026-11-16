# `the-one-skill`

> **One skill to discover, evolve, and tailor them all.**
>
> License: MIT · Targets: **Gemini Web**, **Claude Code**, **OpenAI Codex**

`the-one-skill` is a personal-first, open-source skill manager and control plane that runs inside your existing AI hosts without requiring a custom runtime or background daemon. Using standard Agent Skills files (`SKILL.md`, `references/`, `scripts/`, `artifacts/`), it helps you **discover**, **evolve**, and **tailor** your skill library safely over time.

---

## Core Design Principles

1. **Explicit Consent & Clean Reversibility:** `the-one-skill` never modifies an existing skill without an explicit opt-in/opt-out decision. Decisions live directly on each skill (`<!-- the-one-skill:opt-in -->` or `<!-- the-one-skill:ignore -->`) and are mirrored in Memory on Gemini Web to avoid redundant reads. Every edit requires diff-first approval and saves a pre-patch snapshot (`artifacts/snapshots/`) for one-step revert or clean uninstall.
2. **Progressive Disclosure & 800-Token Discipline:** Every `SKILL.md` is strictly capped at **800 tokens**. Detailed guides, rubrics, and checklists live in `references/` (loaded only when needed), deterministic checks live in `scripts/`, and generated outputs go to `artifacts/`.
3. **Pure Python 3 Standard Library Scripts:** Because Gemini Web only executes Python in its sandbox (and has no outbound VM internet), all scripts in `scripts/` use **pure Python 3 standard library** so they run identically across Gemini Web, Claude Code, and OpenAI Codex.
4. **Two-Tier Reflection (Fast-Path vs. Full-Roster Orthogonality):**
   - **Fast-Path Single-Skill Audit (Default on Friction):** When you correct the agent, hit a retry loop, or encounter a schema/tool error while using one opted-in skill, `the-one-skill` scopes strictly to **only that active skill** and proposes a compact, surgical diff.
   - **Full-Roster Orthogonality Audit:** When 2+ skills trigger on the same prompt, a workflow spans 3+ skills, or you ask for a roster review, `the-one-skill` audits all opted-in skills so work is divided across the **smallest necessary number of non-overlapping skills**—splitting bloated monoliths and merging or sharpening `"Use when / Do not use when"` boundaries.

---

## Quickstart

### 1. Install `the-one-skill`
- **Gemini Web:** Upload the `the-one-skill` folder (or `SKILL.md` + `references/`, `scripts/`, `config/`, `templates/`, `vendors/`, `registry.json`) as a custom skill. Uploaded skills persist across sessions and can be updated in place.
- **Claude Code:** Clone into `.claude/skills/the-one-skill` (workspace) or `~/.claude/skills/the-one-skill` (global).
- **OpenAI Codex:** Clone into `.codex/skills/the-one-skill` (workspace) or `~/.codex/skills/the-one-skill` (global).

### 2. Talk Naturally (No Rigid `/` Commands Required)
`the-one-skill` infers intent from conversation context while also supporting optional `/init`, `/discover`, `/reflect`, `/revert`, `/uninstall`, and `/export` shortcuts:

| Natural Prompt or Signal | Intent Routed | Reference Loaded |
| :--- | :--- | :--- |
| *"Set up `the-one-skill` on my skills"* or `/init` | Onboarding, overlap scan, per-skill Opt-In / Ignore prompt | `references/init.md` |
| Correction, retry loop, or error in 1 active opted-in skill | **Fast-Path Single-Skill Audit** (reads only the active skill) | `references/reflect.md` (§1) |
| 2+ skills fire together, 3+ skill chain, or *"audit my skill overlaps"* | **Full-Roster Orthogonality Audit** | `references/reflect.md` (§2) |
| Repeatable unmatched task or *"find/create a skill for CSVs"* | Verified lookup in `registry.json` (`verify_hash.py` gate) or template draft | `references/discover.md` |
| *"Undo that last skill edit"* or *"remove `the-one-skill` blocks"* | Snapshot restore (`revert`) or clean block stripping (`uninstall`) | `references/revert.md` |
| *"Export my local skill improvements for a PR"* | Sanitized unified diff + PR summary via `export_diff.py` | `references/export.md` |

---

## Deterministic CLI Utilities (Pure Python 3 Stdlib)

All scripts run with zero third-party packages:

```bash
# 1. Lint skills for the 800-token cap, YAML frontmatter, boundary sections,
#    trigger keyword overlaps, and security-policy.json traps:
python3 scripts/lint_skills.py --verify-repo

# 2. Compute or verify canonical cross-platform SHA-256 hash for a staged skill:
python3 scripts/verify_hash.py <staged_dir> <expected_sha256>
python3 scripts/verify_hash.py --compute <staged_dir>

# 3. Export a sanitized unified diff and PR summary against upstream:
python3 scripts/export_diff.py <upstream_dir> <local_dir> artifacts/the-one-skill-changes.patch

# 4. Run the full deterministic unit & round-trip lifecycle test suite:
python3 scripts/test_lifecycle.py
```

---

## Repository Structure

```text
the-one-skill/
├── README.md                          # Pitch, quickstart, and natural-intent overview
├── SKILL.md                           # Entry point (<800 tokens), intent routing, safety invariants
├── registry.json                      # Commit-pinned, SHA-256-verified skill index
├── references/
│   ├── init.md                        # Onboarding, opt-in/opt-out prompts, delimited mounting
│   ├── revert.md                      # Snapshot restore, block stripping, ignore markers
│   ├── reflect.md                     # Single-skill fast fix vs. full-roster orthogonality audit
│   ├── discover.md                    # Registry-first lookup, verify_hash.py gate, security scan
│   └── export.md                      # Local state export & unified diff generation for PRs
├── scripts/
│   ├── verify_hash.py                 # Pure Python stdlib SHA-256 verifier for staged skills
│   ├── lint_skills.py                 # Deterministic token cap, frontmatter, & trigger-overlap linter
│   ├── export_diff.py                 # Unified diff & PR summary generator vs. upstream
│   └── test_lifecycle.py              # Deterministic unit/round-trip tests (mount/unmount/ignore)
├── templates/
│   ├── skill-template.md              # Standard skill template (references/, scripts/, artifacts/)
│   └── integration-block.md           # Delimited adapter block for opted-in existing skills
├── config/
│   ├── contract.json                  # Integration contract version, delimiters, ignore markers
│   └── security-policy.json           # Capability tiers & banned exfiltration patterns
├── vendors/
│   ├── gemini-web.md                  # Persistent skills, Python-only scripts, no VM internet, Memory state
│   ├── claude-code.md                 # Local filesystem, MCP, CLAUDE.md conventions
│   └── codex.md                       # Codex skill paths and AGENTS.md conventions
├── evals/
│   ├── rubric.md                      # Scoring criteria for lifecycle smoke scenarios
│   ├── fixtures/                      # Verified registry skills, injection traps, overlapping pairs
│   └── scenarios/                     # 3 lightweight end-to-end lifecycle scenarios
└── .github/
    └── workflows/
        ├── test-deterministic.yml     # Runs lint_skills.py + test_lifecycle.py on every PR (free)
        ├── eval-scenarios.yml         # Runs 3 lifecycle smoke tests on release tags / manual
        └── maintain-registry.yml      # Scheduled upstream skill hash & audit checks
```
