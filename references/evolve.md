# Evolve: Fast-Path Reflection, Roster Orthogonality & Safe Modification (`references/evolve.md`)

Use this reference whenever improving existing opted-in skills—either to fix friction in one active skill or to resolve overlap/bloat across the skill roster.

---

## Decision Rule: Which Audit Should Run?

| Signal in Conversation | Scope to Run |
| :--- | :--- |
| User corrects output, agent hits a retry loop, or a tool/schema error occurs while using **1 active opted-in skill** | **Section 1: Fast-Path Single-Skill Audit** |
| **2+ skills** trigger on the same prompt, a workflow chains **3+ skills** with duplicated instructions, or user mentions overlap/confusion/bloat | **Section 2: Full-Roster Orthogonality Audit** |

---

## Section 1: Fast-Path Single-Skill Audit (Default on Friction)

**Goal:** Fix the immediate defect in the active skill with minimal token overhead and zero cross-roster scanning.

1. **Scope Lock:** Read **only** the currently active skill's `SKILL.md` (and its specific `references/` file if the defect lives there). Do **not** scan other skills in the roster.
2. **Diagnose Root Cause:**
   - *Missing edge-case rule or flag?* Add a concise 1–2 line rule.
   - *Ambiguous instruction causing retries?* Replace vague prose with a deterministic step or `scripts/` invocation.
   - *Approaching or exceeding 800 tokens?* Move detailed examples, schemas, or checklists into `<skill>/references/<topic>.md` and link to it from `SKILL.md`.
3. **Execute Section 3 (4-Step Safe Modification Protocol)** below.

---

## Section 2: Full-Roster Orthogonality Audit

**Goal:** Divide work across the **smallest necessary number of non-overlapping skills**, each `<= 800` tokens with crisp boundaries in both frontmatter `description:` and body sections.

1. **Gather Opted-In Roster:**
   - Run `python3 scripts/lint_skills.py <skills_root_dir>` across opted-in skills (skipping any skill marked `<!-- the-one-skill:ignore -->`).
2. **Evaluate Against Three Orthogonality Rules:**
   - **Rule A — Merge Redundant Skills:** If two skills share `>= 0.35` trigger Jaccard similarity (or `>= 4` shared trigger keywords with `>= 0.20` Jaccard) and serve the same workflow, propose merging them into one skill with domain details in `references/`.
   - **Rule B — Sharpen Mutual Exclusions:** If two distinct skills triggered together on the same prompt, tighten each skill's frontmatter `description:` and `## Use when` / `## Do not use when` bullets so each explicitly defers the other's domain.
   - **Rule C — Split Overloaded Monoliths:** If a single skill exceeds 800 tokens even after moving reference material to `references/`, or covers unrelated domains that never co-occur, propose splitting it into focused orthogonal skills.
3. **Present Roster Audit Plan:**
   - Output a concise table of findings (`Keep`, `Sharpen Boundary`, `Merge`, `Split`, `Move Bloat to references/`), then apply approved changes using **Section 3**.

---

## Section 3: Mandatory 4-Step Safe Modification Protocol

Every edit to an existing skill must follow these four steps in order:

1. **Hard Consent Check:** Verify the skill contains `<!-- the-one-skill:opt-in -->` and does **not** contain `<!-- the-one-skill:ignore -->`. If locked with `ignore`, stop immediately.
2. **Save Pre-Patch Snapshot:** Copy the current `SKILL.md` to `artifacts/snapshots/<skill-name>.<YYYYMMDDTHHMMSSZ>.bak.md`.
3. **Enforce 800-Token Cap & Lint Gate:** Run `python3 scripts/lint_skills.py <skill_dir>` and confirm `PASS` (`tokens <= 800`, explicit `Use when` / `Do not use when` in frontmatter `description:` and body sections, balanced delimiters, zero security findings).
4. **Diff-First Approval:** Show the snapshot path, token delta, and unified diff (`--- a/SKILL.md` / `+++ b/SKILL.md`), and write changes **only** after user confirmation.
