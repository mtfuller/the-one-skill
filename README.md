# the-one-skill

> Reflect on how your skills performed, improve them, and never lose the original.

`the-one-skill` is an Agent Skill for **Claude Code** and **Gemini**. After a session it looks at which skills were used and what you had to correct, proposes specific fixes, checks them against each skill's existing rules, and applies only what you approve. The first change to any skill keeps the original untouched, so you can always say *"revert"*.

## Install
- **Claude Code:** clone into `~/.claude/skills/the-one-skill` (personal) or `.claude/skills/the-one-skill` (project).
- **Gemini:** upload the folder as a custom skill.

## Use it
Just ask:
- *"Reflect on this session."* / *"That skill got the format wrong again, fix it."*
- *"Make a skill for this; I do it every week."*
- *"Put that skill back how it was."*

## How changes stay reversible
| | Claude Code | Gemini |
| :--- | :--- | :--- |
| Original | Exact copy saved in `the-one-skill-store/` next to the skills folder, never modified | The original skill, disabled, never edited |
| Improved version | Installed in place of the original (one copy) | A separate `<name>-tuned` skill, enabled |
| Revert | `skillctl.py use <skill> original` | Disable `-tuned`, enable the original |
| Hand edits | Never overwritten: commands refuse, and `draft` keeps them | n/a |

Every change is shown as a diff and needs your yes.

## Layout
```
SKILL.md               the workflow (reflect → evaluate → propose → check → apply → revert)
vendors/claude-code.md how changes are applied on Claude Code
vendors/gemini.md      how changes are applied on Gemini
scripts/skillctl.py    Claude Code helper: status, draft, diff, apply, use (Python 3 stdlib)
tests/                 unit tests for skillctl.py
evals/checklist.md     manual checks to run in each host before a release
```

## Develop
```bash
python3 -m unittest discover tests
```
