#!/usr/bin/env python3
"""Safe, reversible skill changes for Claude Code (pure Python 3 standard library).

How it works
------------
* The first `draft` of a skill saves an exact copy of the installed skill as its original, in a
  store next to the skills folder (e.g. ~/.claude/the-one-skill-store/). It is never modified.
* You edit the draft (also in the store, so Claude Code never loads it), then `apply` installs it.
  The store keeps the original and the latest applied version ("tuned"); nothing else.
* `use <skill> original` puts the original back; `use <skill> tuned` swaps the change back in.
* A skill folder is only ever replaced when its contents match a copy in the store, so edits
  made by hand are never lost: `draft` starts from them and `apply` keeps them.

Commands
--------
    python3 scripts/skillctl.py --root <skills_folder> status
    python3 scripts/skillctl.py --root <skills_folder> draft <skill>
    python3 scripts/skillctl.py --root <skills_folder> diff <skill>
    python3 scripts/skillctl.py --root <skills_folder> apply <skill>
    python3 scripts/skillctl.py --root <skills_folder> use <skill> original|tuned
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

STORE_DIRNAME = "the-one-skill-store"
SKIP = {"__pycache__", ".DS_Store", "Thumbs.db", ".git"}
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")


class Refused(RuntimeError):
    """The operation was refused. Nothing was changed."""


def _ignore(_dir: str, names: list[str]) -> set[str]:
    return {n for n in names if n in SKIP or n.endswith((".pyc", ".pyo"))}


def files_of(folder: Path) -> dict[str, Path]:
    if not folder.is_dir():
        return {}
    out = {}
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder)
        if p.is_file() and not any(x in SKIP for x in rel.parts) and p.suffix not in (".pyc", ".pyo"):
            out[rel.as_posix()] = p
    return out


def folder_hash(folder: Path) -> str | None:
    """Hash of every file's path and bytes; None if the folder does not exist."""
    if not folder.is_dir():
        return None
    h = hashlib.sha256()
    for rel, p in files_of(folder).items():
        h.update(rel.encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()[:16]


def folder_diff(old: Path, new: Path, old_label: str, new_label: str) -> str:
    a_files, b_files = files_of(old), files_of(new)
    out: list[str] = []
    for rel in sorted(set(a_files) | set(b_files)):
        a = a_files[rel].read_bytes() if rel in a_files else None
        b = b_files[rel].read_bytes() if rel in b_files else None
        if a == b:
            continue
        try:
            a_lines = (a or b"").decode().splitlines(keepends=True)
            b_lines = (b or b"").decode().splitlines(keepends=True)
        except UnicodeDecodeError:
            out.append(f"Binary file {rel} differs\n")
            continue
        for line in difflib.unified_diff(
            a_lines, b_lines,
            f"{old_label}/{rel}" if a is not None else "/dev/null",
            f"{new_label}/{rel}" if b is not None else "/dev/null",
        ):
            out.append(line if line.endswith("\n") else line + "\n")
    return "".join(out)


def frontmatter_name(folder: Path) -> str | None:
    md = folder / "SKILL.md"
    if not md.is_file():
        return None
    m = re.match(r"\A---\r?\n(.*?)\r?\n---", md.read_text(encoding="utf-8"), re.DOTALL)
    if not m:
        return None
    for line in m.group(1).splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None


class SkillCtl:
    def __init__(self, root: str | Path, store: str | Path | None = None) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise Refused(f"Skills folder not found: {self.root}")
        self.store = Path(store).expanduser().resolve() if store else self.root.parent / STORE_DIRNAME
        if self.store == self.root or self.root in self.store.parents:
            raise Refused("The store must be outside the skills folder, or Claude Code would load stored copies.")

    # ----- paths & state -----
    def installed(self, name: str) -> Path:
        return self.root / name

    def sdir(self, name: str) -> Path:
        return self.store / name

    def version(self, name: str, digest: str) -> Path:
        return self.sdir(name) / "versions" / digest

    def state(self, name: str) -> dict[str, Any] | None:
        p = self.sdir(name) / "state.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

    def _save_state(self, name: str, st: dict[str, Any]) -> None:
        p = self.sdir(name) / "state.json"
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")
        tmp.replace(p)

    def _copy(self, src: Path, dst: Path) -> str:
        """Copy a skill folder and check the copy matches exactly."""
        shutil.copytree(src, dst, symlinks=True, ignore=_ignore)
        digest = folder_hash(dst)
        if digest != folder_hash(src):
            shutil.rmtree(dst, ignore_errors=True)
            raise Refused(f"Copy of {src} did not match; nothing was changed.")
        assert digest
        return digest

    def _store_version(self, name: str, src: Path) -> str:
        digest = folder_hash(src)
        assert digest
        dest = self.version(name, digest)
        if folder_hash(dest) != digest:
            shutil.rmtree(dest, ignore_errors=True)
            self._copy(src, dest)
        return digest

    def which(self, name: str, st: dict[str, Any]) -> str:
        """Which version is installed: original, tuned, missing, or edited (by hand)."""
        digest = folder_hash(self.installed(name))
        if digest is None:
            return "missing"
        if digest == st["original"]:
            return "original"
        if digest == st.get("tuned"):
            return "tuned"
        return "edited"

    def _install(self, name: str, digest: str, allowed: set[str | None]) -> None:
        """Replace the installed folder with a stored version, only if the current one is safe to replace."""
        installed = self.installed(name)
        current = folder_hash(installed)
        if current is not None and current not in allowed:
            raise Refused(
                f"`{name}` was edited outside the-one-skill. Run `draft {name}` (it starts from those edits) "
                "and `apply` to keep them. Nothing was changed."
            )
        src = self.version(name, digest)
        if folder_hash(src) != digest:
            raise Refused(f"The stored copy {src} is missing or damaged; nothing was changed.")
        work = self.sdir(name) / "work"
        shutil.rmtree(work, ignore_errors=True)
        self._copy(src, work / "incoming")
        if current is not None:
            shutil.move(str(installed), str(work / "outgoing"))  # a copy of it is in the store or the draft
        shutil.move(str(work / "incoming"), str(installed))
        shutil.rmtree(work, ignore_errors=True)

    # ----- commands -----
    def draft(self, name: str) -> Path:
        installed = self.installed(name)
        if installed.is_symlink():
            raise Refused(f"`{name}` is a link to {installed.resolve()}; edit that folder directly instead.")
        if not (installed / "SKILL.md").is_file():
            raise Refused(f"No skill `{name}` in {self.root}.")
        st = self.state(name)
        if st is None:
            self.sdir(name).mkdir(parents=True, exist_ok=True)
            st = {"name": name, "original": self._store_version(name, installed), "tuned": None}
            self._save_state(name, st)
        d = self.sdir(name) / "draft"
        shutil.rmtree(d, ignore_errors=True)
        st["draft_base"] = self._copy(installed, d)
        self._save_state(name, st)
        return d

    def diff(self, name: str) -> str:
        st = self.state(name)
        if st is None:
            raise Refused(f"`{name}` has not been changed by the-one-skill.")
        d = self.sdir(name) / "draft"
        if d.is_dir():
            return folder_diff(self.installed(name), d, "installed", "draft")
        if st.get("tuned"):
            return folder_diff(self.version(name, st["original"]), self.version(name, st["tuned"]), "original", "tuned")
        return ""

    def apply(self, name: str) -> list[str]:
        """Install the draft. Returns warnings. Call only after the user approved the diff."""
        st = self.state(name)
        d = self.sdir(name) / "draft"
        if st is None or not d.is_dir():
            raise Refused(f"No draft for `{name}`; run `draft {name}` first.")
        if not (d / "SKILL.md").is_file():
            raise Refused("The draft has no SKILL.md.")
        fm_name = frontmatter_name(d)
        if fm_name != name:
            raise Refused(f"The draft's frontmatter `name` must stay `{name}` (found {fm_name!r}).")
        digest = self._store_version(name, d)
        # Safe to replace: a stored version, the folder the draft started from, or the draft itself
        # (if an earlier `apply` was interrupted, running it again finishes the job).
        allowed = {st["original"], st.get("tuned"), st.get("draft_base"), digest}
        self._install(name, digest, allowed)
        st["tuned"] = digest if digest != st["original"] else st.get("tuned")
        st.pop("draft_base", None)
        self._save_state(name, st)
        shutil.rmtree(d, ignore_errors=True)
        self._prune(name, st)
        warnings = []
        if len((self.installed(name) / "SKILL.md").read_text(encoding="utf-8").splitlines()) > 500:
            warnings.append("SKILL.md is over 500 lines; consider moving detail into references/.")
        return warnings

    def use(self, name: str, which: str) -> None:
        st = self.state(name)
        if st is None:
            raise Refused(f"`{name}` has not been changed by the-one-skill.")
        digest = st.get(which)
        if not digest:
            raise Refused(f"`{name}` has no {which} version.")
        if self.which(name, st) == which:
            return
        self._install(name, digest, {st["original"], st.get("tuned")})

    def _prune(self, name: str, st: dict[str, Any]) -> None:
        keep = {st["original"], st.get("tuned")}
        for p in (self.sdir(name) / "versions").iterdir():
            if p.name not in keep:
                shutil.rmtree(p, ignore_errors=True)

    def status(self) -> list[tuple[str, str]]:
        rows = []
        for p in sorted(self.store.glob("*/state.json")) if self.store.is_dir() else []:
            st = json.loads(p.read_text(encoding="utf-8"))
            installed = self.which(st["name"], st)
            note = installed
            if installed == "original" and st.get("tuned"):
                note += " (tuned version saved)"
            if (p.parent / "draft").is_dir():
                note += " (draft in progress)"
            rows.append((st["name"], note))
        return rows


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Safe, reversible skill changes for Claude Code.")
    ap.add_argument("--root", required=True, help="Skills folder, e.g. ~/.claude/skills or .claude/skills")
    ap.add_argument("--store", help=f"Store folder (default: next to the skills folder, {STORE_DIRNAME}/)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    for cmd in ("draft", "diff", "apply"):
        sub.add_parser(cmd).add_argument("skill")
    p = sub.add_parser("use")
    p.add_argument("skill")
    p.add_argument("version", choices=["original", "tuned"])
    a = ap.parse_args(argv)
    try:
        ctl = SkillCtl(a.root, a.store)
        if a.cmd == "status":
            rows = ctl.status()
            print("\n".join(f"{n:32} {s}" for n, s in rows) if rows else "No skills changed by the-one-skill yet.")
        elif a.cmd == "draft":
            print(f"Draft ready: {ctl.draft(a.skill)}\nEdit it there, show `diff`, and `apply` after approval.")
        elif a.cmd == "diff":
            print(ctl.diff(a.skill) or "(no differences)", end="")
        elif a.cmd == "apply":
            for w in ctl.apply(a.skill):
                print(f"WARNING: {w}")
            print(f"Applied. `use {a.skill} original` puts the original back.")
        elif a.cmd == "use":
            ctl.use(a.skill, a.version)
            print(f"`{a.skill}`: {a.version} version installed.")
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
