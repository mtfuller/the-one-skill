# Changelog

Plain-language notes for each release. the-one-skill reads these when you ask it to update itself.

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
