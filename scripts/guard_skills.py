#!/usr/bin/env python3
"""Claude Code PreToolUse hook: block direct file edits inside skills folders.

Skills change only through the-one-skill (skillctl.py runs as its own process, so it is not
affected). Install it with the JSON that `skillctl.py --root <skills_folder> guard` prints.

Usage (as a hook command): python3 guard_skills.py <skills_folder> [<skills_folder> ...]
Reads the hook event (JSON) on stdin. Exit 0 allows the call; exit 2 blocks it, and the message
on stderr goes back to the model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

GUARDED_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
MESSAGE = (
    "Blocked by the-one-skill's guard: {path} is inside a skills folder ({root}). Skills change only "
    "through the-one-skill: load it, describe the change to the user in plain language, get their yes, "
    "and apply it with skillctl.py (draft, edit the draft in the store, apply). Do not edit installed "
    "skill files directly, and do not remove or work around this guard. If the user wants direct "
    "edits, they can remove the hook from .claude/settings.local.json themselves."
)


def check(event: dict, roots: list[Path]) -> str | None:
    """Return a block message, or None to allow."""
    if event.get("tool_name") not in GUARDED_TOOLS:
        return None
    tool_input = event.get("tool_input") or {}
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path(event.get("cwd") or ".") / path
    path = path.resolve()
    for root in roots:
        if path == root or root in path.parents:
            return MESSAGE.format(path=path, root=root)
    return None


def main(argv: list[str]) -> int:
    roots = [Path(a).expanduser().resolve() for a in argv]
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # not a hook event we understand: never break the session
    msg = check(event, roots)
    if msg:
        print(msg, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
