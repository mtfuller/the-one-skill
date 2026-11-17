# the-one-skill

> *One skill to tend them all, one skill to find them,*
> *one skill to mend them all, and never leave the old behind.*

An Agent Skill that keeps watch over all your other skills. After each journey it sits by the fire and goes over the road behind you: which skills were used, where you had to correct the output, where the way got hard. Then it proposes how to make the next journey easier. It applies only the changes you approve, and it **never loses the original**.

It works on any host that loads skills: Claude Code, Gemini, or another agent that follows the same pattern. It ships no vendor-specific code. On first use it studies your host and writes its own adapter for it.

---

## ✦ What it can do

### 🔥 Reflect and improve: *the council at the hearth*
After a session it tells you, in a line or two, what went wrong and what it would change: *"CSV summaries kept coming back as prose. From now on they'll be a table, which replaces the skill's old prose rule. Apply?"* You say yes once. You never have to manage skills, files, or versions: it talks about how things will behave, never about the mechanics. If you want the exact diff, just ask, and it shows it right away.

### 🗺️ Manage your roster: *keeping the company in order*
It reviews every installed skill and flags:
- triggers that overlap
- descriptions too vague to say when the skill should be used
- broken structure
- workflows that recur but no skill covers

It can **create, merge, split, rename, retire, and restore** skills. A skill is never deleted, only retired, and it can be called back whenever you want. Merging several skills brings their conflicts into the open (two fonts, two slide limits), and you settle each one. The merge is recorded as a single change set, so it can be undone in one step.

### 🏹 Find and install a skill: *seeking aid from trusted realms*
When you keep correcting the same mistakes, it first names the corrections. Then it looks for an existing skill in sources you trust:
1. your host's directory
2. sources listed in your `sources.md`
3. the vendor's official repositories

It compares the candidates against exactly what went wrong, and says plainly if none covers everything. Before installing a skill, it reads **every file** and tells you what the skill instructs, runs, and reaches over the network.

### 📜 Never lose the original: *the old ways are kept*
The first change to any skill saves the original untouched, along with its last five versions. You can undo as much or as little as you want:
- *"Remove the rule you added"* steps back one version, or removes just that rule. It never wipes everything.
- *"Revert"* brings back one skill's original exactly as it was. *"Bring the change back"* returns the improved version.
- *"Back to vanilla"* returns every skill as it was before the-one-skill touched it:
  - originals are put back
  - retired skills are restored
  - skills it created are retired
  - for skills you edited by hand, it asks first

Edits you made by hand are never overwritten.

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

3. Writes the map, `references/agentspace/<host>.md`. It records where skills live, the exact steps for each operation, any permission prompts to expect, and which skills, connectors, or plugins are **protected** and must never be touched. To you it's a one-time setup you agree to in a word. Ask to see the map if you're curious.

If the land turns out different from the map, it stops, shows you what it found, and offers a correction.

On Claude Code it also sets a **guard at the gate**: a small hook that blocks direct edits to your skills folder. That way, no session can rewrite a skill behind the-one-skill's back, even in auto mode. Its own tool still works, and you can remove the guard whenever you like.

### 📕 Learns your setup: *the red book of your journeys*
`references/agentspace/` is its own book about you. Next to the host maps it can keep preferences, roster notes, domain rules, connector notes, and trusted skill sources: anything that would otherwise be forgotten between sessions. `index.md`, the book's table of contents, is read at the start of every session, so it can see at a glance what it already knows. Every new page is proposed to you first.

### ⚖️ Improves itself, within limits it cannot change
the-one-skill can propose changes to its own instructions and maps, using the same plain-language yes and undo as any other skill. What it may never become is set by `references/readonly-self-improvement.md`, a policy it can't edit. The policy has eleven invariants. Among them:
- originals are kept
- nothing changes without approval
- no action is quietly swapped for another
- results are checked, not trusted
- protected things stay untouched
- nothing is deleted
- skills from outside are read in full before they're installed

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
- *"Find me a trusted Terraform skill; I'm tired of correcting you."*
- *"Combine my PPTX proposal skills into one."*
- *"Put that skill back how it was."* / *"Remove the rule you added to the adapter."* / *"Take everything back to vanilla."*
- *"Remember that I always want options as a table."*
- *"Improve the-one-skill: it asked too many questions."*

## Layout
```
SKILL.md                                  the always-on core: start, routing, how to talk, hard rules
references/readonly-self-improvement.md   read-only policy: tiers, invariants, self-change procedure
references/building-adapters.md           framework: probe a host, choose a strategy, write adapters, keep the index
references/improving.md                   reflect on a session and improve skills
references/undoing.md                     step back, undo change sets, back to vanilla
references/managing-roster.md             review, create, find and install, merge, split, rename, retire, restore
references/agentspace/index.md            map of agentspace (ships empty; filled in on your system)
references/agentspace/*                   adapters and your notes (generated on your system, git-ignored)
scripts/skillctl.py                       strategy A helper (Python 3 stdlib, no installs)
scripts/guard_skills.py                   Claude Code hook: blocks direct edits inside skills folders
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
| `status` | Skills the-one-skill manages: `original`, `tuned`, `earlier`, `edited`, `retired`, or created |
| `draft <skill>` | Saves the original (first time only) and opens a draft in the store |
| `diff <skill>` | Shows the draft against the installed skill (when you ask to see it) |
| `apply <skill>` | Installs the draft (after your yes) |
| `use <skill> original\|previous\|tuned\|<version>` | Reverts, steps back one version, or switches the improvement back in |
| `history <skill>` | The kept versions: the original plus the last 5 applied |
| `guard` | Prints the Claude Code hook that blocks direct edits to the skills folder |
| `sets` / `undo-set <name> [--apply]` | Lists change sets; shows, then runs, the reverse steps of one (merges, vanilla, renames) |
| `new <skill> [--from <folder>]` | Starts a skill that the-one-skill creates or installs, so it's tracked (going back to vanilla retires it) |
| `retire <skill>` / `restore <skill>` | Moves a skill out of the skills folder and back, intact |
| `--set <name> [--note "…"]` | On `apply`, `use`, `retire`, `restore`: records the step in a change set |

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
