# Host Adapter: Gemini Web (`gemini-web`)

This guide defines how `the-one-skill` operates inside **Gemini Web** (the Gemini app). Skills are always changed through Gemini's own skill tools, never with `skillctl.py` (see §2).

## 1. Chat Mode vs. Task Mode

Gemini Web has two modes, and only one can run code:

| | **Chat** | **Task** |
| :--- | :--- | :--- |
| Code execution | No | Yes |
| the-one-skill's `scripts/` reachable | No | Yes (tested) |
| Installed skills readable as files | No | Yes (tested) |

At the start of every the-one-skill action, run `python3 scripts/lint_skills.py --self-check`. If it cannot run, you are in Chat mode: say so, and say which checks will be skipped.

| Operation | Chat mode | Task mode |
| :--- | :--- | :--- |
| Refine / revert / reapply / retire / merge (§4) | Allowed: Gemini skill tools plus a full diff shown to the user, with a manual lint check (`references/evolve.md` §3) | Allowed, with the automated lint: copy the draft into `/tmp/draft/<name>/` and run `lint_skills.py` on it |
| Install a skill from outside (Discover) | **Stop** and ask the user to switch to Task mode (`references/discover.md` step 0) | Allowed with the full security and lint gate |
| Status / overlap audit | Read skill descriptions only | Run `lint_skills.py` on the installed skill files for token counts and overlaps |
| Export | Not available | Allowed |

## 2. Why Not `skillctl.py` in Task Mode?

Task mode can read installed skills as files, but it is **not yet verified** that (a) writing to those files changes the skill on the Skills page, or (b) anything written outside them (the store) survives to the next session. Until both are tested, use the Gemini swap rules below even in Task mode: the disabled original is the only backup that is known to persist.

## 3. What Gemini's Skill Tools Can and Cannot Do (Tested)

| Ability | Result |
| :--- | :--- |
| Create a skill from chat | Yes |
| Edit a skill from chat | Yes, but it **overwrites the skill with no history or backup** |
| Disable / enable a skill | Yes |
| Two skills with the same name | No: names are unique |
| Rename a skill | No |
| Delete a skill | No: only the user can, in skill settings |

Gemini only uses enabled skills automatically. Its descriptions of its own abilities have been wrong before, so after every create, disable, or enable, confirm the skill's actual state (ask Gemini to list skills and their status) before reporting success.

## 4. The Swap Model on Gemini

Because names are unique and edits are destructive, the working copy uses a fixed suffix:

- **First refinement of `<name>`:** Create a new skill `<name>-tuned` containing the original's content plus the approved change (show the full diff first). Confirm it exists, then **disable `<name>`**. Never edit `<name>` itself.
- **Later refinements:** Edit only `<name>-tuned`, after showing the diff and getting approval.
- **Revert:** Disable `<name>-tuned`, enable `<name>`. **Reapply:** the reverse.
- **No step-back undo:** edits to `<name>-tuned` are not versioned, so the only undo is a full revert to the original.
- **Retire:** disable the skill. Point the user to skill settings if they want it permanently deleted.
- **Merge A + B into C:** create C, confirm it, then disable A and B. Revert: disable C, enable A and B.

## 5. Hard Rules

1. Never edit a skill that does not end in `-tuned` (or that `the-one-skill` did not create).
2. If Gemini reports that a name already exists, always choose "create with a different name"; never "update the existing skill".
3. If an operation is not possible, stop and ask the user. Never substitute a different action (for example, disabling when asked to delete).
4. Never ask Gemini to delete a skill.
5. Before the first refinement of a skill, suggest the user download the original from the Skills page as an offline backup.

## 6. Roster Memory

There is no manifest file on Gemini Web. Keep a roster in **Gemini Memory**, e.g. `the-one-skill roster: csv-inspector=original(disabled), csv-inspector-tuned=working(enabled), legacy-tax=locked`. Check Memory first to avoid reading unrelated skills, and update it after every swap.

## 7. Sandbox Constraints (Python Stdlib Only, No Outbound VM Network)

- The code execution environment only runs Python and has no outbound internet access. Never invoke `pip install`, `curl`, `wget`, or non-Python runtimes.
- **Discover (Task mode only):** use Gemini's built-in browsing to read the trusted repositories, write candidate files into the sandbox (`/tmp/staged/<skill-name>/`), and run:
  ```bash
  python3 scripts/lint_skills.py --check-source-url <candidate_url>
  python3 scripts/lint_skills.py /tmp/staged/<skill-name>
  ```
  Only after both pass and the user approves, create the skill through Gemini's skill tools.
- Sandbox files do not persist between sessions; never rely on them as a backup.
