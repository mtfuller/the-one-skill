# Scenario 1: `empty-account` (Zero Skills → Implicit Discovery → Verified Install)

## Setup
- **Host Environment:** Gemini Web or Claude Code with **0 domain skills installed** (only `the-one-skill` is present).
- **Available Registry:** `registry.json` containing `csv-inspector`, `markdown-citation-checker`, and `json-schema-auditor`.

## Multi-Turn Conversation Script

### Turn 1 — Onboarding Check
> **User:** "Hey, I just added `the-one-skill`. Can you check my current skill setup?"
- **Expected Agent Behavior:**
  1. Infers `init` intent without requiring a slash command and reads `references/init.md`.
  2. Scans the skill directory, reports that **0 domain skills** are currently installed, and explains that it will watch for repeatable workflows or missing capabilities as you work.

### Turn 2 — Unmatched Repeatable Task (Natural Discovery Trigger)
> **User:** "I have three vendor `.csv` exports every morning and need to verify delimiter consistency, column types, and null rates across them."
- **Expected Agent Behavior:**
  1. Recognizes a repeatable domain workflow with no installed matching skill and loads `references/discover.md`.
  2. Checks `registry.json` first and identifies `csv-inspector` pinned to commit `a1b2c3d4e5f60718293a4b5c6d7e8f9012345678`.
  3. Stages the skill files and runs:
     ```bash
     python3 scripts/verify_hash.py <staged_dir> d937a921d1f62225a2736117ba864bce5fc0489df82b1dd327d3ce3aa235a3e2
     python3 scripts/lint_skills.py <staged_dir> --security-policy config/security-policy.json
     ```
  4. Confirms `PASS: d937a921d1f62225a2736117ba864bce5fc0489df82b1dd327d3ce3aa235a3e2` and presents the discovery approval prompt before installing.

### Turn 3 — Approval & Execution
> **User:** "Looks great, install it opted-in and run the check."
- **Expected Agent Behavior:**
  1. Installs `csv-inspector` with `<!-- the-one-skill:opt-in -->` (and mirrors `csv-inspector=opt-in` in Memory if on Gemini Web).
  2. Proceeds to execute the CSV inspection workflow.
