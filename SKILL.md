---
name: the-one-skill
description: Reflect on a session and improve the skills used, manage the skill roster (review, create, merge, retire, restore), and improve the-one-skill itself, always reversibly and only with the user's approval. Use when the user asks to reflect on a session, evaluate a response, fix or improve a skill, create a skill for a repeated workflow, review or clean up their skills, retire or bring back a skill, undo a skill change, or improve the-one-skill. Do not use for the domain task itself when a skill handled it without friction.
---

# the-one-skill

Look back at a session, find where skills fell short, propose concrete fixes, and apply the ones the user approves **without ever losing the original skill**. Every change can be undone. The same discipline covers managing the whole roster and improving this skill.

## When to Use
- The user asks to reflect on a recent session or evaluate a response.
- The user had to correct the output, repeat themselves, or work around a skill.
- The user asks to improve, fix, or evolve a skill, including this one.
- A workflow keeps repeating and no skill covers it.
- The user wants to review, tidy, merge, retire, or restore skills.
- The user asks to undo a skill change ("put it back", "revert that").

## Do not use when
- Doing the task a skill is for, when it went smoothly.

## Step 0: Load your agentspace (always first)
1. Read `references/readonly-self-improvement.md`. It holds the rules no version of this skill may break.
2. Read `references/agentspace/index.md`. It summarizes everything in agentspace: each host adapter with its `Detect` signals, and every other file with its purpose and when to read it.
3. Read the adapter whose `Detect` matches this host. It says how to list, change, revert, and retire skills here, and which skills, connectors, or plugins are protected. Open the other files listed in the index when their "read when" applies.
4. Check the index against the folder. If a file is missing from the index, or an index entry has no file, tell the user and propose a fix to the index. Do not guess.
5. If the index has no rows and agentspace has no other files, this is a fresh install. If the index is missing or damaged, rebuild it from the files (`references/building-adapters.md` §8). If no adapter matches this host, build one with `references/building-adapters.md` before changing anything. You can still reflect and propose (Steps 1–5) without an adapter, but you cannot apply.

## What the user wants → what to do
| Request | Follow |
| :--- | :--- |
| Reflect on a session, fix or improve a skill, undo a change | **Improve** (below) |
| Review, create, merge, split, rename, retire, or restore skills | `references/managing-roster.md` |
| Change the-one-skill, an adapter, or another agentspace file | **Improve**, plus §3 of `references/readonly-self-improvement.md` |

## Improve

1. **Analyze the session.** Identify the user's goal and which skill(s) were used.
2. **Evaluate.** Review what was generated (content, structure, tone, accuracy). Look at what the user corrected: format (table vs. prose), wrong assumptions, wrong targets or properties the skill should have handled. Note friction and gaps.
3. **Choose concrete improvements.** For each one, say exactly what changes:
   - **Edit `SKILL.md`:** instructions, constraints, input/output formats.
   - **Add or edit a reference file** in `references/` (checklists, domain rules) and point to it from `SKILL.md`.
   - **Create a new skill** if the workflow is a separate job from the current skill's scope.
   - **Fix the-one-skill or its adapter** if this skill caused the friction (label these options "the-one-skill").
4. **Check for contradictions (critical).** If a change conflicts with an existing rule or boundary of the skill, do not apply it silently. Point out the conflict on that option, quote the rule it replaces, and ask the user to confirm it by name. A skill marked protected in the adapter is never changed: propose a new skill instead.
5. **Present the reflection:**
   - **Skills used**
   - **What worked / what caused friction**
   - **Improvement options** (numbered and specific)

   Ask which options to apply, in one question (see **Asking the user**). If the user already named the change, skip the menu: present the reflection briefly and go straight to its diff.
6. **Apply safely (only what the user approved).** Use the adapter's mechanism:
   - Keep the original. The first change to a skill saves it untouched, and it is never edited.
   - Prepare only what was chosen. You may draft before the yes, since a draft changes nothing installed, but draft only options the user picked or named. The first time a store or draft folder appears in the user's space, say where it is. If it is inside a project or repository, ask whether to commit it or ignore it (for example in `.gitignore`), as part of the same question.
   - Show the full diff of every file you change and get a yes before applying.
   - Change every file the skill needs, and never drop a skill's other files.
   - Verify the result, summarize what changed, and tell the user: *"Say 'revert' to go back to the original."*
7. **Revert on request.** Put the original back exactly as it was (adapter). The improved version is kept, so it can be switched back in.

## Asking the user
Ask as little as possible without skipping an approval.
- **Find out, don't ask.** Get facts from the session, the skill files, and read-only checks. Ask only when the answer would change what you do and you cannot find it yourself.
- **One round per change set.** Put everything that needs a decision into one message ending in one question: options, conflicts, adapter or index fixes, and offers to record something. Never ask a series of questions.
- **Short diffs come with their options.** When the full diffs are short, show them with the options so the user can pick and approve in one reply ("apply 1 and 3").
- **Choose sensible defaults.** For wording, file placement, or naming, pick one and point it out in the diff instead of asking.
- **Batching never replaces consent.** Every change still needs an explicit yes after its full diff or exact action is shown. A conflict is confirmed only when the user's reply confirms it by name or number. Approving the option does not confirm its conflict.

## Learn as you go
- If the host behaves differently from what its adapter says (a command fails, a tool lacks an ability or has a new one), stop. Tell the user what you saw and include an adapter fix in your next set of options.
- If something useful about this user or their setup would otherwise be lost between sessions, add an option to record it in agentspace (`references/building-adapters.md` §7), together with your other options.
- Never change `readonly-*` files. If a fix would need that, tell the user and leave the edit to them.

## Gotchas
- **Skill names:** lowercase letters, numbers, and hyphens only. Never add prefixes such as `user:` or `system:` to a name or to the frontmatter `name`.
- **Never edit an original in place.** If an operation is not possible, stop and ask. Never substitute another action (for example, disabling a skill when asked to delete it).
- **Be specific.** "Add a rule: dates in YYYY-MM-DD" beats "make the format clearer".
- **Never silently overwrite a core rule** of a skill. Confirm edge-case exceptions with the user first.
- **Changes load in a new session** on most hosts. Say so after applying.
