# Evolve: Fast-Path Refinement, Roster Orthogonality & Safe Refinement (`references/evolve.md`)

Use this reference whenever improving existing skills—either to fix friction in one active skill or to resolve overlap/bloat across the skill roster. Originals are never edited: every change goes into the skill's single working copy (see `references/configure.md` §0).

---

## Decision Rule: Which Audit Should Run?

| Signal in Conversation | Scope to Run |
| :--- | :--- |
| User corrects output, agent hits a retry loop, or a tool/schema error occurs while using **1 active skill** | **Section 1: Fast-Path Single-Skill Refinement** |
| **2+ skills** trigger on the same prompt, a workflow chains **3+ skills** with duplicated instructions, or user mentions overlap/confusion/bloat | **Section 2: Full-Roster Orthogonality Audit** |

---

## Section 1: Fast-Path Single-Skill Refinement (Default on Friction)

**Goal:** Fix the immediate defect in the active skill with minimal token overhead and zero cross-roster scanning.

1. **Scope Lock:** Read **only** the currently active skill's folder. Do **not** scan other skills in the roster.
2. **Diagnose Root Cause:**
   - *Missing edge-case rule or flag?* Add a concise 1–2 line rule.
   - *Ambiguous instruction causing retries?* Replace vague prose with a deterministic step or `scripts/` invocation.
   - *Approaching or exceeding 800 tokens?* Move detailed examples, schemas, or checklists into `references/<topic>.md` and link to it from `SKILL.md`.
3. **Execute Section 3** below.

---

## Section 2: Full-Roster Orthogonality Audit

**Goal:** Divide work across the **smallest necessary number of non-overlapping skills**, each `<= 800` tokens with crisp boundaries in both frontmatter `description:` and body sections.

1. **Gather the Roster:** Run `skillctl.py --root <skills_root> status` and `python3 scripts/lint_skills.py <skills_root>`. Skip locked skills.
2. **Evaluate Against Three Orthogonality Rules:**
   - **Rule A — Merge Redundant Skills:** If two skills share `>= 0.35` trigger Jaccard similarity (or `>= 4` shared trigger keywords with `>= 0.20` Jaccard) and serve the same workflow, propose merging them into one skill with domain details in `references/`.
   - **Rule B — Sharpen Mutual Exclusions:** If two distinct skills triggered together on the same prompt, refine each skill's frontmatter `description:` and `## Use when` / `## Do not use when` bullets so each explicitly defers the other's domain.
   - **Rule C — Split Overloaded Monoliths:** Only if a single skill exceeds 800 tokens even after moving reference material to `references/`, *and* covers unrelated domains that never co-occur. Prefer moving material to `references/` over splitting.
3. **Present Roster Audit Plan:** Output a concise table of findings (`Keep`, `Sharpen Boundary`, `Merge`, `Split`, `Move Bloat to references/`, `Retire`), then apply approved changes:
   - **Sharpen / move bloat:** Section 3 on each skill.
   - **Merge A + B into C:** stage C outside the skills root, lint it, show the diff against A and B, then `skillctl.py install <staged_C> --replaces A B`. `revert C` restores A and B exactly.
   - **Split A into X + Y:** `install <staged_X> --replaces A`, then `install <staged_Y>`. Reverting X restores A; retire Y separately if needed.

---

## Section 3: Safe Refinement Protocol (Every Change to an Existing Skill)

1. **Lock Check:** If `status` shows the skill as locked, stop.
2. **Start a Draft:** `skillctl.py --root <skills_root> refine-start <skill>`. On the first refinement this saves the pristine original in the store. Edit **only** the files in the printed draft folder (outside the skills root); keep the frontmatter `name:` unchanged.
3. **Lint Gate:** `python3 scripts/lint_skills.py <draft_dir>`. Security findings always block. Aim for `<= 800` tokens and explicit `Use when` / `Do not use when`; report any remaining lint errors to the user rather than silently rewriting the whole skill.
4. **Diff-First Approval:** Show `skillctl.py ... diff <skill>` (installed vs. draft, all files) plus the token delta. Run `commit <skill> --reason "<why>"` **only** after user confirmation; otherwise `abort <skill>`.
5. **Remind:** Tell the user they can `undo` (one refinement back) or `revert` (back to the original) at any time. On Codex, remind them to restart Codex.

On **Gemini Web**, follow the equivalent steps in `vendors/gemini-web.md`.
