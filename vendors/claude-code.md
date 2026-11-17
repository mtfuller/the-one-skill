# Host Guide: Claude Code

Skills are folders in `~/.claude/skills/` (personal) or `.claude/skills/` (project). Always change them through `scripts/skillctl.py` (pure Python 3, no installs), never by editing the skill folder directly.

```bash
python3 scripts/skillctl.py --root <skills_folder> <command>
```

| Command | What it does |
| :--- | :--- |
| `status` | Lists skills the-one-skill has changed and which version is installed: `original`, `tuned`, `edited` (changed by hand), or `missing`. |
| `draft <skill>` | Saves the original (first time only) and copies the installed skill to a draft folder in the store. Edit the files there. |
| `diff <skill>` | Shows the draft against the installed skill (or, with no draft, the original against the tuned version). |
| `apply <skill>` | Installs the draft as the tuned version. Run only after the user approves the diff. |
| `use <skill> original` / `use <skill> tuned` | Revert to the original, or switch the improvement back in. |

## Improving a skill (Step 6)
1. `draft <skill>` and edit the files in the printed draft folder. Keep the frontmatter `name` the same.
2. `diff <skill>` and show the diff to the user. Wait for a yes.
3. `apply <skill>`. If the user says no, just leave the draft; the next `draft` starts over.

## Reverting (Step 7)
`use <skill> original`. `use <skill> tuned` brings the improvement back.

## Creating a new skill
Check that `<skills_folder>/<name>/` does not exist, show the user the full `SKILL.md`, and create the folder after they approve. Nothing is overwritten, so no backup is needed; its first later change goes through `draft`.

## Good to know
- The store sits next to the skills folder (`~/.claude/the-one-skill-store/` or `.claude/the-one-skill-store/`), so Claude Code never loads stored copies. For a project folder, ask the user whether to commit the store or add it to `.gitignore`.
- It keeps exactly two versions per skill: the original and the latest tuned one. Applying a new change replaces the previous tuned version.
- If a skill was edited by hand, `use` refuses. Run `draft` (it starts from the hand edits) and `apply` to keep them.
- If a command is interrupted, run the same command again.
- Plugin skills and skills managed by an organization are not in these folders; tell the user to change them where they came from.
- If Claude Code does not pick up a changed skill, start a new session.
