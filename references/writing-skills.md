# Writing a Skill

How to write the files of a skill you create or improve, so it works the first time and gives the same result every time. `references/managing-roster.md` covers where a new skill starts from (install, adapt, borrow, or scratch). This file covers what goes into the skill itself. `skillctl new` starts from a template with these sections.

## Shape
- **`SKILL.md` is the map, not the manual.** Keep it short: aim for under 150 lines, and never over 500. Put long material in `references/` and tell the model when to open each file ("Read `references/<topic>.md` before choosing a chart").
- **One level deep.** `SKILL.md` points to each reference and script directly. References don't send the model on to further references.
- **Every file is reachable.** A file `SKILL.md` never mentions is never read or run. `list` flags files nothing points to, and pointers to files that don't exist.
- **No machine-specific paths.** Paths are relative to the skill's folder. `list` flags absolute paths into one machine.

## Description
The description is the only part the host reads before deciding to load the skill.
- Say what it does, then "Use when …" with the words a user would actually say ("a CSV", "a pitch deck"), then "Do not use when … (use `<neighbour>`)" for each skill it could be confused with.
- Keep it under 1,024 characters (Claude's limit; `list` flags longer ones), and write it in the third person ("Builds…", not "I build…").

## Body sections
| Section | What goes in it |
| :--- | :--- |
| Opening lines | The job, and what a good result looks like |
| Inputs | What the skill needs and where it comes from |
| Steps | Numbered. Judgement in words; deterministic work as script calls |
| Output | The exact shape of the result, with a short example |
| Edge cases | Each case that went wrong before, and what to do instead |
| More detail | Each reference and when to read it |

Fill these from the session that prompted the change. The user's corrections are the requirements: each one becomes a rule, an edge case, or a script.

## Instructions or a script?
Prose gets followed slightly differently each run. Code runs the same way every time. **Put a step in a script when any of these is true:**
- The step should give the same result every time: parsing, validating, converting, counting, computing, sorting, formatting to an exact layout.
- A small slip breaks the result: an exact schema, file format, date format, or naming rule.
- The model wrote similar code for this skill in two or more sessions.
- The user corrected the same mechanical detail more than once.

**Keep in the instructions** what needs judgement: what to look at, what matters, how to word the result, and when to stop or ask. A good skill usually mixes both: the instructions decide, and the scripts carry out the mechanical parts.

When you propose a change, say in one plain line if part of it becomes a script, and why ("Counting rows is now done by a small script, so the header is never counted again").

### How to write a script
- **Standard library first.** If the script needs a package, say so in `SKILL.md` and check the host can install it. If it can't, keep the step in prose.
- **Inputs as arguments, results on stdout.** Print exactly what the next step needs: plain text in a fixed layout, or JSON. Print errors to stderr and exit non-zero, with a message that says what to fix.
- **Never change the input files.** Write output to a new file or to stdout.
- **No network access** unless the job needs it. If it does, say so in `SKILL.md`, as for any skill's network access.
- **One job per script**, named for that job (`count_rows.py`, not `utils.py`).
- **Say how to run it.** The step in `SKILL.md` gives the exact command in backticks, with the path relative to the skill (`python3 scripts/<job>.py <file>`), and says what it prints. `list` flags scripts with no such line.
- **One owner.** If another skill already has the same script, defer to that skill or merge the two. Don't copy the script (`overlap` flags copies).

### Test it before you propose it
1. Run the script on the real input from the session (a copy of it, never the original), and on the case the user corrected.
2. Compare the output with what the user wanted. If it doesn't match, fix it before proposing. Never propose an untested script.
3. Save what it fixed as a case (below), so later changes can't quietly break it.
4. In the proposal, say in a few words that it was tested on the user's own file.

If the host can't run code, don't add scripts: keep the step in prose and say why in one line. Never run a script from a skill that is not installed yet (policy invariant 11). Read it instead.

## Cases: keep each fix fixed
A case records one thing a change fixed: what the user asked, the input files, and what a good result does. Cases live in the store, outside the skill, so they never load as part of it. On strategy A:
- **Save one with every fix:** `case add <skill> <case> --prompt "<what the user asked>" --expect "<what a good result does>" [--file <input>]…`. Use a short name that describes the fix, such as `header-not-counted`. Saving a case is part of the change the user already approved. Don't ask about it separately.
- **For a script, record its output:** add `--run "python3 {skill}/scripts/<script>.py <args>" --record`. `{skill}` and `{inputs}` are throwaway copies of the skill and the input files, and the command runs inside the inputs folder. The output is recorded from the draft, so record it only after the draft gives the right result.
- **Before proposing any later change to the skill:** `case run <skill>` checks the draft. A recorded case passes or fails on its own. For each "check by hand" case, do the request in your head against the draft and confirm every expectation still holds. A failing case means the change breaks an earlier fix: fix the draft, or name the conflict in your proposal ("this undoes the earlier rule that the header isn't counted").
- **Cases follow the user, not the code.** If the user changes their mind about something a case protects, remove that case with `case remove` in the same change, and say so in your proposal.

On other strategies there is no store. Note each case's prompt and expectations in the roster map, under the skill's row, and check them by hand.

## Before you propose
- `list` shows no problems for the skill.
- `overlap --candidate <skill>` comes back clean, or each finding is explained.
- `case run <skill>` passes, and every "check by hand" case still holds.
- No template placeholders are left (`list` flags them).
