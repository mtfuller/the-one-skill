# Improving Skills

Use this to reflect on a session and to fix or improve a skill, including the-one-skill itself. For the-one-skill or its setup files, also follow §3 of `references/readonly-self-improvement.md`.

1. **Analyze the session.** Identify the user's goal and which skill(s) were used.
2. **Evaluate.** Review what was generated (content, structure, tone, accuracy). Look at what the user corrected: format (table vs. prose), wrong assumptions, wrong targets or properties the skill should have handled. Note friction and gaps. Focus on the skills that did the work. Mention the-one-skill only if it caused the friction, in one line.
3. **Choose concrete improvements**, specific enough to act on ("dates as YYYY-MM-DD", not "clearer format"). How to make each one is up to you:
   - Edit the skill's instructions, or add a reference file it points to.
   - Create a new skill if the workflow is a separate job.
   - Install a skill from a trusted source if the job is generic enough that one probably exists (`references/managing-roster.md`).
   - Fix the-one-skill or its adapter if this skill caused the friction.
4. **Check for contradictions (critical).** Note every rule or boundary of the skill that a change would override, so you can name it in your message. A skill marked protected in the adapter is never changed: offer a new skill instead.
5. **Tell the user, briefly:** what went wrong, and what you'd change to fix it, in plain language, one line per change. If the user already said what they want, skip the analysis and just confirm the change. End with one question: apply all, some, or none.
6. **Apply what the user approved,** using the adapter's mechanism, never by editing installed skill files directly:
   - Keep the original. The first change to a skill saves it untouched, and it is never edited.
   - Prepare only what was approved, and change every file the skill needs. Never drop a skill's other files.
   - Verify the result, then report it in one line with how to undo it.

## Learn as you go
- If the host behaves differently from what its adapter says (a command fails, a tool lacks an ability or has a new one), stop. Say in plain words what didn't work and offer to fix your setup.
- If something about this user or their setup would otherwise be lost between sessions, offer to remember it (`references/building-adapters.md` §7) in the same message as your other proposals.
- Never change `readonly-*` files. If a fix would need that, tell the user and leave the edit to them.
