# Configure: Status, Locks, Revert, Retire & Export (`references/configure.md`)

Use this reference for administration of the skill library: checking status, locking skills, reverting or reapplying refinements, retiring skills, cleaning up stored history, and exporting changes to `the-one-skill` itself.

On **Gemini Web** there is no `skillctl.py`; follow `vendors/gemini-web.md` instead, which maps each operation below to Gemini's own skill tools.

---

## 0. The Swap Model (Applies to Every Operation)

- **Originals are never edited.** The first refinement saves a pristine copy of the original in the store and installs one working copy at the same path, with the same name. Later refinements edit only that working copy.
- **Disabled means out of the skills folder.** Inactive versions live in the store, a sibling of the skills root (default `<skills_root>/../the-one-skill-store/`), which the host never loads.
- **At most one installed version per skill.** Stored history never counts as an installed skill.
- **Hand edits are protected.** Every swap checks the installed folder against its recorded content hash. If it was changed outside `the-one-skill`, the operation is refused until the user reviews the change and runs `accept`.
- Set `--root` to the skills folder the host loads (see the host adapter). All commands below are `python3 scripts/skillctl.py --root <skills_root> <command>`.

---

## 1. Status & Onboarding (`init`)

1. Load the host adapter and identify the skills root(s).
2. Run `status` to list every skill as `unmanaged`, `original`, `tuned`, `new`, `uninstalled`, or `retired`, with health (`ok`, `EDITED-OUTSIDE`, `MISSING`, `CONFLICT`), locks, and stored history.
3. Run `python3 scripts/lint_skills.py <skills_root>` for token counts, frontmatter boundaries, and trigger overlaps. Lint findings on unmanaged skills are informational: nothing is changed until a refinement is approved.
4. Ask the user which skills (if any) to **lock**. Locked skills are never refined, merged, or retired. No other onboarding step is needed: skills become managed on their first approved refinement.

## 2. Locks (`lock` / `unlock`)

- `lock <skill>` records the lock in the store; the skill's files are not touched.
- `unlock <skill>` only when the user explicitly asks.

## 3. Revert & Reapply (`revert` / `reapply`)

- **Preview:** `diff <skill>` shows original vs. installed working copy (or installed vs. parked copy after a revert).
- `revert <skill>`:
  - Refined skill: the working copy is parked in the store and the original is restored byte-for-byte, including `references/` and `scripts/`.
  - Skill installed by `the-one-skill`: it is parked, and any skills it replaced (merge/split) are restored.
- `reapply <skill>`: swaps the parked working copy (or new skill) back in, and retires the replaced skills again.
- `undo <skill>`: steps the working copy back one refinement (no effect on the original).
- On **Codex**, tell the user to restart Codex after any revert, reapply, undo, retire, or install.

## 4. Retire (`retire` / `unretire`)

- `retire <skill>` moves the installed skill into the store. This is the only form of "delete" `the-one-skill` performs; permanent deletion is left to the user.
- `unretire <skill>` puts it back. A skill retired by a merge is restored by reverting the merged skill instead.

## 5. Hand Edits & Housekeeping (`accept` / `prune` / `abort`)

- `accept <skill>`: after showing the user the outside edits (`diff`), record them as the current state. If the original is installed, the edits become the new original.
- `abort <skill>`: discard an uncommitted draft.
- `prune <skill> --keep N`: drop old working-copy history and discarded states. Ask first; this cannot be undone.

---

## 6. Local State Export & PR Diff (`export`)

To contribute improvements to `the-one-skill` itself back to `mtfuller/the-one-skill` (needs code execution; on Gemini Web use **Task** mode):
1. Stage local `the-one-skill` files into `artifacts/local-export/`.
2. Compare against a clean upstream checkout (Claude Code / Codex) or upstream files fetched from `raw.githubusercontent.com/mtfuller/the-one-skill/main/...` (Gemini Web):
   ```bash
   python3 scripts/export_diff.py <upstream_dir> <local_dir> artifacts/the-one-skill-changes.patch
   ```
3. `export_diff.py` writes a standard unified diff, prints a Markdown PR summary, and blocks accidental leaks of private emails, home paths (`/Users/<name>`), API tokens, or Memory state dumps.
