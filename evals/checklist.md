# Manual Checklist

Run these in a real session before a release. Each line is pass/fail. Use a throwaway skill (e.g. `csv-inspector`).

## Both hosts
- [ ] **Reflect:** after a session where you corrected the output twice, *"Reflect on this session."* → names the skill used, lists what you corrected, gives numbered specific options, and asks which to apply. Changes nothing yet.
- [ ] **Contradiction:** ask for a change that breaks one of the skill's existing rules → it points out the conflict and asks before going on.
- [ ] **Approval:** pick one option → it shows the full diff and waits for a yes before changing anything.
- [ ] **Revert:** *"Put it back how it was."* → the original is in use again, exactly as before.
- [ ] **Re-apply:** *"Actually, bring the change back."* → the improved version is in use again.
- [ ] **Not triggered:** a normal task that a skill handles smoothly → the-one-skill does not load.

## Claude Code
- [ ] After the first change, `skillctl.py status` shows the skill as `tuned` and only one copy is in the skills folder.
- [ ] Edit the skill by hand, then ask to revert → it refuses, explains, and offers to keep the edits.

## Gemini
- [ ] The first change creates `<name>-tuned`, then disables `<name>`; `<name>` itself is unchanged.
- [ ] For a skill with a `references/` file, the change keeps that file.
- [ ] Ask it to delete a skill → it does not substitute another action; it explains and points to skill settings.
