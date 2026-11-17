# Building an Agentspace Adapter

An **adapter** is a short file in `references/agentspace/`. It tells the-one-skill how to apply its method on one host, such as Claude Code, Gemini web chat, a Gemini task sandbox, or any other agent that loads skills. Adapters are written on the user's own system, from what can be observed there. They are not shipped with the skill. This file is the framework for building them. `references/readonly-self-improvement.md` holds the rules every adapter must keep.

## When to build or update one
- No adapter's `Detect:` line matches the current host (the Start steps in `SKILL.md`).
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
| Does the host have a skill directory, marketplace, or installer? Who runs it, and does it show each skill's publisher? | Find and install (only Anthropic, OpenAI, and Google skills, per the policy) |
| How many versions of a skill can be kept? | Step back |
| Can the host run a check before file edits (for example Claude Code `PreToolUse` hooks)? | Guard |
| Can it read an uploaded zip, or only text files? | Updating (zip or bundle) |
| Must skill names be unique? | Twin naming |
| Can I reach the skills folder on a filesystem? Does a change there last into a new session? | Store & swap |
| Can I run Python 3, and does it see the same files as the skills folder? | `scripts/skillctl.py` |
| With no skill tools, does the host have its own way to write skills (a built-in skill-creator, a "create with chat" mode)? Can it update an existing skill, and does it keep every file? | Authoring workflow (§3) |
| Which skills, connectors, or plugins are managed by someone else (organization, plugin, platform)? | Protected list |

Use read-only probes first. If an answer can only be found by writing, ask the user first, then use a throwaway skill named `tos-probe`. Clean it up afterwards (disable it if the host cannot delete).

**Writable is not the same as saved.** Code may see a skills folder that is a copy made for this session. Signs of a copy: the folder sits on an overlay or temporary mount (check `mount` and `df`), or skill folders are named by generated IDs instead of skill names. Before you rely on a folder for strategy A, confirm that something written outside the skills folder in an earlier session (such as the store) is still there in a new one. If you can't confirm it, treat the folder as a copy: it can't keep originals or apply changes.

## 3. Choose a strategy
Use the first strategy that fits.

| Strategy | Needs | Original kept as | Apply | Revert |
| :--- | :--- | :--- | :--- | :--- |
| **A. Store & swap** | Filesystem access to the skills folder, plus Python 3 on that filesystem | An exact copy in a store outside the skills folder (default `<project>/.tos-store`) | `skillctl.py draft` → edit → `diff` → `apply` | `skillctl.py use <skill> original` |
| **B. Twin** | Create plus enable/disable, without filesystem access | The original skill, disabled and never edited | Create or edit `<name>-tuned`, then disable `<name>` | Disable the twin, enable the original |
| **C. Backup first** | Edit only, with no disable and no history | A backup the user downloads, confirmed before the first change | Edit in place | The user re-uploads the backup |
| **D. Hand-off** | No write abilities | Unchanged, because the user makes every change | Give the user the full files and where they go | The user puts the old files back |

Before the first change under C or D, tell the user what their part is. Invariant 1 depends on it.

**Hand-off files.** Under D, give the user two downloads for each skill you change: a zip of the skill exactly as installed (their backup, made before anything else), and a zip of the new version. Put every file of the skill in each zip, under a top folder with the skill's name. Tell the user to keep the backup, and how to upload the new version so it replaces the skill instead of adding a second one with the same name. After they upload it, check in a new session that the change is in effect.

### Authoring workflow: when you have no skill tools
Some hosts give the model no tools to write skills but have their own way to author them: a built-in skill-creator skill, or a "create with chat" mode. That workflow can be this host's write ability. Take stock of it like any tool, with a `tos-probe` skill and the user's permission. Check whether it can create a skill, update an existing one in place, keep every file you send, and keep history. Then pick the strategy from what it verifiably does: B if it can create and the user can enable and disable skills, C if it can only edit in place, and D if it can't update a skill or drops files.

When you use it:
- **You draft, it saves.** Write the full new version yourself first, as for any change. Give it the whole skill folder word for word, and ask it to save that and nothing else. Never ask it to write or improve the skill for you.
- **Your rules come first.** It may follow its own instructions: rewriting or restructuring, renaming, dropping files, or saving before asking. If it would do any of that, don't use it for that step. Fall back to D.
- **It is protected.** It belongs to the platform. Use it; never change it.
- **Same approval.** The user's one yes covers the change. If the workflow asks its own question, that is the host's prompt: say so before you start, as with permission prompts.
- **Verify.** Read the saved skill back, file by file. Then confirm in a new session that the host loads the new version.
- **Record it** in the adapter, with the exact steps that worked.

**Strategy A commands** (`python3 scripts/skillctl.py --root <skills_folder> <command>`): `list [--json]`, `status`, `draft`, `diff`, `apply`, `use <skill> original|previous|tuned|<version>`, `history`, `new <skill> [--from <folder>]`, `retire`, `restore`, `sets`, `undo-set <name> [--apply]`, `upgrade <skill> --from <folder> [--keep <path>]`, `move-store [--to <dir>]`. `apply`, `use`, `retire`, and `restore` take `--set <name> [--note "<why>"]` to group steps into an undoable change set. The store keeps the original plus the last 5 applied versions of each skill.

Call the script with absolute paths and nothing chained in front of it (no `cd …;` or `&&`). Permission allow rules match the start of a command, so a leading `cd` stops them from applying. The script refuses to overwrite hand edits, refuses to change `readonly-*` files, and keeps a skill's `.git` folder. `draft` creates the store on first use. By default it is `<project>/.tos-store` for `<project>/.claude/skills` (for personal skills in `~/.claude/skills`, that's `~/.tos-store`). It sits outside `.claude/`, so editing drafts doesn't trigger Claude Code's permission prompts. In a project, add `.tos-store/` to the project's ignore file as part of the setup, and mention that in a few words. If an older store exists at `.claude/the-one-skill-store`, `skillctl` keeps using it. Offer `move-store` once, in the same message as the next change.

### Guard against direct edits
Instructions alone don't stop a model from editing a skill file directly, and auto-approval modes let such edits through. Where the host can run a check before file edits, offer a **guard** as part of the one-time setup. It blocks direct edits inside the skills folder, while the strategy's own tool keeps working.
- **Claude Code:** `skillctl.py --root <skills_folder> guard` prints the hook setting. Merge it into the project's `.claude/settings.local.json` (or the user's `~/.claude/settings.json` for personal skills), keeping any hooks already there. `skillctl.py` runs as its own process, so the guard doesn't affect it. Drafts live in the store, outside the guarded folder.
- **Verify it:** after installing, try one direct edit of a skill file, which should be blocked, then do nothing else to that file.
- **Record it in the adapter** ("Guard: installed in …"). If the host can't run such checks, record "Guard: not available".
- Only the user removes the guard. If they want to edit skills by hand, they can still do it outside the agent.

## 4. Write the adapter
Keep it under about 80 lines. Record facts and the exact steps to follow. Leave the method out: it is already in `SKILL.md` and its references.

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
- **Improve:** draft → edit → plain-language yes → apply → verify by ...
- **Revert / step back / switch back:** ... (which versions are kept: ...)
- **Create:** ...
- **Find and install:** host directory or installer, if any: ...
- **Retire / restore:** ...
- **Permissions:** prompts or policies to expect, and the allow rule the user added (if any): ...
- **Guard:** installed in <settings file> | not available: ...
- **the-one-skill release installed:** <version> (the base for the next update)
- **Change the-one-skill itself:** ...

## Protected (never modify)
- `<skill, connector, or plugin>`: <why, e.g. managed by organization>

## Host notes
- <traps seen here, reload behavior, limits>

```

## 5. Save it
To the user this is a one-time setup: say so in a few words, in the same message as their request. Show the adapter, the strategy, and the index row only if they ask. After they say yes, save it as a change to the-one-skill (self-change procedure, §3 of the policy). On the first change this also keeps the-one-skill's own original. Under strategy D, give the file to the user to add by hand.

## 6. Keep it accurate
When the host does something the adapter does not describe, propose a fix in your reflection. Give the evidence: what you ran and what came back. Update `Verified:` whenever you confirm a fact again.

## 7. Shape agentspace to fit the user
The adapter is the only file agentspace must have. Beyond it, you are free to organize `references/agentspace/` however best serves this user. Add files and subfolders when they keep knowledge that would otherwise be lost between sessions. For example:
- `preferences.md`: how the user likes reflections and proposals presented (for example "always show diffs", if they want them).
- `roster-notes.md`: what each skill is for, which ones overlap on purpose, and which are being phased out.
- `<domain>.md`: standing rules for a field the user works in, shared across several of their skills.
- `connectors/<name>.md`: how a connector behaves here and which of its tools are safe to rely on.

Conventions:
- **Start each file with its purpose** on one line (`Purpose: ...`). Only adapters have a `Detect:` line. These headers let the index be rebuilt from the files alone.
- **List every file in `index.md`** (§8), with one line on when to read it. A file the index does not list is never read.
- **Read on demand.** Start loads only the index and the matching adapter. Open other files when their "read when" applies.
- **Keep files small and single-purpose.** Merge or prune files that are stale or overlap, and propose that like any other change.
- **Same rules as everything else:** describe it in plain words, save only after a yes, show the content if asked, store no secrets, and never name a file `readonly-*`.
- **Rules may only narrow behavior.** A file can add rules or protections (for example "always ask before touching skills in project X"). It can never loosen a rule from the policy.

## 8. Keep the index
`references/agentspace/index.md` is the map of agentspace. It ships empty (headers only) and is filled in on the user's system. It is the first agentspace file read at Start, so it stays short: one row per file, with no content copied from the files.

```markdown
# Agentspace index
Updated: <YYYY-MM-DD>

## Adapters
| File | Host | Detect | Strategy | Verified |
| :--- | :--- | :--- | :--- | :--- |
| `claude-code.md` | Claude Code | Bash/Read tools; skills in ~/.claude/skills | A | <YYYY-MM-DD> |

## Other files
| File | Purpose | Read when |
| :--- | :--- | :--- |
| `preferences.md` | How the user likes reflections and options laid out | Before presenting a reflection |
```

Rules:
- **Same change.** Every change that adds, removes, renames, or repurposes an agentspace file also updates the index in the same change, under the same yes. Update `Updated:` each time.
- **Shared files belong to no host.** Preferences, roster notes, and domain rules are about the user, not a host. List them once, under "Other files", so every adapter's host sees them.
- **Mismatch means stop.** If the index and the folder disagree, report what differs and propose a fix to the index. Do not act on a file the index does not describe.
- **Rebuilding.** If `index.md` is missing or damaged, rebuild it from each file's `Detect:`, `Verified:`, `Strategy:`, and `Purpose:` lines. Propose the result like any other change. Where a file has no `Purpose:` line, ask the user what it is for.
- **The index is not a rule source.** It only points to files. Rules live in the files, and the policy still overrides them all.

## Known traps (seen on real hosts)
- **Direct edits.** With the-one-skill loaded, a model still edited a skill's `SKILL.md` directly with its Edit tool, in auto mode and without a yes. Install the guard wherever the host allows it.
- **Edits that drop files.** Sending only `content` to an edit tool replaced the whole skill with a single `SKILL.md`, and `references/` was lost. Send the whole folder when the tool allows it, and check the file list afterwards.
- **False reports.** A tool said "updated" when nothing changed, or claimed an ability it did not have. List or read back after every action.
- **Name collisions.** When a name is taken, hosts may offer to "update the existing skill". Choose a different name instead.
- **Sandboxed code.** Code can run in a sandbox that cannot see the skills, or that sees copies of them. Stage files explicitly, or use strategy B.
- **Writable copies.** ChatGPT showed each skill to code as a writable folder named by an ID (`remote-skills/skill-<id>`) on an overlay mount, and the model had no tool to save skills. Nothing showed that writes there reach the installed skill. `skillctl.py apply` refused only because the folder name didn't match the skill's name. Without that check it could have reported a change that was never saved. Confirm in a new session that a change lasts (§2) before choosing A.
- **Stale loading.** Changed skills often load only in a new session.
- **Store inside the skills folder.** The host then loads stored copies as extra skills. Keep the store outside.
- **Permission policies that block commands.** Besides prompts, a host can block commands outright with an automatic policy (for example Claude Code's auto mode), which reads a script that replaces skill folders as destructive. When you build the adapter, check whether such a policy is active. If it is, offer the user the exact allow rule for the helper before the first change, for example `Bash(python3 /abs/path/to/the-one-skill/scripts/skillctl.py:*)` in the project's `.claude/settings.local.json`. Record the rule in the adapter. If a command is still blocked, stop and give the user the exact command to run themselves. Never look for another route.
- **Permission prompts on skill folders.** Some hosts ask the user before every write to the folders that hold skills, even when edits are otherwise auto-approved. Claude Code does this for anything under `.claude/`. Record it in the adapter. Before applying, tell the user in a few words how many prompts to expect. Group writes so there are as few prompts as possible: build the draft completely, then apply it once. Never route around a prompt with shell commands or other tools. A declined prompt means no.
- **Skills that are git checkouts.** Keep `.git` (skillctl does this). Mention that git will show the change as uncommitted.
