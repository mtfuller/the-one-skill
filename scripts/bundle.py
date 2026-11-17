#!/usr/bin/env python3
"""Pack a skill folder into one plain-text file, or unpack it again.

A bundle lets a chat that cannot open zip files read a whole release, file by file. Each file
sits between two marker lines; nothing is escaped, so the text reads as-is.

    python3 scripts/bundle.py pack <skill_folder> [-o the-one-skill.bundle.md]
    python3 scripts/bundle.py unpack <bundle.md> <out_folder>

`pack` never includes a user's agentspace: only references/agentspace/index.md (empty in a
release) goes in, so a bundle made from an installed copy does not leak private notes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

START = "=== FILE: {} ==="
END = "=== END FILE: {} ==="
# A release is the whole folder: anything missing from a bundle would read as "removed" in an
# update. Only version-control data, caches, and private agentspace notes stay out.
SKIP_DIRS = {".git", "__pycache__"}
SKIP_SUFFIXES = (".pyc", ".pyo", ".zip")


def included(rel: Path) -> bool:
    if any(p in SKIP_DIRS for p in rel.parts) or rel.suffix in SKIP_SUFFIXES or rel.name.endswith(".bundle.md"):
        return False
    if rel.parts[:2] == ("references", "agentspace"):
        return rel.as_posix() == "references/agentspace/index.md"
    return True


def pack(folder: Path) -> str:
    folder = folder.resolve()
    if not (folder / "SKILL.md").is_file():
        raise SystemExit(f"{folder} has no SKILL.md")
    version = (folder / "VERSION").read_text(encoding="utf-8").strip() if (folder / "VERSION").is_file() else "unknown"
    files = sorted(p for p in folder.rglob("*") if p.is_file() and included(p.relative_to(folder)))
    out = [f"# {folder.name} bundle", "",
           f"Version: {version}. {len(files)} files. Each file is between `=== FILE: <path> ===` and "
           "`=== END FILE: <path> ===` lines, exactly as written.", ""]
    for p in files:
        rel = p.relative_to(folder).as_posix()
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binary files are not bundled
        out += [START.format(rel), text.rstrip("\n"), END.format(rel), ""]
    return "\n".join(out)


def unpack(bundle: Path, out: Path) -> list[str]:
    lines = bundle.read_text(encoding="utf-8").splitlines()
    written, i = [], 0
    out = out.resolve()
    while i < len(lines):
        line = lines[i]
        if line.startswith("=== FILE: ") and line.endswith(" ==="):
            rel = line[len("=== FILE: "):-len(" ===")]
            end = END.format(rel)
            j = lines.index(end, i + 1)
            target = (out / rel).resolve()
            if out not in target.parents:
                raise SystemExit(f"Refusing a path outside the output folder: {rel}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("\n".join(lines[i + 1:j]) + "\n", encoding="utf-8")
            written.append(rel)
            i = j
        i += 1
    if not written:
        raise SystemExit("No files found in the bundle.")
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack")
    p.add_argument("folder")
    p.add_argument("-o", "--output")
    p = sub.add_parser("unpack")
    p.add_argument("bundle")
    p.add_argument("out")
    a = ap.parse_args(argv)
    if a.cmd == "pack":
        text = pack(Path(a.folder))
        if a.output:
            Path(a.output).write_text(text + "\n", encoding="utf-8")
        else:
            sys.stdout.write(text + "\n")
    else:
        for rel in unpack(Path(a.bundle), Path(a.out)):
            print(rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
