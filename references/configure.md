# Configure: Consent, Rollback, Uninstall & Export (`references/configure.md`)

Use this reference for all control-plane administration: onboarding skills (`init`), managing consent (`opt-in` vs. `ignore`), restoring backups (`revert`), stripping integration blocks (`uninstall`), and exporting diffs for upstream PRs (`export`).

---

## 1. Onboarding & Consent Management (`init`)

1. **Discover Installed Skills:**
   - Load the host adapter (`vendors/gemini-web.md`, `vendors/claude-code.md`, or `vendors/codex.md`).
   - On **Gemini Web**, check Memory first for the `the-one-skill` consent roster (`opt-in` / `ignore` list) to avoid redundant file reads, then inspect any newly uploaded skills.
   - Run `python3 scripts/lint_skills.py <skills_root_dir>` to inspect token counts, frontmatter boundaries, consent status, and trigger overlaps.
2. **Per-Skill Consent Prompt:**
   Present a summary table of unmanaged skills and ask the user to choose per skill:
   - **Opt-In:** Mounts `<!-- the-one-skill:opt-in -->` + the canonical integration block below. Eligible for evolution and orthogonality audits.
   - **Opt-Out (`ignore`):** Appends `<!-- the-one-skill:ignore -->`. Locked—`the-one-skill` will never read it for evolution or propose edits unless explicitly unlocked.
   - **Ask Later:** Leaves the skill unmanaged for this session.

### Canonical Integration Block (Mount on Opt-In)
Save a pre-mount snapshot to `artifacts/snapshots/<skill-name>.<timestamp>.bak.md`, verify `SKILL.md <= 800` tokens after mounting, get diff approval, and append this exact block separated by one blank line (idempotent):

```markdown
<!-- the-one-skill:opt-in -->
<!-- the-one-skill:start -->
### Continuous Evolution (`the-one-skill`)
- **Fast-Path Reflection:** If the user corrects output, a step retries, or a tool/schema error occurs while running this skill, read `the-one-skill/references/evolve.md` (§1) to propose a surgical, diff-first fix to **only this skill** (saving a pre-patch snapshot first).
- **Boundary & Cap Discipline:** Keep this `SKILL.md` under 800 tokens; move bulky examples or checklists into `references/`. If another skill triggers simultaneously, run the Full-Roster Orthogonality Audit in `the-one-skill/references/evolve.md` (§2).
<!-- the-one-skill:end -->
```

On Gemini Web, mirror `{skill_name: "opt-in" | "ignore"}` in Memory so future turns know consent status immediately.

---

## 2. Rollback (`revert`) & Clean Removal (`uninstall`)

- **Revert to Snapshot (`revert`):**
  1. Locate the latest (or requested) snapshot in `artifacts/snapshots/<skill-name>.<YYYYMMDDTHHMMSSZ>.bak.md`.
  2. Show the unified diff between the current `SKILL.md` and the snapshot.
  3. Upon user confirmation, restore the snapshot and validate with `python3 scripts/lint_skills.py`.
- **Strip Integration Blocks (`uninstall`):**
  1. Remove `<!-- the-one-skill:opt-in -->` (or `<!-- the-one-skill:ignore -->`) and the `<!-- the-one-skill:start --> ... <!-- the-one-skill:end -->` block.
  2. Normalize trailing whitespace to a single newline (`\n`) so the file matches its exact pre-mount vanilla bytes.
  3. To permanently lock a skill instead, strip the `start...end` block and place `<!-- the-one-skill:ignore -->` at the bottom of `SKILL.md`.

---

## 3. Local State Export & PR Diff (`export`)

To contribute local improvements back to `mtfuller/the-one-skill`:
1. Stage local `the-one-skill` files into `artifacts/local-export/`.
2. Compare against a clean upstream checkout (Claude Code / Codex) or upstream files fetched from `raw.githubusercontent.com/mtfuller/the-one-skill/main/...` (Gemini Web):
   ```bash
   python3 scripts/export_diff.py <upstream_dir> <local_dir> artifacts/the-one-skill-changes.patch
   ```
3. `export_diff.py` writes a standard unified diff, prints a Markdown PR summary, and blocks accidental leaks of private emails, home paths (`/Users/<name>`), API tokens, or Memory state dumps.
