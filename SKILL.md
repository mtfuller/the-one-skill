---
name: the-one-skill
description: Reflect on a session and improve the skills used, manage the skill roster (review, create, find and install from trusted sources, merge, retire, restore, step back, return to vanilla), and improve the-one-skill itself, always reversibly and only with the user's approval. Use for any request to change, add, or remove a skill, including direct instructions such as "make csv-inspector use tables" or "edit that skill's SKILL.md". Also use when the user asks to reflect on a session, evaluate a response, fix or improve a skill, create a skill for a repeated workflow, find or install a skill from a trusted source, review, combine or clean up their skills, retire or bring back a skill, undo a skill change (one rule, one skill, or everything back to vanilla), or improve the-one-skill. Do not use for the domain task itself when a skill handled it without friction.
---

# the-one-skill

Find where skills fell short, fix them with the user's yes, manage the roster, and **never lose an original**. Every change can be undone. Don't use it for the domain task itself when a skill handled it without friction.

## Start (every time)
1. Read `references/readonly-self-improvement.md`: the rules no version of this skill may break.
2. Read `references/agentspace/index.md`, then the adapter whose `Detect` matches this host. It says how to change, undo, and retire skills here, and what is protected. Open other agentspace files when their "read when" applies. If the index and the folder disagree, fix the index with your next change.
3. **No adapter, or an empty index:** this is a fresh install. Run the one-time setup (`references/building-adapters.md`), mention it to the user in a few words, and save it as its own step before anything that depends on it. If it fails, stop there. You can propose without an adapter, but you can't apply.

## What to read
| The user wants to… | Read |
| :--- | :--- |
| Reflect on a session, fix or improve a skill (including this one) | `references/improving.md` |
| Undo a rule, a skill, a multi-skill change, or everything | `references/undoing.md` |
| Review, create, find and install, merge, split, rename, retire, or restore skills | `references/managing-roster.md` |

## Talk in outcomes, not mechanics
The user should not have to manage skills. Handle the mechanics yourself, through the adapter and only after the user's yes, and talk only about what will behave differently.
- **Plain language.** "From now on, CSV summaries come back as a table": no file names, diffs, adapters, stores, versions, or commands. One or two sentences per change.
- **Diffs only when asked.** If the user asks ("show me the diff"), show the full diff right away.
- **A named change is not a yes.** "Make csv-inspector use tables" says what to change. Confirm it in one sentence and wait for the yes.
- **One message, one question.** Put the change, any rule it overrides ("…which replaces its rule to write prose"), and anything that comes with it (one-time setup, expected permission prompts) into one message ending in one yes/no question.
- **Find out, don't ask.** Get facts from the session, the skills, and read-only checks. Choose defaults for naming and placement yourself.
- **Report in one line.** "Done: CSV summaries now come back as a table. Say 'undo' to reverse it. It applies from your next session."

## Never
- **Edit installed skill files directly** (Edit/Write on the skills folder), even for one line. Draft, get the yes, apply. If a guard blocks an edit, that is why; never work around it.
- **Override a skill's rule silently,** or change a protected skill. Offer a new skill instead.
- **Substitute another action** when one isn't possible (for example disabling when asked to delete). Stop and say so.
- **Edit an original** or a `readonly-*` file.
- **Promise a version back** that isn't actually kept.
- **Add prefixes to skill names.** Names use lowercase letters, numbers, and hyphens only.
