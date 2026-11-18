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
It keeps your skills **orthogonal**: every job and every policy has one owner. Two skills overlap if they answer the same requests, *or* if they carry the same procedure. Three deck skills that each repeat the same brand rules are one policy with three copies, and a fix lands in one but not the others. A built-in check compares every pair of skills on both counts and finds instruction blocks repeated across skills. It runs on every review, and before any skill is created, installed, or widened, so overlap is caught before it's added.

It reviews every installed skill and flags:
- skills that compete for the same requests, or repeat the same procedure
- descriptions too vague to say when the skill should be used
- the same skill name in two places (project, personal, plugin)
- broken structure
- workflows that recur but no skill covers

It keeps a **roster map** in its notes: which skill owns each job and each shared policy, and which overlaps you chose to keep, so it doesn't ask twice.

It can **create, merge, extract a shared policy, split, rename, retire, and restore** skills. A repeated policy becomes one skill the others defer to, or the skills merge when they were really one job. A skill is never deleted, only retired, and it can be called back whenever you want. Merging several skills brings their conflicts into the open (two fonts, two slide limits), and you settle each one. The merge is recorded as a single change set, so it can be undone in one step.

### 🛠️ Create from verified work: *no forge starts cold*
A new skill never starts from a blank page if someone has already done the work. Before writing one, it checks the skills already on your host and the ones Anthropic, OpenAI, or Google publish, reads the closest, and picks a start:
- **install** a verified skill that fits as is
- **adapt** one that fits most of the job: installed exactly as published, with your changes as a second version you can undo on their own
- **borrow** structure, steps, and scripts from verified skills for a new one
- **scratch** only when nothing close exists

The draft is filled from your actual corrections in the session, names the neighbours it hands off to, and is checked for overlap before you see it.

It remembers the verified skills it has already read, and what it decided about each, so it doesn't search from scratch every session. A skill installed or adapted from a publisher can later be **updated from the publisher's newer release**: their changes go in, and your tweaks stay.

### ⚙️ Scripts for what must be exact: *what is forged does not waver*
Instructions get followed slightly differently each run, and code runs the same way every time. When a correction was mechanical (a count, a date format, a parse, a file layout), or the same code got written twice, it moves that step into a small script. It tests the script on the file from your session before proposing it. The instructions keep the judgement, and the scripts do the mechanical work. Scripts are written only in languages your host can run. Hosts differ (one may allow JavaScript, another only Python and bash), so it checks and records which languages work on each host and flags scripts that won't run there. Every new skill starts from a template built that way: inputs, steps, output with an example, edge cases, and where each script and reference fits.

### 🔌 Fits your connected tools: *allies already at hand*
When it creates or improves a skill, it looks at the connectors you have connected, such as your calendar, tasks, mail, docs, or issue tracker. If one would feed the skill's work or take its output, it offers that as an option in the same question. For example: *"Create it as described, or also have it pull your completed tasks?"* Roster reviews add a few one-line ideas for connected tools none of your skills use yet. Skills it writes this way still work when a connector is missing. They read through connectors freely but ask before sending, creating, or changing anything, and they never copy your account details.

### 🩺 Structure checks: *every road leads somewhere*
Reviewing your skills also catches skills whose files don't fit together:
- pointers to files that don't exist
- references and scripts that nothing mentions, so they're never read or run
- scripts with no line saying how to run them
- template placeholders left in
- descriptions over the host's limit
- absolute paths into one machine

It also tracks **when each skill was last used**: on Claude Code from your session history (it asks once first), elsewhere from its reflections. Skills idle for two months get listed so you can decide. It never retires one on its own.

### 🏹 Find and install a skill: *seeking aid from trusted realms*
When you keep correcting the same mistakes, it first names the corrections. Then it looks for an existing skill, but only one that **Anthropic, OpenAI, or Google** publishes:
- in their own products' skill directories (Claude, ChatGPT, Gemini), counting only skills the company itself publishes there
- in their official repositories

That list is fixed in the read-only policy. Agentspace notes can narrow it, but nothing the skill writes can widen it. Any other skill, you install yourself.

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
| A. Store & swap | Filesystem access + Python | An exact copy in `.tos-store/` in your project (or home folder), outside the skills folder | `skillctl.py use <skill> original` |
| B. Twin | Create + enable/disable | The original, disabled and never edited; changes go into `<name>-tuned` | Disable the twin, enable the original |
| C. Backup first | Edit only | A backup you download before the first change | Re-upload it |
| D. Hand-off | No write access | A backup zip it gives you; you upload the new version | Upload the backup |

Where the model has no skill tools but the host has its own skill-authoring workflow (such as a built-in skill-creator), that workflow can serve as the write ability for B or C. It's checked on a throwaway skill first, and only ever saves what the-one-skill drafted.

3. Writes the map, `references/agentspace/<host>.md`. It records where skills live, the exact steps for each operation, any permission prompts to expect, and which skills, connectors, or plugins are **protected** and must never be touched. To you it's a one-time setup you agree to in a word. Ask to see the map if you're curious.

If the land turns out different from the map, it stops, shows you what it found, and offers a correction.

On Claude Code it also sets a **guard at the gate**: a small hook that blocks direct edits to your skills folder. That way, no session can rewrite a skill behind the-one-skill's back, even in auto mode. Its own tool still works, and you can remove the guard whenever you like.

### 📕 Learns your setup: *the red book of your journeys*
`references/agentspace/` is its own book about you. Next to the host maps it can keep preferences, roster notes, domain rules, and connector notes: anything that would otherwise be forgotten between sessions. `index.md`, the book's table of contents, is read at the start of every session, so it can see at a glance what it already knows. Every new page is proposed to you first.

### 🦅 Updates itself, keeping what's yours: *news from the wider world*
When a new release comes out, download it (zip, folder, or the single-file `the-one-skill.bundle.md`, which any chat can read) and give it to the skill: *"Here's a new version, update yourself."* It reads every file, tells you in a few lines what's new, and merges three ways:
- the release's changes go in
- your own local improvements stay
- your agentspace isn't touched

Any change to the read-only policy is called out on its own. One yes applies it, and *"undo the update"* puts the previous version back.

### ⚖️ Improves itself, within limits it cannot change
the-one-skill can propose changes to its own instructions and maps, using the same plain-language yes and undo as any other skill. What it may never become is set by `references/readonly-self-improvement.md`, a policy it can't edit. The policy has eleven invariants. Among them:
- originals are kept
- nothing changes without approval
- no action is quietly swapped for another
- results are checked, not trusted
- protected things stay untouched
- nothing is deleted
- skills from outside come only from Anthropic, OpenAI, or Google, and are read in full before they're installed

Notes in agentspace can make these rules stricter, but never looser. Only you can change the policy, by hand.

---

## Install
- **Claude Code:** clone into `~/.claude/skills/the-one-skill` (personal) or `.claude/skills/the-one-skill` (project).
- **ChatGPT:** upload the release zip under Plugins → Skills. ChatGPT gives it no tools to change skills, so it drafts each change and hands you two zips: a backup of the skill as it was, and the new version to upload. If ChatGPT's own skill-creator can save a skill exactly as drafted, it can use that instead, after checking it on a throwaway skill.
- **Other hosts:** upload or install the folder as a custom skill.

On its first run it finds an empty `agentspace/index.md`, recognizes a fresh install, and proposes a map for your host.

## Speak, friend, and ask
- *"Reflect on this session."* / *"That skill got the format wrong again, fix it."*
- *"Make a skill for this; I do it every week."*
- *"Review my skills. Which ones overlap?"* / *"Merge these two."* / *"Retire the old report skill."*
- *"Find me an official skill for spreadsheets; I'm tired of correcting you."*
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
scripts/bundle.py                         pack a release into one text file (no agentspace), or unpack it
scripts/release.sh                        check, tag locally, and build the release files into dist/
references/updating.md                    update the-one-skill from a downloaded release
VERSION.md, CHANGELOG.md                  release number and plain-language notes
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
| `upgrade <skill> --from <folder> [--keep <path>]` | Drafts a new release merged three ways with your local changes; `--keep references/agentspace` keeps your setup |
| `move-store [--to <dir>]` | Moves the store, for example from the old `.claude/the-one-skill-store` to `.tos-store` |
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

## Releasing
1. On a branch, bump `VERSION.md` and add a plain-language `## <version>` entry to `CHANGELOG.md`. Merge it into main.
2. On an up-to-date, clean main, run `scripts/release.sh --tag`. It checks the version and the changelog, runs the tests, creates the tag `v<version>` locally, and builds `dist/the-one-skill-<version>.zip`, `dist/the-one-skill-<version>.bundle.md` and `dist/notes.md` from that tag. Both release files hold only the **package**: `SKILL.md`, `README.md`, `CHANGELOG.md`, `VERSION.md`, `LICENSE.md`, `references/`, and `scripts/*.py`. Every file is `.md` or `.py`, which skill hosts such as Gemini accept, and the script refuses to finish if any other file slips in.
3. Publish. The script pushes nothing; it prints the two commands: `git push origin v<version>`, then `gh release create …` (or create the release on GitHub and attach the two files).

Users update by downloading either file and asking the-one-skill to update itself.

## Develop
```bash
python3 -m unittest discover tests            # unit tests for skillctl.py
evals/headless/scenarios.sh /tmp/tos-eval     # judgment scenarios in real Claude Code sessions
```
See [`evals/headless/README.md`](evals/headless/README.md) for what each scenario checks, and [`evals/checklist.md`](evals/checklist.md) for the interactive checks.
