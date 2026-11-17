# the-one-skill

> One skill to manage them all. It reflects on how your skills performed, improves them, keeps your roster tidy, learns your setup, and never loses an original.

`the-one-skill` is an Agent Skill for any host that loads skills: Claude Code, Gemini, or anything else that follows the same pattern. It ships no vendor-specific code paths. On first use it studies your host, writes its own adapter, and from then on manages your skills there. Every change is shown first, needs your yes, and can be undone.

## Capabilities

### 🔍 Reflect and improve
After a session, it identifies which skills were used, what you had to correct, and where friction came from. It then proposes **numbered, specific fixes**, such as "add a rule: dates in YYYY-MM-DD", not "make the format clearer". It checks each fix against the skill's existing rules and raises conflicts instead of overwriting them. It applies only the options you pick.

### 🗂️ Manage your roster
It reviews every installed skill and flags:
- overlapping triggers
- vague descriptions
- broken structure (a frontmatter name that doesn't match the folder, oversized `SKILL.md` files)
- gaps where a recurring workflow has no skill

It can also **create, merge, split, rename, retire, and restore** skills. "Delete" always means a retire that can be undone. Permanent deletion is left to you, in your host's settings.

### ↩️ Never lose the original
The first change to any skill saves the untouched original. Say *"revert"* to put it back exactly as it was, and *"bring the change back"* to swap the improved version in again. Edits you made by hand are never overwritten.

### 🧭 Adapts to any host
Instead of maintained vendor guides, the skill carries a **framework** for building adapters. On a new host it:
1. Takes stock of what the host can really do, using read-only probes (it never asks the host to describe itself, and never experiments on your real skills).
2. Picks the safest way to keep originals that the host supports:

| Strategy | When the host offers | Original kept as | Revert |
| :--- | :--- | :--- | :--- |
| A. Store & swap | Filesystem access + Python | An exact copy in `the-one-skill-store/`, next to the skills folder | `skillctl.py use <skill> original` |
| B. Twin | Create + enable/disable | The original, disabled and never edited; changes go in `<name>-tuned` | Disable the twin, enable the original |
| C. Backup first | Edit only | A backup you download before the first change | Re-upload it |
| D. Hand-off | No write access | Unchanged; you apply the files yourself | Put the old files back |

3. Writes `references/agentspace/<host>.md`, recording where skills live, the exact steps for each operation, and which skills, connectors, or plugins are **protected** and must never be touched. It shows you the file before saving it.

If the host later behaves differently from what the adapter says, the skill stops and offers a fix to the adapter, with evidence.

### 🧠 Learns your setup
`references/agentspace/` is the skill's own workspace for you. Beyond the host adapter, it can keep whatever helps it serve you between sessions, such as preferences, roster notes, domain rules, connector notes, and a change history. `index.md` is a one-page map of all of it, read first at the start of every session, so the skill knows at a glance what it has. Every addition is proposed and approved like any other change.

### 🔁 Improves itself, within limits it can't change
the-one-skill can propose changes to its own instructions and adapters, using the same flow it uses for any skill: diff, approval, reversible. What it may never do is set by `references/readonly-self-improvement.md`, a policy it is not allowed to edit, which defines ten invariants. Among them:
- originals are kept
- nothing changes without approval
- no quiet substitution of one action for another
- verify results instead of trusting the host
- protected things stay untouched
- nothing is deleted

Agentspace files may add rules, never loosen these.

## Install
- **Claude Code:** clone into `~/.claude/skills/the-one-skill` (personal) or `.claude/skills/the-one-skill` (project).
- **Other hosts:** upload or install the folder as a custom skill.

The first time you use it, it reads the empty `agentspace/index.md`, sees a fresh install, and proposes an adapter for your host.

## Use it
Just ask:
- *"Reflect on this session."* / *"That skill got the format wrong again, fix it."*
- *"Make a skill for this; I do it every week."*
- *"Review my skills. Which ones overlap?"* / *"Merge these two."* / *"Retire the old report skill."*
- *"Put that skill back how it was."* / *"Actually, bring the change back."*
- *"Remember that I always want options as a table."*
- *"Improve the-one-skill: it asked too many questions."*

## Layout
```
SKILL.md                                  workflow: load agentspace → reflect → propose → check → apply → revert
references/readonly-self-improvement.md   read-only policy: tiers, invariants, self-change procedure
references/building-adapters.md           framework: probe a host, choose a strategy, write adapters, keep the index
references/managing-roster.md             review, create, merge, split, rename, retire, restore
references/agentspace/index.md            map of agentspace (ships empty; filled in on your system)
references/agentspace/*                   adapters and your notes (generated on your system, git-ignored)
scripts/skillctl.py                       strategy A helper (Python 3 stdlib, no installs)
tests/                                    unit tests for skillctl.py
evals/checklist.md                        manual checks to run on a host before a release
```

### `skillctl.py` (strategy A)
```bash
python3 scripts/skillctl.py --root <skills_folder> <command>
```
| Command | What it does |
| :--- | :--- |
| `list [--json]` | Every installed skill, its state, and any structural problems |
| `status` | Skills the-one-skill manages: `original`, `tuned`, `edited`, `retired` |
| `draft <skill>` | Saves the original (first time only) and opens a draft in the store |
| `diff <skill>` | Shows the draft against the installed skill |
| `apply <skill>` | Installs the draft (after you approve the diff) |
| `use <skill> original\|tuned` | Revert, or switch the improvement back in |
| `retire <skill>` / `restore <skill>` | Moves a skill out of the skills folder and back, intact |

Built-in safeguards:
- It never overwrites hand edits.
- It checks every copy against the original before trusting it.
- It refuses any change to `readonly-*` files.
- It keeps a skill's `.git` folder across swaps.
- If a command is interrupted, running it again finishes the job.

## Privacy
Your agentspace can name your private skills and connectors, so everything in `references/agentspace/` except the empty `index.md` is git-ignored. Once the skill fills in your index, git will show it as modified. Don't commit that copy upstream.

## Develop
```bash
python3 -m unittest discover tests
```
