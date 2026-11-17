# Host Adapter: Gemini Web (`gemini-web`)

This guide defines how `the-one-skill` operates inside **Gemini Web** (the Gemini app). Skills are always changed through Gemini's own skill tools, never with `skillctl.py` (see §2).

## 1. Chat Mode vs. Task Mode

Gemini Web has two modes, and only one can run code:

| | **Chat** | **Task** |
| :--- | :--- | :--- |
| Code execution (Python, stdlib and pre-installed packages, no internet) | No | Yes |
| Skill files inside the sandbox | No | No: Gemini reads a skill's files through its skill tools and can copy them into the sandbox |
| Changes to sandbox copies saved back to the skill | No | No |

**Staging the-one-skill's scripts (Task mode).** Skill files are not mounted in the sandbox, so before any script runs, read `scripts/lint_skills.py` and `scripts/export_diff.py` from `the-one-skill` through the skill tools, write them unchanged to `/tmp/the-one-skill/scripts/`, and run `python3 /tmp/the-one-skill/scripts/lint_skills.py --self-check`. Do the same for any skill being linted: copy its files to `/tmp/skills/<name>/` first. Re-stage in each new session; sandbox files do not persist.

If no code can run at all, you are in Chat mode: say so, and say which checks will be skipped.

| Operation | Chat mode | Task mode |
| :--- | :--- | :--- |
| Refine / revert / reapply / retire / merge (§4) | Allowed: Gemini skill tools plus a full diff shown to the user, with a manual lint check (`references/evolve.md` §3) | Allowed, with the automated lint: write the draft to `/tmp/draft/<name>/` and run the staged `lint_skills.py` on it |
| Install a skill from outside (Discover) | **Stop** and ask the user to switch to Task mode (`references/discover.md` step 0) | Allowed with the full security and lint gate |
| Status / overlap audit | Read skill descriptions only | Copy installed skills to `/tmp/skills/` and run the staged `lint_skills.py` on them for token counts and overlaps |
| Export | Not available | Allowed |

## 2. Why Not `skillctl.py`?

Gemini skills live in Gemini's own storage and are reached only through its skill tools. The sandbox only ever holds copies: editing them does not change a skill, and they disappear when the session ends. `skillctl.py` manages folders on disk, so it cannot manage Gemini skills in either mode. Use the swap rules in §4; the disabled original is the only backup that persists.

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
  python3 /tmp/the-one-skill/scripts/lint_skills.py --check-source-url <candidate_url>
  python3 /tmp/the-one-skill/scripts/lint_skills.py /tmp/staged/<skill-name>
  ```
  Only after both pass and the user approves, create the skill through Gemini's skill tools.
- Sandbox files do not persist between sessions; never rely on them as a backup.
