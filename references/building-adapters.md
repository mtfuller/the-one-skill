# Building an Agentspace Adapter

An **adapter** is a short file in `references/agentspace/`. It tells the-one-skill how to apply its method on one host, such as Claude Code, Gemini web chat, a Gemini task sandbox, or any other agent that loads skills. Adapters are written on the user's own system, from what can be observed there. They are not shipped with the skill. This file is the framework for building them. `references/readonly-self-improvement.md` holds the rules every adapter must keep.

## When to build or update one
- No adapter's `Detect:` line matches the current host (Step 0).
- The host behaved differently from what its adapter says.
- The user wants to protect a skill, connector, or plugin, or record a preference about how skills are managed.

## 1. Identify the host
Use what you can observe: your tool names, your system prompt, where skills live, and how they are loaded. Choose a slug made of lowercase letters and hyphens. Give each surface its own file when surfaces behave differently (for example `gemini-chat` and `gemini-task`).

## 2. Take stock of abilities
Answer each question from observation (a tool's schema, a listing, a read-back). Do not ask the host what it can do: hosts misdescribe their own abilities. Mark each answer `verified`, `documented`, or `unknown`.

| Question | Needed for |
| :--- | :--- |
| Can I list skills, with name, enabled state, and source? | Roster |
| Can I read every file of a skill? | Evaluate, diff |
| Can I create a skill? With more than one file? | Create |
| Can I edit a skill? Does editing keep history? Does it drop files I did not send? | Apply |
| Can I enable and disable skills? | Twin strategy, retire |
| Can I rename or delete? (Record it, but do not rely on it.) | n/a |
| Must skill names be unique? | Twin naming |
| Can I reach the skills folder on a filesystem? | Store & swap |
| Can I run Python 3, and does it see the same files as the skills folder? | `scripts/skillctl.py` |
| Which skills, connectors, or plugins are managed by someone else (organization, plugin, platform)? | Protected list |

Use read-only probes first. If an answer can only be found by writing, ask the user first, then use a throwaway skill named `tos-probe`. Clean it up afterwards (disable it if the host cannot delete).

## 3. Choose a strategy
Use the first strategy that fits.

| Strategy | Needs | Original kept as | Apply | Revert |
| :--- | :--- | :--- | :--- | :--- |
| **A. Store & swap** | Filesystem access to the skills folder, plus Python 3 on that filesystem | An exact copy in a store next to (never inside) the skills folder | `skillctl.py draft` → edit → `diff` → `apply` | `skillctl.py use <skill> original` |
| **B. Twin** | Create plus enable/disable, without filesystem access | The original skill, disabled and never edited | Create or edit `<name>-tuned`, then disable `<name>` | Disable the twin, enable the original |
| **C. Backup first** | Edit only, with no disable and no history | A backup the user downloads, confirmed before the first change | Edit in place | The user re-uploads the backup |
| **D. Hand-off** | No write abilities | Unchanged, because the user makes every change | Give the user the full files and where they go | The user puts the old files back |

Before the first change under C or D, tell the user what their part is. Invariant 1 depends on it.

**Strategy A commands** (`python3 scripts/skillctl.py --root <skills_folder> <command>`): `list [--json]`, `status`, `draft`, `diff`, `apply`, `use <skill> original|tuned`, `retire`, `restore`. The script refuses to overwrite hand edits, refuses to change `readonly-*` files, and keeps a skill's `.git` folder.

## 4. Write the adapter
Keep it under about 80 lines. Record facts and the exact steps to follow. Leave the method out: it is already in `SKILL.md`.

```markdown
# Agentspace: <Host name and surface>
Slug: <slug>
Detect: <signals you can observe that this is the host, e.g. tool names, skills folder path>
Verified: <YYYY-MM-DD>
Strategy: <A|B|C|D>: <one line on how originals are kept>

## Where skills live
<paths or UI location, including scopes such as personal or project>

## Abilities
| Ability | Status | Notes |
| :--- | :--- | :--- |
| List | verified | ... |

## Operations
- **List roster:** ...
- **Improve:** draft → show diff → yes → apply → verify by ...
- **Revert / switch back:** ...
- **Create:** ...
- **Retire / restore:** ...
- **Change the-one-skill itself:** ...

## Protected (never modify)
- `<skill, connector, or plugin>`: <why, e.g. managed by organization>

## Host notes
- <traps seen here, reload behavior, limits>
```

## 5. Save it
Show the user the whole adapter and the strategy you chose, with reasons. After they approve, save it as a change to the-one-skill (self-change procedure, §3 of the policy). On the first change this also keeps the-one-skill's own original. Under strategy D, give the file to the user to add by hand.

## 6. Keep it accurate
When the host does something the adapter does not describe, propose a fix in your reflection. Give the evidence: what you ran and what came back. Update `Verified:` whenever you confirm a fact again.

## Known traps (seen on real hosts)
- **Edits that drop files.** Sending only `content` to an edit tool replaced the whole skill with a single `SKILL.md`, and `references/` was lost. Send the whole folder when the tool allows it, and check the file list afterwards.
- **False reports.** A tool said "updated" when nothing changed, or claimed an ability it did not have. List or read back after every action.
- **Name collisions.** When a name is taken, hosts may offer to "update the existing skill". Choose a different name instead.
- **Sandboxed code.** Code can run in a sandbox that cannot see the skills, or that sees copies of them. Stage files explicitly, or use strategy B.
- **Stale loading.** Changed skills often load only in a new session.
- **Store inside the skills folder.** The host then loads stored copies as extra skills. Keep the store outside.
- **Skills that are git checkouts.** Keep `.git` (skillctl does this). Mention that git will show the change as uncommitted.
