---
name: the-one-skill
description: Reflect on a chat or task session, evaluate how well the skills used served the user, and safely improve, create, or revert skills. Use when the user asks to reflect on a session, evaluate a response, improve or fix a skill, create a skill for a repeated workflow, or undo a skill change. Do not use for the domain task itself when a skill handled it without friction.
---

# the-one-skill

Look back at a session, find where skills fell short, propose concrete fixes, and apply the ones the user approves **without ever losing the original skill**. Every change can be undone.

## When to Use
- The user asks to reflect on a recent session or evaluate a response.
- The user had to correct the output, repeat themselves, or work around a skill.
- The user asks to improve, fix, or evolve a skill (including this one).
- A workflow keeps repeating and no skill covers it.
- The user asks to undo a skill change ("put it back", "revert that").

## Do not use when
- Doing the task a skill is for, when it went smoothly.

## Host
Read **one** host guide before changing anything: `vendors/claude-code.md` or `vendors/gemini.md`.

## Steps

1. **Analyze the session.** Identify the user's goal and which skill(s) were used.
2. **Evaluate.** Review what was generated (content, structure, tone, accuracy). Look at what the user corrected: format (table vs. prose), wrong assumptions, wrong targets or properties the skill should have handled. Note friction and gaps.
3. **Choose concrete improvements.** For each, say exactly what changes:
   - **Edit `SKILL.md`:** instructions, constraints, input/output formats.
   - **Add or edit a reference file** in `references/` (checklists, domain rules) and point to it from `SKILL.md`.
   - **Create a new skill** if the workflow is a separate job from the current skill's scope.
4. **Check for contradictions (critical).** If a change conflicts with an existing rule or boundary of the skill, do not apply it silently. Point out the conflict and ask the user to confirm.
5. **Present the reflection:**
   - **Skills used**
   - **What worked / what caused friction**
   - **Improvement options** (numbered, specific)
   Ask which options to apply.
6. **Apply safely (only what the user approved).** Follow the host guide:
   - Keep the original. The first change to a skill saves it untouched; it is never edited.
   - Show the full diff of every file you change and get a yes before applying.
   - Change every file the skill needs; never drop a skill's other files.
   - Verify the result, summarize what changed, and tell the user: *"Say 'revert' to go back to the original."*
7. **Revert on request.** Put the original back exactly as it was (host guide). The improved version is kept, so it can be switched back in.

## Gotchas
- **Skill names:** lowercase letters, numbers, and hyphens only. Never add prefixes such as `user:` or `system:` to a name or to the frontmatter `name`.
- **Never edit an original in place.** If an operation is not possible, stop and ask; never substitute another action (for example, disabling a skill when asked to delete it).
- **Be specific.** "Add a rule: dates in YYYY-MM-DD" beats "make the format clearer".
- **Never silently overwrite a core rule** of a skill; confirm edge-case exceptions with the user first.
