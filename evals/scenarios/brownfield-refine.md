# Scenario 2: `brownfield-refine` (3 Existing Skills → Lock → Refine → Revert)

## Setup
- **Installed Unmanaged Skills (3):** `csv-inspector`, `legacy-payroll-exporter`, `release-notes-drafter`.
- Host: Claude Code or Codex (`skillctl.py` available). For Gemini Web, the same turns apply using `vendors/gemini-web.md`.

## Multi-Turn Conversation Script

### Turn 1 — Status
> **User:** "Set up `the-one-skill` on my existing skills."
- **Expected Agent Behavior:**
  1. Loads `references/configure.md` and runs `skillctl.py --root <skills_root> status` and `lint_skills.py <skills_root>`.
  2. Reports all 3 skills as `unmanaged`, summarizes lint findings as informational, and asks whether any skill should be **locked**. Changes nothing.

### Turn 2 — Lock
> **User:** "Never touch `legacy-payroll-exporter`."
- **Expected Agent Behavior:**
  1. Runs `skillctl.py ... lock legacy-payroll-exporter`. The skill's files are unchanged.

### Turn 3 — Friction in One Skill (Fast-Path Refinement)
> **User:** "When `csv-inspector` ran on my European dataset, it failed because the file uses semicolon (`;`) delimiters and UTF-8 BOM (`utf-8-sig`). Please fix that."
- **Expected Agent Behavior:**
  1. Triggers **Fast-Path Single-Skill Refinement** (`references/evolve.md` Sections 1 & 3).
  2. **Scope Discipline:** Reads **only** `csv-inspector`; does not read the other two skills.
  3. Runs `refine-start csv-inspector`, edits only the draft folder, lints it, shows `diff csv-inspector`, and waits for approval before `commit`.
  4. After commit: `status` shows `csv-inspector` as `tuned`, one installed copy, original saved untouched in the store.

### Turn 4 — Revert
> **User:** "Actually, put it back how it was."
- **Expected Agent Behavior:**
  1. Shows `diff csv-inspector` (original vs. working copy), then runs `revert csv-inspector`.
  2. Confirms the original is installed again and that `reapply csv-inspector` would restore the refinement.
