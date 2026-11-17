---
name: the-one-skill
description: Reflect on a session and improve the skills used, manage the skill roster (review, create, find and install from trusted sources, merge, retire, restore, step back, return to vanilla), and improve the-one-skill itself, always reversibly and only with the user's approval. Use when the user asks to reflect on a session, evaluate a response, fix or improve a skill, create a skill for a repeated workflow, find or install a skill from a trusted source, review, combine or clean up their skills, retire or bring back a skill, undo a skill change (one rule, one skill, or everything back to vanilla), or improve the-one-skill. Do not use for the domain task itself when a skill handled it without friction.
---

# the-one-skill

Look back at a session, find where skills fell short, propose concrete fixes, and apply the ones the user approves **without ever losing the original skill**. Every change can be undone. The same discipline covers managing the whole roster and improving this skill.

## When to Use
- The user asks to reflect on a recent session or evaluate a response.
- The user had to correct the output, repeat themselves, or work around a skill.
- The user asks to improve, fix, or evolve a skill, including this one.
- A workflow keeps repeating and no skill covers it, or the user wants an existing skill from a trusted source.
- The user wants to review, tidy, merge, retire, or restore skills.
- The user asks to undo a skill change ("put it back", "revert that", "remove the rule you added", "back to vanilla").

## Do not use when
- Doing the task a skill is for, when it went smoothly.

## Step 0: Load your agentspace (always first)
1. Read `references/readonly-self-improvement.md`. It holds the rules no version of this skill may break.
2. Read `references/agentspace/index.md`. It summarizes everything in agentspace: each host adapter with its `Detect` signals, and every other file with its purpose and when to read it.
3. Read the adapter whose `Detect` matches this host. It says how to list, change, revert, and retire skills here, and which skills, connectors, or plugins are protected. Open the other files listed in the index when their "read when" applies.
4. Check the index against the folder. If a file is missing from the index, or an index entry has no file, fix the index as part of your next change and mention it in a few words. Never act on a file the index does not describe.
5. If the index has no rows and agentspace has no other files, this is a fresh install. If the index is missing or damaged, rebuild it from the files (`references/building-adapters.md` §8). If no adapter matches this host, build one with `references/building-adapters.md` before changing anything. To the user, this is a one-time setup, mentioned in a few words in the same message as their change. Saving the adapter is its own step: apply and verify it alone, before anything that depends on it. If it fails, stop there. You can still reflect and propose (Improve steps 1–5) without an adapter, but you cannot apply.

## What the user wants → what to do
| Request | Follow |
| :--- | :--- |
| Reflect on a session, fix or improve a skill, undo a change | **Improve** (below) |
| Review, create, find and install, merge, split, rename, retire, or restore skills, or go back to vanilla | `references/managing-roster.md` |
| Change the-one-skill, an adapter, or another agentspace file | **Improve**, plus §3 of `references/readonly-self-improvement.md` |

## Talk in outcomes, not mechanics
The user should not have to manage skills. Handle the mechanics yourself and talk only about what will behave differently.
- **Describe changes in plain language.** "From now on, CSV summaries come back as a table" — not file names, diffs, frontmatter, adapters, stores, versions, or tool commands. Use one or two sentences per change.
- **Show diffs and file detail only when asked.** If the user asks ("show me the diff", "what exactly changes?"), show the full diff right away. It must always be available.
- **One yes per request.** Gather everything the change needs into one short message that ends in one yes/no question: what will change, any rule it overrides, and anything that goes with it (a one-time setup on a fresh install, an ignore entry for the store, the number of permission prompts to expect). Never ask a series of questions.
- **Overrides go in the same sentence.** If a change overrides a rule the skill already has, say so plainly in that sentence ("…which replaces its rule to write prose"). The yes then covers it. Never override a rule without saying so.
- **Find out, don't ask.** Get facts from the session, the skills, and read-only checks. Choose sensible defaults for naming, wording, and placement without mentioning them.
- **Report after, in one line.** "Done: CSV summaries now come back as a table. Say 'undo' to reverse it. It applies from your next session."

## Improve

1. **Analyze the session.** Identify the user's goal and which skill(s) were used.
2. **Evaluate.** Review what was generated (content, structure, tone, accuracy). Look at what the user corrected: format (table vs. prose), wrong assumptions, wrong targets or properties the skill should have handled. Note friction and gaps.
3. **Choose concrete improvements**, specific enough to act on ("dates as YYYY-MM-DD", not "clearer format"). How to make each one is up to you:
   - Edit the skill's instructions, or add a reference file it points to.
   - Create a new skill if the workflow is a separate job.
   - Install a skill from a trusted source if the job is generic enough that one probably exists (`references/managing-roster.md`).
   - Fix the-one-skill or its adapter if this skill caused the friction.
4. **Check for contradictions (critical).** Note every rule or boundary of the skill that a change would override, so you can name it in your message. A skill marked protected in the adapter is never changed: offer a new skill instead.
5. **Tell the user, briefly:** what went wrong, and what you'd change to fix it, in plain language, one line per change. If the user already said what they want, skip the analysis and just confirm the change. End with one question: apply all, some, or none.
6. **Apply what the user approved,** using the adapter's mechanism:
   - Keep the original. The first change to a skill saves it untouched, and it is never edited.
   - Prepare only what was approved, and change every file the skill needs. Never drop a skill's other files.
   - Verify the result, then report it in one line with how to undo it.
7. **Undo on request, as narrowly as the user asked.**
   - **One rule or one change:** step that skill back to its previous version, or apply a new change that removes just that part. Never revert the whole skill for this: that would also undo every later change, including the-one-skill's own setup.
   - **One skill:** put its original back exactly as it was. The improved versions are kept, so they can come back.
   - **Several skills or everything:** follow `references/managing-roster.md` (change sets, back to vanilla).
   - **Promise only what is kept.** Check which versions actually exist (on strategy A, `history <skill>`) before telling the user they can get one back.

## Learn as you go
- If the host behaves differently from what its adapter says (a command fails, a tool lacks an ability or has a new one), stop. Say in plain words what didn't work and offer to fix your setup.
- If something about this user or their setup would otherwise be lost between sessions, offer to remember it (`references/building-adapters.md` §7) in the same message as your other proposals.
- Never change `readonly-*` files. If a fix would need that, tell the user and leave the edit to them.

## Gotchas
- **Skill names:** lowercase letters, numbers, and hyphens only. Never add prefixes such as `user:` or `system:` to a name or to the frontmatter `name`.
- **Never edit an original in place.** If an operation is not possible, stop and ask. Never substitute another action (for example, disabling a skill when asked to delete it).
- **Never silently overwrite a core rule** of a skill. Name it in your message, so the user's yes covers it knowingly.
- **Changes load in a new session** on most hosts. Say so after applying.
