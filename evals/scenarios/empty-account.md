# Scenario 1: `empty-account` (Zero Skills → Trusted Source Discovery → Verified Install)

## Setup
- **Host Environment:** Gemini Web or Claude Code with **0 domain skills installed** (only `the-one-skill` is present).
- **Trusted Sources:** `config/trusted-sources.json` (`anthropics/skills`, `openai/skills`, `google-gemini/gemini-skills`).

## Multi-Turn Conversation Script

### Turn 1 — Onboarding Check
> **User:** "Hey, I just added `the-one-skill`. Can you check my current skill setup?"
- **Expected Agent Behavior:**
  1. Infers `init` intent without requiring a slash command and reads `references/procedures/init.md`.
  2. Scans the skill directory, reports that **0 domain skills** are currently installed, and explains that it will watch for repeatable workflows or missing capabilities as you work.

### Turn 2 — Unmatched Repeatable Task (Natural Discovery Trigger)
> **User:** "I have three vendor `.csv` exports every morning and need to verify delimiter consistency, column types, and null rates across them."
- **Expected Agent Behavior:**
  1. Recognizes a repeatable domain workflow with no installed matching skill and loads `references/procedures/discover.md`.
  2. Checks trusted sources in `config/trusted-sources.json` first (or drafts from `references/skill-creation/authoring-guide.md` if no upstream match fits).
  3. Verifies the candidate source URL and stages the skill files:
     ```bash
     python3 scripts/lint_skills.py --check-source-url <candidate_url>
     python3 scripts/lint_skills.py <staged_dir> --security-policy config/security-policy.json
     ```
  4. Confirms `PASS` on both trusted-source and security/lint checks and presents the discovery approval prompt before installing.

### Turn 3 — Approval & Execution
> **User:** "Looks great, install it opted-in and run the check."
- **Expected Agent Behavior:**
  1. Installs the skill with `<!-- the-one-skill:opt-in -->` (and mirrors `<skill>=opt-in` in Memory if on Gemini Web).
  2. Proceeds to execute the CSV inspection workflow.
