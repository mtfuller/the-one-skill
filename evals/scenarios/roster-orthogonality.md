# Scenario 3: `roster-orthogonality` (Trigger Collision → Full-Roster Audit → Boundary/Merge Fix)

## Setup
- **Installed Skills:**
  - `sql-query-optimizer` and `postgres-query-tuner` (from `evals/fixtures/overlap-pair/`), plus `csv-inspector`.

## Multi-Turn Conversation Script

### Turn 1 — Simultaneous Trigger Collision
> **User:** "Here is my slow PostgreSQL `EXPLAIN ANALYZE` output—why did both `sql-query-optimizer` and `postgres-query-tuner` try to handle this? My skill list feels overlapping."
- **Expected Agent Behavior:**
  1. Recognizes both a 2-skill trigger collision and an explicit overlap complaint, routing to **Full-Roster Orthogonality Audit** (`references/evolve.md` Section 2 & Section 3).
  2. Runs `skillctl.py ... status` and `python3 scripts/lint_skills.py <skills_root>` across the roster.
  3. Reports the deterministic overlap finding between `sql-query-optimizer` and `postgres-query-tuner` (`Jaccard >= 0.35`) while confirming `csv-inspector` is orthogonal (`0` overlap).
  4. Proposes consolidating the two redundant PostgreSQL query skills into a single `<800`-token `postgres-query-optimizer` skill (with detailed index heuristics moved to `references/indexing-guide.md`) or sharpening their frontmatter `description:` and `"Use when"` / `"Do not use when"` boundaries.

### Turn 2 — Approval & Verification
> **User:** "Merge them into one skill under the 800-token cap."
- **Expected Agent Behavior:**
  1. Stages the merged skill outside the skills root under a new name (e.g. `sql-query-tuning`), since originals are never edited.
  2. Shows the diff against both originals, runs `python3 scripts/lint_skills.py <skills_root> <staged_dir>` to prove `<= 800` tokens, and after confirmation runs `skillctl.py ... install <staged_dir> --replaces sql-query-optimizer postgres-query-tuner`.
  3. Confirms `status` shows both originals `retired` (replaced by the merged skill) and that `revert sql-query-tuning` restores them exactly.
