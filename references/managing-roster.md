# Managing the Skill Roster

The roster is every skill available on the host. All roster changes follow the same rules as improvements: say in plain language what will change, get one yes, verify, and keep it reversible. Show diffs and exact steps only when the user asks. The adapter says how each operation is done on this host. On strategy A, the `skillctl.py` commands are listed after each operation.

## Review the roster
1. **Leave the-one-skill out.** It is the reviewer, not one of the skills under review. Don't list it in the table or propose changes to it, unless the user asks to review it or it clearly caused friction in this session (then one line at most). The same goes for its setup files.
2. List every other skill with its name, enabled state, source (the user's own, created by the-one-skill, installed from outside, or protected), and its managed state. On strategy A, `list --json` and `status` give you this, and `list` also flags structural problems.
3. Check for:
   - **Overlap:** descriptions that would trigger on the same request, including overlap with protected built-in skills. Propose a merge, or sharpen each skill's "Use when / Do not use when".
   - **Vague triggers:** a description that never says when to use the skill. Propose a rewrite.
   - **Broken structure:** a missing `SKILL.md`, a frontmatter `name` that differs from the folder, an invalid name, or a `SKILL.md` over 500 lines (move detail into `references/`).
   - **Gaps:** a workflow from this or recent sessions that no skill covers. Offer to create one, or to find one (below).
   - **Dead weight:** skills the user says they no longer use.
4. Give a short table (skill · what's wrong · what you'd do), in plain words, and end with one question: do all, some, or none. Nothing changes until the user answers.

## Operations

| Operation | How (always with approval) | Strategy A |
| :--- | :--- | :--- |
| **Improve** | `references/improving.md`. | `draft` → edit → `apply` (`diff` if asked) |
| **Create** | Check that the name is free. Describe what the new skill will do, and create it after a yes. Show its files if asked. Track it as created by the-one-skill, so going back to vanilla can find it. | `new <name>` → write files → `apply` |
| **Find and install** | See below. | `new <name> --from <folder>` |
| **Merge** | See below. | `new` or `draft`, then `retire` each |
| **Split** | Create the new skill, then improve the old one to narrow its scope and point to the new one. | `new`, then `draft` |
| **Rename** | Names are identities. Create the new name with the same files, then retire the old one. | `new --from`, then `retire` |
| **Retire** | Reversible removal. On strategy B, disable the skill. On C or D, tell the user how to do it. | `retire` |
| **Restore** | Bring a retired skill back. Refuse if the name is now taken by another skill. | `restore` |
| **Step back** | Undo the latest change to one skill but keep earlier ones (`references/undoing.md`). | `history`, `use previous` |
| **Back to vanilla** | `references/undoing.md`. | |

Run every operation that touches more than one skill (merge, split, rename, back to vanilla, installing several skills) as one **change set** (`references/undoing.md`), so it can be undone in one step.

## Find and install a skill from Anthropic, OpenAI, or Google
Use this when the user wants an existing skill rather than one written for them, or when a gap is generic enough that someone has probably already solved it.

1. **Reflect first.** If the friction came from repeated corrections, name them. Say whether the fix could also be a small change to a skill the user already has. Offer both paths.
2. **Search only skills that Anthropic, OpenAI, or Google publish** (policy invariant 11):
   - their skill directories in their own products (Claude, ChatGPT, Gemini), counting only the skills the company itself publishes there
   - their official repositories, such as the `anthropics`, `openai`, `google`, and `google-gemini` organizations on GitHub

   Check the publisher from where the skill actually lives (the organization or the directory's publisher field), never from what its name or description claims. No other source counts, even if the user names one or asks for more. If none of the three publishes a fitting skill, say so plainly, and offer to write one or to change a skill the user already has. If the user wants a skill from somewhere else, they can install it themselves, outside the-one-skill.
3. **Compare candidates against the user's actual corrections.** Use a table: which corrections each candidate fixes, which it doesn't, who publishes it, and when it was last updated. Be honest when nothing covers everything, and say what would close the gap (a small local addition, a hook, or a rule).
4. **Read before installing (policy invariant 11).** Read every file of the chosen skill. Summarize its instructions, scripts, network access, and anything it would run or install. Flag anything that reaches beyond its stated purpose.
5. **Install as a new skill** after a yes. Show the files if asked. Install through the host's own installer if it has one, or else as a created skill (strategy A: `new <name> --from <folder>`, then `apply <name> --note "<source> <version>"`).
   - **Install it exactly as published first.** Any tweaks (the user's requests, or removing something you flagged) go in afterwards as a separate change, under the same change set. Then the kept versions are "as published" and "with tweaks", so "undo my tweaks" leaves the published skill in place, and an update from the source can be compared with what was installed. One yes covers both steps.
6. **Verify.** Confirm the skill is listed and enabled. Tell the user it loads in a new session, and that retiring it undoes the install.

Never install a skill that Anthropic, OpenAI, or Google didn't publish. Never run a skill's scripts in order to evaluate it.

## Merge several skills
1. **Read every skill involved, including its references.** Also list protected skills that cover the same ground (for example a built-in skill for the same file type). Protected skills are never merged. The merged skill should defer to them, or say how it differs from them.
2. **Find conflicts between the skills**, such as two different fonts or two different limits. Pick a default for each and name it in your one message ("Arial everywhere, replacing the timeline skill's Calibri"). The user's yes covers it, or they say otherwise.
3. **Choose the target.** Improve one existing skill if its name and scope still fit. Otherwise create a new skill with a name that covers the whole job. Bring over every reference file that is still needed.
4. **Write a description that triggers on every request the old skills did**, plus "Do not use when" lines for anything a protected skill should handle.
5. **Propose it as one change set:** the new or changed skill, plus retiring each of the others. Apply every step under the same set name, and verify it. Undoing it means restoring each retired skill and retiring the new one (or stepping the target back), in reverse order.

## Rules
- **Protected skills** (see the adapter) are never merged, renamed, retired, or edited. You can still flag their overlap with other skills and propose changes to the user's own skills instead.
- **Delete means retire.** If the user wants a skill permanently gone, retire it and tell them where the host lets them delete it. Never substitute an action without saying so.
- **One change at a time inside a change set.** Verify each step before starting the next, and stop if one fails. Report how far the set got and how to undo that part.
