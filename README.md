# the-one-skill

> Reflect on how your skills performed, improve them, manage your roster, and never lose the original.

`the-one-skill` is an Agent Skill that works on any host that loads skills, such as Claude Code or Gemini. After a session it looks at which skills were used and what you had to correct, proposes specific fixes, checks them against each skill's existing rules, and applies only what you approve. It can also review your whole skill roster (overlaps, vague triggers, gaps) and create, merge, retire, or restore skills. It can improve itself too, within a policy it is not allowed to edit.

## Install
- **Claude Code:** clone into `~/.claude/skills/the-one-skill` (personal) or `.claude/skills/the-one-skill` (project).
- **Other hosts:** upload or install the folder as a custom skill.

On first use, it builds an **adapter** for your host (see below) and shows it to you before saving it.

## Use it
Just ask:
- *"Reflect on this session."* / *"That skill got the format wrong again, fix it."*
- *"Make a skill for this; I do it every week."*
- *"Review my skills. Which ones overlap?"* / *"Retire the old report skill."*
- *"Put that skill back how it was."*
- *"Improve the-one-skill: it asked too many questions."*

## How it adapts to each host
The skill ships no vendor-specific guides. Instead:

| File | Role | Who changes it |
| :--- | :--- | :--- |
| `references/readonly-self-improvement.md` | The policy: tiers, invariants, and how the skill may change itself | Only you, by hand |
| `references/building-adapters.md` | The framework: how to probe a host, choose a strategy, and write an adapter | the-one-skill, with your approval |
| `references/agentspace/` | `index.md` (a map of everything here, read first), one adapter per host (where skills live, what the host can really do, how to apply and revert, what is protected), plus any other files the agent creates to fit how you work: preferences, roster notes, domain rules, connector notes | Written by the-one-skill on your system, with your approval |

Agentspace contents are git-ignored because they can name your private skills and connectors.

### Reversibility strategies
| Strategy | When | Original | Revert |
| :--- | :--- | :--- | :--- |
| A. Store & swap | Filesystem access + Python | Exact copy in `the-one-skill-store/` next to the skills folder | `skillctl.py use <skill> original` |
| B. Twin | Create + enable/disable only | The original, disabled and never edited; changes go in `<name>-tuned` | Disable the twin, enable the original |
| C. Backup first | Edit only | A backup you download before the first change | Re-upload it |
| D. Hand-off | No write access | Unchanged; you apply the files | Put the old files back |

Every change is shown as a diff and needs your yes. Nothing is ever deleted: retiring a skill can always be undone.

## Layout
```
SKILL.md                                  workflow: load adapter → reflect → propose → check → apply → revert
references/readonly-self-improvement.md   read-only policy and invariants
references/building-adapters.md           how to build a host adapter
references/managing-roster.md             review, create, merge, split, rename, retire, restore
references/agentspace/                    adapters and user-specific notes (generated per system, git-ignored)
scripts/skillctl.py                       strategy A helper: list, status, draft, diff, apply, use, retire, restore
tests/                                    unit tests for skillctl.py
evals/checklist.md                        manual checks to run on a host before a release
```

## Develop
```bash
python3 -m unittest discover tests
```
