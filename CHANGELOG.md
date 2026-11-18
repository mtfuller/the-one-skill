# Changelog

Plain-language notes for each release. the-one-skill reads these when you ask it to update itself.

## 1.1.0
- Keeps skills orthogonal in what they do, not only in what triggers them. A new check compares every pair of skills for competing triggers and for repeated procedure, and finds instruction blocks copied across skills. It runs on every roster review, and before a skill is created, installed, or widened.
- A policy repeated across several skills gets one owner: the skills merge if they were one job, or the policy moves into one skill the others defer to. Rules are added to the skill that owns the policy, not copied.
- Keeps a roster map in your notes: which skill owns each job and shared policy, and which overlaps you chose to keep.
- Creating a skill now starts from verified work. It checks skills already on your host and the ones Anthropic, OpenAI, or Google publish, then installs, adapts, or borrows from the closest before writing anything from scratch.
- Compares against your personal, plugin, and built-in skill folders too (read-only), and reports the same skill name in two places.
- Flags scripts copied across skills as the same procedure.
- Moves deterministic steps (counting, parsing, formatting, validating) into small scripts, and tests them on your real input before proposing. A new guide covers how to write a skill's description, sections, and scripts. New skills start from a template with inputs, steps, output, edge cases, and where scripts and references fit.
- The roster review also checks how each skill's files fit together: missing files, files nothing mentions, scripts with no run line, leftover template text, overlong descriptions, and machine-specific paths.
- Remembers the publisher skills it has already read, and what it decided, so later sessions don't search from scratch.
- Skills installed or adapted from a publisher can take the publisher's newer release while keeping your tweaks.
- Tracks when each skill was last used (on Claude Code from your session history, after asking once) and lists skills idle for 60 days so you can decide.

## 1.0.2
- Finds and installs skills only from Anthropic, OpenAI, or Google. The editable list of trusted sources (`sources.md`) is gone, and the read-only policy now fixes the list.
- Works on hosts that only show skills to code as a temporary copy, such as ChatGPT. It no longer treats a folder it can write to as saved until a new session shows the change lasted. Until then it hands changes off to you.
- Hand-off now gives you two downloads per change: a backup of the skill as it was, and the new version to upload.
- Where the model has no tools to change skills but the host has its own skill-authoring workflow (such as a built-in skill-creator), it can use that workflow to save exactly what it drafted. It checks the workflow on a throwaway skill first.

## 1.0.1
- Release downloads contain only the files the skill needs, all `.md` or `.py`, so Gemini accepts the upload. Before, the extensionless `VERSION` file was rejected.
- The version now lives in `VERSION.md`, and the license in `LICENSE.md`.
- Updating from a release leaves files that aren't part of a release alone, such as tests or your own notes.

## 1.0.0
First release.
- Reflects on a session and fixes the skills that fell short. It describes each change in a sentence or two, asks one yes, and keeps every original.
- Manages your roster: review, create, find and install from trusted sources, merge, split, rename, retire, and restore.
- Undoes as narrowly as you ask: one rule, one skill, a multi-skill change, or everything back to vanilla.
- Adapts to any host by writing its own setup notes ("agentspace") the first time it runs.
- Keeps originals and drafts in `.tos-store/` in your project, outside `.claude/`, so Claude Code asks for fewer permissions.
- On Claude Code, a guard blocks direct edits to your skills folder.
- Improves itself, within a read-only policy that only you can change.
- Updates itself from a release you download, keeping your setup notes and your local improvements.
