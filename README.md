# the-one-skill

> *One skill to tend them all, one skill to find them,*
> *one skill to mend them all, and never leave the old behind.*

An Agent Skill that keeps watch over all your other skills. After each journey it sits by the fire and goes over the road behind you: which skills were used, where you had to correct the output, where the way got hard. Then it proposes how to make the next journey easier. It applies only the changes you approve, and it **never loses the original**.

It works on any host that loads skills: Claude Code, Gemini, or another agent that follows the same pattern. It ships no vendor-specific code. On first use it studies your host and writes its own adapter for it.

---

## ✦ What it can do

### 🔥 Reflect and improve: *the council at the hearth*
After a session it names the skills that came with you and what you had to correct, then offers **numbered, specific fixes**. "Add a rule: dates in YYYY-MM-DD" is specific. "Make the format clearer" is not. Each fix is checked against the skill's existing rules. A conflict is raised and confirmed by you, never overruled quietly. If you've already named the change you want, it goes straight to the diff, and it asks one question, not a string of them.

### 🗺️ Manage your roster: *keeping the company in order*
It reviews every installed skill and flags:
- triggers that overlap
- descriptions too vague to say when the skill should be used
- broken structure
- workflows that recur but no skill covers

It can **create, merge, split, rename, retire, and restore** skills. A skill is never deleted, only retired, and it can be called back whenever you want.

### 📜 Never lose the original: *the old ways are kept*
The first change to any skill saves the original untouched. Say *"revert"* and it comes back exactly as it was. Say *"bring the change back"* and the improved version returns. Edits you made by hand are never overwritten.

### 🧭 Adapts to any host: *learning the lay of each land*
It carries no maps for particular hosts. Instead it carries a **framework for drawing them**. On a new host it:
1. Checks what the host can really do, using read-only probes. It never takes the host's word for it, and never experiments on your real skills.
2. Picks the safest way the host allows to keep originals:

| Strategy | When the host offers | Original kept as | Revert |
| :--- | :--- | :--- | :--- |
| A. Store & swap | Filesystem access + Python | An exact copy in `the-one-skill-store/`, outside the skills folder | `skillctl.py use <skill> original` |
| B. Twin | Create + enable/disable | The original, disabled and never edited; changes go into `<name>-tuned` | Disable the twin, enable the original |
| C. Backup first | Edit only | A backup you download before the first change | Re-upload it |
| D. Hand-off | No write access | Unchanged; you apply the files yourself | Put the old files back |

3. Writes the map, `references/agentspace/<host>.md`. It records where skills live, the exact steps for each operation, any permission prompts to expect, and which skills, connectors, or plugins are **protected** and must never be touched. You see the file before it's saved.

If the land turns out different from the map, it stops, shows you what it found, and offers a correction.

### 📕 Learns your setup: *the red book of your journeys*
`references/agentspace/` is its own book about you. Next to the host maps it can keep preferences, roster notes, domain rules, connector notes, and a history of past changes: anything that would otherwise be forgotten between sessions. `index.md`, the book's table of contents, is read at the start of every session, so it can see at a glance what it already knows. Every new page is proposed to you first.

### ⚖️ Improves itself, within limits it cannot change
the-one-skill can propose changes to its own instructions and maps, using the same diff, approval and revert as any other skill. What it may never become is set by `references/readonly-self-improvement.md`, a policy it can't edit. The policy has ten invariants. Among them:
- originals are kept
- nothing changes without approval
- no action is quietly swapped for another
- results are checked, not trusted
- protected things stay untouched
- nothing is deleted

Notes in agentspace can make these rules stricter, but never looser. Only you can change the policy, by hand.

---

## Install
- **Claude Code:** clone into `~/.claude/skills/the-one-skill` (personal) or `.claude/skills/the-one-skill` (project).
- **Other hosts:** upload or install the folder as a custom skill.

On its first run it finds an empty `agentspace/index.md`, recognizes a fresh install, and proposes a map for your host.

## Speak, friend, and ask
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
evals/headless/                           scripted Claude Code eval scenarios (claude -p)
```

### `skillctl.py` (strategy A)
```bash
python3 scripts/skillctl.py --root <skills_folder> <command>
```
| Command | What it does |
| :--- | :--- |
| `list [--json]` | Every installed skill, its state, and any structural problems |
| `status` | Skills the-one-skill manages: `original`, `tuned`, `edited`, or `retired` |
| `draft <skill>` | Saves the original (first time only) and opens a draft in the store |
| `diff <skill>` | Shows the draft against the installed skill |
| `apply <skill>` | Installs the draft (after you approve the diff) |
| `use <skill> original\|tuned` | Reverts, or switches the improvement back in |
| `retire <skill>` / `restore <skill>` | Moves a skill out of the skills folder and back, intact |

Built-in safeguards:
- It never overwrites hand edits.
- It checks every copy against the original before trusting it.
- It refuses to change `readonly-*` files.
- It keeps a skill's `.git` folder across swaps.
- If a command is interrupted, running it again finishes the job.

## Privacy
Your agentspace can name your private skills and connectors, so everything in `references/agentspace/` except the empty `index.md` is git-ignored. Once the skill fills in your index, git shows it as modified. Keep it home: don't commit it upstream.

## Develop
```bash
python3 -m unittest discover tests            # unit tests for skillctl.py
evals/headless/scenarios.sh /tmp/tos-eval     # judgment scenarios in real Claude Code sessions
```
See [`evals/headless/README.md`](evals/headless/README.md) for what each scenario checks, and [`evals/checklist.md`](evals/checklist.md) for the interactive checks.
