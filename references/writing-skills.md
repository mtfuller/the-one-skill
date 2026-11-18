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
- **Only a language every host can run.** Hosts differ in which script languages a skill may use, and that can change. Use only languages the adapter lists under "Script languages" for this host. If the user uses the skill on more than one host (other adapters in agentspace), use a language they all list. Python is the most widely supported, so prefer it when there's a choice. If the adapter doesn't record the languages yet, find out first (`references/building-adapters.md` §2). Don't guess from what you know about the vendor.
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
3. In the proposal, say in a few words that it was tested on the user's own file.

If the host can't run code, or can't run any language the script could be written in, don't add scripts: keep the step in prose and say why in one line. Never run a script from a skill that is not installed yet (policy invariant 11). Read it instead.

## Before you propose
- `list` shows no problems for the skill. On strategy A, pass `--languages` with the adapter's script languages.
- `overlap --candidate <skill>` comes back clean, or each finding is explained.
- No template placeholders are left (`list` flags them).
