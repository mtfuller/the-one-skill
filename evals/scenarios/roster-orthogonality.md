# Scenario 3: `roster-orthogonality` (Trigger Collision → Full-Roster Audit → Boundary/Merge Fix)

## Setup
- **Installed Opted-In Skills:**
  - `sql-query-optimizer` and `postgres-query-tuner` (from `evals/fixtures/overlap-pair/`), plus `csv-inspector`.

## Multi-Turn Conversation Script

### Turn 1 — Simultaneous Trigger Collision
> **User:** "Here is my slow PostgreSQL `EXPLAIN ANALYZE` output—why did both `sql-query-optimizer` and `postgres-query-tuner` try to handle this? My skill list feels overlapping."
- **Expected Agent Behavior:**
  1. Recognizes both a 2-skill trigger collision and an explicit overlap complaint, routing to **Full-Roster Orthogonality Audit** (`references/reflect.md` Section 2).
  2. Runs `python3 scripts/lint_skills.py` across the opted-in roster.
  3. Reports the deterministic overlap finding between `sql-query-optimizer` and `postgres-query-tuner` (`Jaccard >= 0.35`, shared keywords `['analyze', 'b-tree', 'explain', 'index', 'indexes', 'postgresql', 'queries', 'query', 'scan', 'sequential', 'slow', 'sql']`) while confirming `csv-inspector` is orthogonal (`0` overlap).
  4. Proposes consolidating the two redundant PostgreSQL query skills into a single `<800`-token `postgres-query-optimizer` skill (with detailed index heuristics moved to `references/indexing-guide.md`) or sharpening their `"Use when"` / `"Do not use when"` boundaries if the user wants one for general ANSI SQL and one for Postgres internals.

### Turn 2 — Approval & Verification
> **User:** "Merge them into `sql-query-optimizer` under the 800-token cap and remove the duplicate."
- **Expected Agent Behavior:**
  1. Saves snapshots of both skills to `artifacts/snapshots/`.
  2. Presents the unified diff for the merged `sql-query-optimizer/SKILL.md`, runs `python3 scripts/lint_skills.py` to prove `<= 800` tokens and `0` remaining roster overlaps, and applies after confirmation.
