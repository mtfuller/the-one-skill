#!/usr/bin/env python3
"""Build release packages of a skill: a zip, or one plain-text bundle; and unpack a bundle.

Both contain only the release package (skillctl.in_release): files a host needs to run the skill,
all .md or .py, which skill hosts such as Gemini accept. Tests, evals, CI, release tooling, and a
user's agentspace notes (beyond the empty index) never go in.

A bundle lets a chat that cannot open zip files read a whole release, file by file. Each file
sits between two marker lines; nothing is escaped, so the text reads as-is.

    python3 scripts/bundle.py pack <skill_folder> [-o the-one-skill.bundle.md]
    python3 scripts/bundle.py zip <skill_folder> -o the-one-skill.zip   (files under the-one-skill/)
    python3 scripts/bundle.py unpack <bundle.md> <out_folder>
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skillctl import in_release  # noqa: E402  (one definition of what a release contains)

START = "=== FILE: {} ==="
END = "=== END FILE: {} ==="
def release_files(folder: Path) -> list[Path]:
    folder = folder.resolve()
    return sorted(p for p in folder.rglob("*")
                  if p.is_file() and ".git" not in p.relative_to(folder).parts
                  and in_release(p.relative_to(folder).as_posix()))


def _version(folder: Path) -> str:
    for name in ("VERSION.md", "VERSION"):
        if (folder / name).is_file():
            return (folder / name).read_text(encoding="utf-8").strip()
    return "unknown"


def pack(folder: Path) -> str:
    folder = folder.resolve()
    if not (folder / "SKILL.md").is_file():
        raise SystemExit(f"{folder} has no SKILL.md")
    version = _version(folder)
    files = release_files(folder)
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


def make_zip(folder: Path, out: Path, prefix: str = "the-one-skill") -> list[str]:
    folder = folder.resolve()
    if not (folder / "SKILL.md").is_file():
        raise SystemExit(f"{folder} has no SKILL.md")
    names = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in release_files(folder):
            name = f"{prefix}/{p.relative_to(folder).as_posix()}"
            z.write(p, name)
            names.append(name)
    return names


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
    p = sub.add_parser("zip")
    p.add_argument("folder")
    p.add_argument("-o", "--output", required=True)
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
    elif a.cmd == "zip":
        for name in make_zip(Path(a.folder), Path(a.output)):
            print(name)
    else:
        for rel in unpack(Path(a.bundle), Path(a.out)):
            print(rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
