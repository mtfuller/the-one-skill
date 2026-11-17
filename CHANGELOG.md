# Changelog

Plain-language notes for each release. the-one-skill reads these when you ask it to update itself.

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
