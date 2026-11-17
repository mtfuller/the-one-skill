# Host Guide: Gemini

Gemini skills are changed only through Gemini's own skill tools. No scripts are needed.

## What Gemini's skill tools can and cannot do (tested)

| Ability | Result |
| :--- | :--- |
| Create a skill from chat | Yes |
| Edit a skill from chat | Yes, but it **overwrites the skill with no history or backup** |
| Disable / enable a skill | Yes |
| Two skills with the same name | No: names are unique |
| Rename a skill | No |
| Delete a skill | No: only the user can, in skill settings |

Gemini's descriptions of its own abilities have been wrong before. After every create, edit, disable, or enable, list the skills and their status to confirm what actually happened before telling the user it worked.

## Improving a skill (Step 6): keep the original, work on `<name>-tuned`

Because edits overwrite and names are unique, the improved version is a separate skill with a fixed suffix:

- **First change to `<name>`:** suggest the user download `<name>` from the Skills page as an offline backup. Create a new skill `<name>-tuned` with the original's content (every file) plus the approved change, after showing the full diff. Confirm it exists, then **disable `<name>`**. Never edit `<name>` itself.
- **Later changes:** edit only `<name>-tuned`, after showing the diff and getting a yes. Its previous version is replaced (there is no step-back undo; revert goes to the original).
- **Status:** a skill with a `-tuned` twin is managed by the-one-skill; whichever of the two is enabled is the one in use.

## Reverting (Step 7)
Disable `<name>-tuned`, enable `<name>`. To bring the improvement back: the reverse.

## Creating a new skill
Check that the name is free, show the full `SKILL.md`, and create it after the user approves.

## Rules
1. Never edit a skill unless its name ends in `-tuned` or the-one-skill created it.
2. If Gemini says a name already exists, choose "create with a different name", never "update the existing skill".
3. Never ask Gemini to delete a skill. To retire one, disable it and point the user to skill settings if they want it gone.
4. **Skills with more than `SKILL.md`:** if the update tool accepts either the whole content or a skill folder, use the folder (with `SKILL.md` at its root, plus every reference file). Sending only `content` replaces the skill with a single file and deletes its other files.
5. Check the tool's result (for example `status: "updated"`) before telling the user it worked.
