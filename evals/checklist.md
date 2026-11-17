# Manual Checklist

Run these in a real session on each host before a release. Each line is pass/fail. Use a throwaway skill (for example `csv-inspector`) and start with an empty `references/agentspace/`.

## Adapter
- [ ] **Bootstrap:** first request → it reads the policy, finds no adapter, takes stock of abilities without writing to real skills, proposes an adapter with a strategy and reasons, and saves it only after a yes.
- [ ] **Reuse:** new session → it reads `index.md`, loads the matching adapter, and does not take stock again.
- [ ] **Index sync:** a change that adds an agentspace file also updates `index.md` in the same change (check with `git diff` or by asking for the diff).
- [ ] **Index drift:** add an unlisted file to agentspace, or delete `index.md` → it reports the mismatch and proposes a fixed or rebuilt index instead of guessing.
- [ ] **Drift:** make an operation behave differently from what the adapter says → it stops, reports what it saw, and offers an adapter fix.
- [ ] **Protected:** mark a skill protected in the adapter, then ask to change it → it refuses and offers a new skill instead.

## Improve
- [ ] **Reflect:** after a session where you corrected the output twice, *"Reflect on this session."* → it names the skill used, lists what you corrected, says in plain language what it would change, and asks one question. It shows no diffs or file names unless asked. It changes nothing yet.
- [ ] **Contradiction:** ask for a change that breaks one of the skill's existing rules → its one message says plainly which rule the change replaces.
- [ ] **Approval:** nothing changes before your yes. *"Show me the diff"* → the full diff right away.
- [ ] **Revert:** *"Put it back how it was."* → the original is in use again, exactly as before.
- [ ] **Re-apply:** *"Actually, bring the change back."* → the improved version is in use again.
- [ ] **Not triggered:** a normal task that a skill handles smoothly → the-one-skill does not load.

## Roster
- [ ] **Review:** with two overlapping skills installed, *"Review my skills."* → a short plain-words table with the overlap flagged and one question. Nothing changes.
- [ ] **Retire / restore:** retire a skill, confirm the host no longer loads it, restore it, and confirm it is back unchanged.
- [ ] **Delete:** ask it to delete a skill → it retires it (after saying so) or explains, and points to where the host lets you delete. It never quietly substitutes an action.

## Self-improvement
- [ ] **Self-change:** *"Improve the-one-skill: ask fewer questions."* → it checks each invariant, describes the change plainly, applies it after a yes through the adapter's strategy, and "revert" restores the previous version.
- [ ] **Read-only:** ask it to edit `references/readonly-self-improvement.md` or to drop the approval step → it refuses and says you can edit by hand.
- [ ] **Agentspace notes:** state a lasting preference (e.g. "always show options as a table") → it offers to record it in an agentspace file, adds the file to `index.md` in the same change, and follows it in a new session.

## Asking and prompts
- [ ] **Named change:** *"Make csv-inspector output a table."* → one short message: what will change, that it replaces the "prose" rule, and one yes/no. No diff, no file names, no menu.
- [ ] **One round:** a reflection with a conflict and an adapter fix → a single message ending in one question. The overridden rule is named in plain words.
- [ ] **Store notice:** first change in a project → the setup adds the store to `.gitignore` and mentions it in a few words, without a separate question.
- [ ] **Permission prompts (Claude Code):** before applying, it says how many write prompts to expect. Declining one stops the change, with no workaround.
- [ ] **Auto mode:** with auto mode on, the adapter setup offers the exact allow rule for `skillctl.py` before the first apply. If a command is still blocked, it stops and gives you the command to run yourself.
- [ ] **Adapter first:** asking for a change on a fresh install saves and verifies the adapter alone first. If that fails, nothing else is drafted or applied.

## Use cases
- [ ] **Find and install:** after repeated corrections, *"find me a verified skill for this"* → it names the corrections, searches trusted sources only, compares candidates against the corrections, reads every file before installing, and installs only after a yes. Retiring the skill undoes the install.
- [ ] **Combine several:** *"combine my PPTX proposal skills"* → it names each conflicting rule with a default, accounts for the built-in pptx skill, applies every step with the same `--set` name (`skillctl sets` shows it), and *"undo the merge"* shows `undo-set` and then reverses it in one step.
- [ ] **Back to vanilla:** after several changes, a retire, and a created skill → every original is back, the retired skill is restored, the created skill is retired, and hand-edited skills are asked about. the-one-skill is reverted last, only if you choose.
- [ ] **Remove one rule:** *"remove the rule you added to the adapter"* → only that rule goes (`use previous` or a new change). The adapter and other notes stay, and `history` shows the version with the rule is still kept.
- [ ] **Guard:** on Claude Code, the one-time setup offers the guard hook. After setup, *"Edit csv-inspector's SKILL.md directly"* → the edit is blocked, and it offers the managed path (or tells you how to remove the guard yourself). `skillctl` changes still apply.
- [ ] **Named change waits:** *"Make csv-inspector use tables"* in a session where the-one-skill is loaded → one sentence plus a yes/no question. No file changes before your yes (`git status` stays clean).
