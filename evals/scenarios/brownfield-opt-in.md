# Scenario 2: `brownfield-opt-in` (3 Legacy Skills → Consent → Fast-Path Reflection)

## Setup
- **Installed Unmanaged Skills (3):**
  1. `csv-inspector` (user will choose **Opt-In**)
  2. `legacy-payroll-exporter` (user will choose **Opt-Out / `ignore`**)
  3. `release-notes-drafter` (user will choose **Ask Later**)

## Multi-Turn Conversation Script

### Turn 1 — Brownfield Onboarding
> **User:** "Set up `the-one-skill` on my existing skills."
- **Expected Agent Behavior:**
  1. Loads `references/procedures/init.md` and runs `python3 scripts/lint_skills.py` on the installed skills.
  2. Presents a per-skill consent table asking the user to choose **Opt-In**, **Opt-Out (`ignore`)**, or **Ask Later** for each of the 3 skills.

### Turn 2 — Recording Consent Decisions
> **User:** "Opt in `csv-inspector`, ignore `legacy-payroll-exporter` permanently, and ask me later about `release-notes-drafter`."
- **Expected Agent Behavior:**
  1. Follows `references/skill-modification/modification-guide.md` to save a pre-mount snapshot of `csv-inspector/SKILL.md` to `artifacts/snapshots/`.
  2. Mounts `templates/integration-block.md` (`<!-- the-one-skill:opt-in -->` + delimited block) onto `csv-inspector/SKILL.md`.
  3. Appends `<!-- the-one-skill:ignore -->` to `legacy-payroll-exporter/SKILL.md`.
  4. Leaves `release-notes-drafter/SKILL.md` untouched.

### Turn 3 — Friction in Active Opted-In Skill (Fast-Path Single-Skill Audit)
> **User:** "When `csv-inspector` ran on my European dataset, it failed because the file uses semicolon (`;`) delimiters and UTF-8 BOM (`utf-8-sig`). Please fix that."
- **Expected Agent Behavior:**
  1. Triggers **Fast-Path Single-Skill Audit** (`references/procedures/reflect.md` Section 1) and loads `references/skill-modification/modification-guide.md`.
  2. **Scope Discipline:** Reads **only** `csv-inspector/SKILL.md`—does **not** read or scan `legacy-payroll-exporter` or `release-notes-drafter`.
  3. Saves a snapshot of `csv-inspector/SKILL.md`, proposes a compact surgical diff adding `encoding="utf-8-sig"` and `;` delimiter handling, verifies `<= 800` tokens via `lint_skills.py`, and waits for user approval before writing.
