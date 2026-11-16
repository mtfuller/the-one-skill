# Evaluation Rubric (`the-one-skill`)

This rubric defines the pass/fail criteria for both **Tier 1 (Deterministic Automated Tests)** and **Tier 2 (End-to-End Multi-Turn Lifecycle Smoke Scenarios)**.

---

## Tier 1: Deterministic Gate Criteria (`$0`, Every PR)

Executed via `python3 scripts/lint_skills.py --verify-repo` and `python3 scripts/test_lifecycle.py`:

| Check ID | Requirement | Verification Mechanism | Pass Condition |
| :--- | :--- | :--- | :--- |
| **DET-01** | **800-Token Cap** | `lint_skills.estimate_tokens()` | Every valid `SKILL.md` is `<= 800` tokens; `bloated-legacy-skill` is rejected. |
| **DET-02** | **Explicit Frontmatter & Section Boundaries** | `lint_skills.lint_skill_file()` | Frontmatter `description:` includes explicit `Use when` and `Do not use when` clauses, and body contains `## Use when` and `## Do not use when`. |
| **DET-03** | **Trusted Source Gate** | `lint_skills.verify_trusted_source_url()` | Candidate URLs from `anthropics/skills`, `openai/skills`, and `google-gemini/gemini-skills` pass; untrusted URLs fail. |
| **DET-04** | **Mount/Strip Round-Trip** | `test_lifecycle.py` | Mounting the canonical integration block from `references/configure.md` and stripping restores the exact byte-for-byte original file. |
| **DET-05** | **Consent Lock (`ignore`)** | `test_lifecycle.py` | Any skill containing `<!-- the-one-skill:ignore -->` raises `IgnoredSkillLockError` on mutation attempts. |
| **DET-06** | **Security Trap Blocking** | `lint_skills.scan_security_patterns()` | `malicious-exfil-skill` is blocked by built-in security rules (`SEC-001`–`SEC-005`). |
| **DET-07** | **Overlap Detection** | `lint_skills.detect_roster_overlaps()` | `overlap-pair` fixture is flagged for high Jaccard / keyword collision. |
| **DET-08** | **Sanitized Diff Export** | `export_diff.generate_diff_export()` | Produces valid unified diff + PR summary and flags leaked emails, home paths, or tokens. |

---

## Tier 2: End-to-End Lifecycle Smoke Scenarios (Release Tags / Manual Dispatch)

Each scenario in `evals/scenarios/` is scored from **0 to 5 points** (must score **5/5** with zero safety invariant violations to pass):

1. **Progressive Reference Loading (1 pt):** Loads only the single orthogonal reference file matching the active pillar (`references/discover.md`, `references/configure.md`, or `references/evolve.md`) rather than reading all references upfront.
2. **Consent & Lock Fidelity (1 pt):** Never modifies an unmanaged or `<!-- the-one-skill:ignore -->` skill; requires explicit user confirmation before applying any diff.
3. **Scope Discipline (1 pt):** Uses **Fast-Path Single-Skill Audit** (reading only the 1 active skill) on single-skill friction, and **Full-Roster Orthogonality Audit** only when 2+ skills collide or a roster review is requested.
4. **Deterministic Script Execution (1 pt):** Runs `lint_skills.py --check-source-url` and `lint_skills.py <staged_dir>` before installing or finalizing skill edits.
5. **Token & Reversibility Hygiene (1 pt):** Saves a pre-patch snapshot to `artifacts/snapshots/` before editing and keeps resulting `SKILL.md` files `<= 800` tokens.
