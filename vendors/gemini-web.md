# Host Adapter: Gemini Web (`gemini-web`)

This guide defines how `the-one-skill` operates inside **Gemini Web** (the Gemini app). `skillctl.py` cannot run here: the Python sandbox has no access to your skills. Gemini's own skill tools are used instead.

## 1. What Gemini Can and Cannot Do (Tested)

| Ability | Result |
| :--- | :--- |
| Create a skill from chat | Yes |
| Edit a skill from chat | Yes, but it **overwrites the skill with no history or backup** |
| Disable / enable a skill | Yes |
| Two skills with the same name | No: names are unique |
| Rename a skill | No |
| Delete a skill | No: only the user can, in skill settings |

Gemini only uses enabled skills automatically. Its descriptions of its own abilities have been wrong before, so after every create, disable, or enable, confirm the skill's actual state (ask Gemini to list skills and their status) before reporting success.

## 2. The Swap Model on Gemini

Because names are unique and edits are destructive, the working copy uses a fixed suffix:

- **First refinement of `<name>`:** Create a new skill `<name>-tuned` containing the original's content plus the approved change (show the full diff first). Confirm it exists, then **disable `<name>`**. Never edit `<name>` itself.
- **Later refinements:** Edit only `<name>-tuned`, after showing the diff and getting approval.
- **Revert:** Disable `<name>-tuned`, enable `<name>`. **Reapply:** the reverse.
- **No step-back undo:** edits to `<name>-tuned` are not versioned, so the only undo is a full revert to the original.
- **Retire:** disable the skill. Point the user to skill settings if they want it permanently deleted.
- **Merge A + B into C:** create C, confirm it, then disable A and B. Revert: disable C, enable A and B.

## 3. Hard Rules

1. Never edit a skill that does not end in `-tuned` (or that `the-one-skill` did not create).
2. If Gemini reports that a name already exists, always choose "create with a different name"; never "update the existing skill".
3. If an operation is not possible, stop and ask the user. Never substitute a different action (for example, disabling when asked to delete).
4. Never ask Gemini to delete a skill.
5. Before the first refinement of a skill, suggest the user download the original from the Skills page as an offline backup.

## 4. Roster Memory

There is no manifest file on Gemini Web. Keep a roster in **Gemini Memory**, e.g. `the-one-skill roster: csv-inspector=original(disabled), csv-inspector-tuned=working(enabled), legacy-tax=locked`. Check Memory first to avoid reading unrelated skills, and update it after every swap.

## 5. Sandbox Constraints (Python Stdlib Only, No Outbound VM Network)

- The code execution environment only runs Python and has no outbound internet access. Never invoke `pip install`, `curl`, `wget`, or non-Python runtimes.
- **Discover:** use Gemini's built-in browsing to read the trusted repositories, write candidate files into the sandbox (`/tmp/staged/<skill-name>/`), and run:
  ```bash
  python3 scripts/lint_skills.py --check-source-url <candidate_url>
  python3 scripts/lint_skills.py /tmp/staged/<skill-name>
  ```
  Only after both pass and the user approves, create the skill through Gemini's skill tools.
- Sandbox files do not persist between sessions; never rely on them as a backup.
