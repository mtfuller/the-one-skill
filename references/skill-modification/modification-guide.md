# Skill Modification Guide (`references/skill-modification`)

Use this reference whenever modifying an existing skill—whether during onboarding (`init`), single-skill friction fixes (`reflect` §1), full-roster orthogonality audits (`reflect` §2), or rollback (`revert`).

---

## 1. Hard Consent Verification Gate

Before proposing or writing any modification to an existing skill:

1. **Check for Lock Marker (`ignore`):**
   - If the skill contains `<!-- the-one-skill:ignore -->` (or is marked `ignore` in Gemini Memory), **STOP immediately**. Never propose edits, mount blocks, or include it in orthogonality merges unless the user explicitly asks to unlock that specific skill.
2. **Check for Opt-In Marker (`opt-in`):**
   - During `reflect`, only modify skills containing `<!-- the-one-skill:opt-in -->`. If friction occurs in an unmanaged skill, ask the user if they want to opt it in first.

---

## 2. Mandatory 4-Step Modification Protocol

Every edit to an opted-in skill must follow these four steps in order:

### Step 1 — Save a Pre-Patch Snapshot
Copy the current `SKILL.md` before making any change:
```text
artifacts/snapshots/<skill-name>.<YYYYMMDDTHHMMSSZ>.bak.md
```

### Step 2 — Enforce the 800-Token Cap & Frontmatter Rules
- Ensure the YAML frontmatter `description:` explicitly states both `Use when ...` and `Do not use when ...`.
- If adding a new rule pushes `SKILL.md` near or above **800 tokens**, refactor bulky inline examples, tables, or edge-case notes into `<skill-dir>/references/<subtopic>.md` and replace them in `SKILL.md` with a 1-line link (`Read references/<subtopic>.md when ...`).

### Step 3 — Run Deterministic Lint & Security Checks
Validate the proposed file before showing it to the user:
```bash
python3 scripts/lint_skills.py <skill_dir> --security-policy config/security-policy.json
```
Confirm `PASS` (`tokens <= 800`, valid frontmatter, balanced `the-one-skill:start` / `the-one-skill:end` delimiters, zero security findings).

### Step 4 — Diff-First User Approval
Present to the user:
- **Snapshot Path:** `artifacts/snapshots/<skill-name>.<timestamp>.bak.md`
- **Token Delta:** e.g., `467 -> 482 / 800 tokens`
- **Unified Diff:** Clean `--- a/SKILL.md` / `+++ b/SKILL.md` block showing exact line changes.
- Apply the change **only** after the user confirms.

---

## 3. Delimiter Block Mounting & Stripping Rules

- **Mounting (`init`):** Append `templates/integration-block.md` separated by a single blank line at the bottom of `SKILL.md`. Mounting must be idempotent (never duplicate `<!-- the-one-skill:start -->` blocks).
- **Stripping (`uninstall`):** Remove `<!-- the-one-skill:opt-in -->` and `<!-- the-one-skill:start --> ... <!-- the-one-skill:end -->` cleanly, restoring trailing newline normalization (`\n`) so the file matches its pre-mount vanilla bytes.
