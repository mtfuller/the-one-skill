# Managing the Skill Roster

The roster is every skill available on the host. All roster changes follow the same rules as improvements: say in plain language what will change, get one yes, verify, and keep it reversible. Show diffs and exact steps only when the user asks. The adapter says how each operation is done on this host. On strategy A, the `skillctl.py` commands are listed after each operation.

## Review the roster
1. List every skill with its name, enabled state, source (the user's own, created by the-one-skill, installed from outside, or protected), and its managed state. On strategy A, `list --json` and `status` give you this, and `list` also flags structural problems.
2. Check for:
   - **Overlap:** descriptions that would trigger on the same request, including overlap with protected built-in skills. Propose a merge, or sharpen each skill's "Use when / Do not use when".
   - **Vague triggers:** a description that never says when to use the skill. Propose a rewrite.
   - **Broken structure:** a missing `SKILL.md`, a frontmatter `name` that differs from the folder, an invalid name, or a `SKILL.md` over 500 lines (move detail into `references/`).
   - **Gaps:** a workflow from this or recent sessions that no skill covers. Offer to create one, or to find one (below).
   - **Dead weight:** skills the user says they no longer use.
3. Give a short table (skill · what's wrong · what you'd do), in plain words, and end with one question: do all, some, or none. Nothing changes until the user answers.

## Operations

| Operation | How (always with approval) | Strategy A |
| :--- | :--- | :--- |
| **Improve** | The Improve steps in `SKILL.md`. | `draft` → edit → `apply` (`diff` if asked) |
| **Create** | Check that the name is free. Describe what the new skill will do, and create it after a yes. Show its files if asked. Track it as created by the-one-skill, so going back to vanilla can find it. | `new <name>` → write files → `apply` |
| **Find and install** | See below. | `new <name> --from <folder>` |
| **Merge** | See below. | `new` or `draft`, then `retire` each |
| **Split** | Create the new skill, then improve the old one to narrow its scope and point to the new one. | `new`, then `draft` |
| **Rename** | Names are identities. Create the new name with the same files, then retire the old one. | `new --from`, then `retire` |
| **Retire** | Reversible removal. On strategy B, disable the skill. On C or D, tell the user how to do it. | `retire` |
| **Restore** | Bring a retired skill back. Refuse if the name is now taken by another skill. | `restore` |
| **Step back** | Undo the latest change to one skill but keep earlier ones. Check what is kept first: never promise a version that the store does not have. | `history`, `use previous` |
| **Back to vanilla** | See below. | |

Run every operation that touches more than one skill (merge, split, rename, back to vanilla, installing several skills) as one **change set** (below), so it can be undone in one step.

## Find and install a skill from a trusted source
Use this when the user wants an existing skill rather than one written for them, or when a gap is generic enough that someone has probably already solved it.

1. **Reflect first.** If the friction came from repeated corrections, name them. Say whether the fix could also be a small change to a skill the user already has. Offer both paths.
2. **Search only trusted sources**, in this order:
   1. the host's own skill or plugin directory
   2. sources listed in `agentspace/sources.md`
   3. official repositories from the vendor whose tool the skill covers

   Anything else is a community source. Name it as one, and include it only if the user asks for more. If `sources.md` doesn't exist yet, offer to create it with the sources the user trusts.
3. **Compare candidates against the user's actual corrections.** Use a table: which corrections each candidate fixes, which it doesn't, who publishes it, and when it was last updated. Be honest when nothing covers everything, and say what would close the gap (a small local addition, a hook, or a rule).
4. **Read before installing (policy invariant 11).** Read every file of the chosen skill. Summarize its instructions, scripts, network access, and anything it would run or install. Flag anything that reaches beyond its stated purpose.
5. **Install as a new skill** after a yes. Show the files if asked. Install through the host's own installer if it has one, or else as a created skill (strategy A: `new <name> --from <folder>`, then `apply <name> --note "<source> <version>"`).
6. **Verify.** Confirm the skill is listed and enabled. Tell the user it loads in a new session, and that retiring it undoes the install.

Never install from a source the user hasn't approved. Never run a skill's scripts in order to evaluate it.

## Merge several skills
1. **Read every skill involved, including its references.** Also list protected skills that cover the same ground (for example a built-in skill for the same file type). Protected skills are never merged. The merged skill should defer to them, or say how it differs from them.
2. **Find conflicts between the skills**, such as two different fonts or two different limits. Pick a default for each and name it in your one message ("Arial everywhere, replacing the timeline skill's Calibri"). The user's yes covers it, or they say otherwise.
3. **Choose the target.** Improve one existing skill if its name and scope still fit. Otherwise create a new skill with a name that covers the whole job. Bring over every reference file that is still needed.
4. **Write a description that triggers on every request the old skills did**, plus "Do not use when" lines for anything a protected skill should handle.
5. **Propose it as one change set:** the new or changed skill, plus retiring each of the others. Apply every step under the same set name, and verify it. Undoing it means restoring each retired skill and retiring the new one (or stepping the target back), in reverse order.

## Back to vanilla
Use this when the user wants every skill as it was before the-one-skill changed anything.

1. **Take an inventory:**
   - skills with a kept original that are not currently on it
   - retired skills
   - skills the-one-skill created or installed (`status` shows "created")
   - skills edited by hand
2. **Give a short table** (skill · now · after) in plain words, covering:
   - put each skill back on its original
   - restore each retired skill
   - retire each skill the-one-skill created or installed
   - **ask** about hand-edited skills, because their edits are the user's own work
   - leave untouched any skill the-one-skill never changed
3. **Revert the-one-skill last**, as its own decision. Its original has no adapter or notes, so reverting it means the next session starts from a fresh install. Offer to keep the-one-skill as it is.
4. **Apply as one change set** and verify every skill. Nothing is deleted, so every tuned version can still be switched back in.

## Change sets
A change set groups the steps of one multi-skill change so it can be undone in one step. The tool keeps the record, outside the skills. Never keep a hand-written log for this.

- **Strategy A:** give every step the same `--set <name>` (and one `--note "<why>"`), for example `apply proposal-deck --set merge-proposal-decks --note "4 PPTX skills overlapped"`, then `retire pptx-timeline-slides --set merge-proposal-decks`. `sets` lists them.
- **Undo:** `undo-set <name>` lists the reverse steps, newest first, and changes nothing. Tell the user in plain words what will come back and what will go away, then run `undo-set <name> --apply` after a yes. It refuses if any skill changed after the set or a needed version is no longer kept. In that case, explain which and propose the remaining steps one by one.
- **Other strategies:** there is no store to record in. List the exact reverse steps in your reply when the change is applied, and tell the user that this list is the only record.
- **Undoing one rule or one change:** find it with `history <skill>` (and `diff` against kept versions), then pick the smallest undo, in this order:
  1. step that skill back
  2. a new change that removes just that rule
  3. revert the whole skill to its original, only if nothing else depends on it

## Rules
- **Protected skills** (see the adapter) are never merged, renamed, retired, or edited. You can still flag their overlap with other skills and propose changes to the user's own skills instead.
- **Delete means retire.** If the user wants a skill permanently gone, retire it and tell them where the host lets them delete it. Never substitute an action without saying so.
- **One change at a time inside a change set.** Verify each step before starting the next, and stop if one fails. Report how far the set got and how to undo that part.
