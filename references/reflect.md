# Skill Evolution & Orthogonality (`reflect`)

`the-one-skill` separates reflection into two distinct scopes so everyday friction fixes stay fast and cheap, while structural overlap gets a thorough holistic review.

---

## Decision Rule: Which Audit Should Run?

| Signal in Conversation | Scope to Run |
| :--- | :--- |
| User corrects output, agent hits a retry loop, or a tool/schema error occurs while using **1 active opted-in skill** | **Section 1: Fast-Path Single-Skill Audit** |
| **2+ skills** trigger on the same prompt, a workflow chains **3+ skills** with duplicated instructions, or user mentions overlap/confusion/bloat | **Section 2: Full-Roster Orthogonality Audit** |

> **Hard Consent Gate:** Before proposing any edit, verify the skill contains `<!-- the-one-skill:opt-in -->` and does **not** contain `<!-- the-one-skill:ignore -->`.

---

## Section 1: Fast-Path Single-Skill Audit (Default on Friction)

**Goal:** Fix the immediate defect in the active skill with minimal token overhead and zero cross-roster scanning.

1. **Scope Lock:** Read **only** the currently active skill's `SKILL.md` (and its specific `references/` file if the defect lives there). Do **not** scan other skills in the roster.
2. **Diagnose Root Cause:**
   - *Missing edge-case rule or command flag?* Add a concise 1–2 line rule.
   - *Ambiguous instruction causing retries?* Replace vague prose with a deterministic step or `scripts/` invocation.
   - *Approaching or exceeding 800 tokens?* Extract detailed examples, schemas, or long checklists into `<skill>/references/<topic>.md` and link to it from `SKILL.md`.
3. **Snapshot & Lint:**
   - Save the current version to `artifacts/snapshots/<skill-name>.<timestamp>.bak.md`.
   - Validate the proposed replacement with `python3 scripts/lint_skills.py <skill_dir>` to confirm `SKILL.md <= 800` tokens and valid sections.
4. **Diff-First Approval:** Show a compact unified diff and a one-sentence explanation of why the change prevents repeat friction. Apply only after user confirmation.

---

## Section 2: Full-Roster Orthogonality Audit

**Goal:** Ensure work across the skill library is divided into the **smallest necessary number of non-overlapping skills**, each under 800 tokens with crisp trigger boundaries.

1. **Gather Opted-In Roster:**
   - Run `python3 scripts/lint_skills.py <skills_root_dir>` to get token counts, frontmatter summaries, and pairwise keyword/trigger overlap scores across all opted-in skills (skipping any skill marked `<!-- the-one-skill:ignore -->`).
2. **Evaluate Against Three Orthogonality Rules:**
   - **Rule A — Merge Redundant Skills:** If two skills share `>= 0.35` trigger Jaccard similarity (or `>= 4` core trigger keywords) and serve the same workflow, propose merging them into one skill with domain details in `references/`.
   - **Rule B — Sharpen Mutual Exclusions:** If two skills are legitimately distinct but triggered together on the same prompt, tighten each skill's `"Use when"` and `"Do not use when"` bullets so each explicitly defers the other's domain (e.g., *"Do not use when inspecting CSV schemas; use `csv-inspector` instead"*).
   - **Rule C — Split Overloaded Monoliths:** If a single skill exceeds 800 tokens even after moving reference material to `references/`, or covers unrelated domains that never co-occur, propose splitting it into focused orthogonal skills.
3. **Present Roster Audit Plan:**
   - Output a concise table of findings (`Keep`, `Sharpen Boundary`, `Merge`, `Split`, `Move Bloat to references/`).
   - Snapshot every target skill before editing, present diffs per skill, and re-run `python3 scripts/lint_skills.py` to confirm zero overlaps and `<= 800` tokens across the roster.
