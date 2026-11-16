# Procedure: Safety, Rollback & Clean Uninstall (`snapshot`, `revert`, `uninstall`)

`the-one-skill` guarantees clean reversibility for every managed skill. All edits are preceded by snapshots, and all integration markers live inside deterministic HTML comment delimiters.

## 1. Saving a Snapshot (`snapshot`)

Before modifying any opted-in skill (see `references/skill-modification/modification-guide.md`):
1. Ensure `artifacts/snapshots/` exists.
2. Copy the skill's current `SKILL.md` to:
   ```text
   artifacts/snapshots/<skill-name>.<YYYYMMDDTHHMMSSZ>.bak.md
   ```
3. Record the snapshot path in the diff approval prompt so the user knows the exact rollback point.

## 2. Reverting a Skill (`revert`)

When the user asks to revert or undo changes to a skill:
1. Locate the latest snapshot for `<skill-name>` in `artifacts/snapshots/` (or the specific timestamp requested by the user).
2. Generate a unified diff between the current `SKILL.md` and the snapshot so the user can see what will be restored.
3. Upon user confirmation, overwrite `<skill-name>/SKILL.md` with the snapshot contents and validate with `python3 scripts/lint_skills.py`.

## 3. Stripping Integration Blocks (`uninstall`)

When the user wants to disconnect one skill—or all skills—from `the-one-skill` and return to vanilla state:
1. Remove the `<!-- the-one-skill:opt-in -->` (or `<!-- the-one-skill:ignore -->`) marker line.
2. Remove the delimited block inclusive of markers:
   ```markdown
   <!-- the-one-skill:start -->
   ...
   <!-- the-one-skill:end -->
   ```
3. Normalize trailing whitespace so the file ends with a single newline (`\n`), matching its exact pre-mount byte state.
4. If the user wants `the-one-skill` to permanently ignore a skill while keeping `the-one-skill` installed for other skills, strip the `start...end` block and place a single `<!-- the-one-skill:ignore -->` comment at the bottom of that skill's `SKILL.md` (and update Gemini Memory if on Gemini Web).
