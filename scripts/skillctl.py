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
* Files named `readonly-*` are never changed by `apply`; only the user edits them by hand.
* A skill folder that is a git checkout keeps its `.git` across every swap.
* `retire` moves a skill into the store (Claude Code stops loading it); `restore` brings it back.

Commands
--------
    python3 scripts/skillctl.py --root <skills_folder> list [--json]
    python3 scripts/skillctl.py --root <skills_folder> status
    python3 scripts/skillctl.py --root <skills_folder> draft <skill>
    python3 scripts/skillctl.py --root <skills_folder> diff <skill>
    python3 scripts/skillctl.py --root <skills_folder> apply <skill>
    python3 scripts/skillctl.py --root <skills_folder> use <skill> original|tuned
    python3 scripts/skillctl.py --root <skills_folder> retire <skill>
    python3 scripts/skillctl.py --root <skills_folder> restore <skill>
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
READONLY_PREFIX = "readonly-"
MAX_SKILL_LINES = 500


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


def frontmatter(folder: Path) -> dict[str, str] | None:
    """Top-level `key: value` pairs of SKILL.md's frontmatter (folded `>`/`|` values joined)."""
    md = folder / "SKILL.md"
    if not md.is_file():
        return None
    m = re.match(r"\A---\r?\n(.*?)\r?\n---", md.read_text(encoding="utf-8"), re.DOTALL)
    if not m:
        return None
    out: dict[str, str] = {}
    key = None
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if km:
            key, val = km.group(1), km.group(2).strip()
            out[key] = "" if val in (">", "|", ">-", "|-") else val.strip("'\"")
        elif key and line.startswith((" ", "\t")):
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


def frontmatter_name(folder: Path) -> str | None:
    fm = frontmatter(folder)
    return fm.get("name") if fm else None


def readonly_changes(old: Path, new: Path) -> list[str]:
    """Paths of `readonly-*` files that differ, appear, or disappear between two folders."""
    a, b = files_of(old), files_of(new)
    out = []
    for rel in sorted(set(a) | set(b)):
        if not Path(rel).name.startswith(READONLY_PREFIX):
            continue
        if rel not in a or rel not in b or a[rel].read_bytes() != b[rel].read_bytes():
            out.append(rel)
    return out


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
        hold = self.sdir(name) / "git-hold"  # a git checkout's .git waits here during the swap
        if (installed / ".git").exists() and not hold.exists():
            shutil.move(str(installed / ".git"), str(hold))
        try:
            shutil.rmtree(work, ignore_errors=True)
            self._copy(src, work / "incoming")
            if installed.exists():
                shutil.move(str(installed), str(work / "outgoing"))  # a copy of it is in the store or the draft
            shutil.move(str(work / "incoming"), str(installed))
            shutil.rmtree(work, ignore_errors=True)
        finally:
            if hold.exists() and installed.is_dir() and not (installed / ".git").exists():
                shutil.move(str(hold), str(installed / ".git"))

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
        if self.installed(name).is_dir():
            locked = readonly_changes(self.installed(name), d)
            if locked:
                raise Refused(
                    f"The draft changes read-only file(s): {', '.join(locked)}. Only the user edits "
                    "`readonly-*` files, by hand. Undo those changes in the draft; nothing was changed."
                )
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
        if len((self.installed(name) / "SKILL.md").read_text(encoding="utf-8").splitlines()) > MAX_SKILL_LINES:
            warnings.append(f"SKILL.md is over {MAX_SKILL_LINES} lines; consider moving detail into references/.")
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

    def retire(self, name: str) -> Path:
        """Move a skill out of the skills folder into the store, intact. `restore` undoes it."""
        installed = self.installed(name)
        if installed.is_symlink():
            raise Refused(f"`{name}` is a link to {installed.resolve()}; remove the link by hand instead.")
        if not (installed / "SKILL.md").is_file():
            raise Refused(f"No skill `{name}` in {self.root}.")
        dest = self.sdir(name) / "retired"
        if dest.exists():
            raise Refused(f"A retired copy of `{name}` already exists at {dest}; `restore` it first or move it away.")
        digest = folder_hash(installed)
        self.sdir(name).mkdir(parents=True, exist_ok=True)
        shutil.move(str(installed), str(dest))  # moves everything, .git included
        if folder_hash(dest) != digest:
            raise Refused(f"The retired copy at {dest} does not match; check it before doing anything else.")
        return dest

    def restore(self, name: str) -> None:
        src = self.sdir(name) / "retired"
        if not src.is_dir():
            raise Refused(f"`{name}` is not retired.")
        if self.installed(name).exists():
            raise Refused(f"`{name}` already exists in {self.root}; nothing was changed.")
        digest = folder_hash(src)
        shutil.move(str(src), str(self.installed(name)))
        if folder_hash(self.installed(name)) != digest:
            raise Refused(f"The restored `{name}` does not match its retired copy; check it.")

    def status(self) -> list[tuple[str, str]]:
        rows = []
        dirs = sorted(p for p in self.store.iterdir() if p.is_dir()) if self.store.is_dir() else []
        for sd in dirs:
            st = self.state(sd.name)
            retired = (sd / "retired").is_dir()
            if st is None and not retired:
                continue
            notes = []
            if st is not None:
                installed = self.which(sd.name, st)
                notes.append(installed)
                if installed == "original" and st.get("tuned"):
                    notes.append("(tuned version saved)")
                if (sd / "draft").is_dir():
                    notes.append("(draft in progress)")
            if retired:
                notes.append("retired" if st is None else "(retired copy saved)")
            rows.append((sd.name, " ".join(notes)))
        return rows

    def roster(self) -> list[dict[str, Any]]:
        """Every skill in the skills folder with its state and any problems found."""
        rows = []
        for p in sorted(self.root.iterdir()):
            if not p.is_dir() or p.name.startswith("."):
                continue
            issues: list[str] = []
            fm = frontmatter(p)
            if not (p / "SKILL.md").is_file():
                issues.append("no SKILL.md")
            elif fm is None:
                issues.append("no frontmatter")
            fm = fm or {}
            fm_name, desc = fm.get("name", ""), fm.get("description", "")
            if fm and not fm_name:
                issues.append("no name")
            elif fm_name and fm_name != p.name:
                issues.append(f"name `{fm_name}` differs from folder")
            if not NAME_RE.match(p.name):
                issues.append("invalid folder name (use a-z, 0-9, -)")
            if fm and not desc:
                issues.append("no description")
            elif desc and not re.search(r"\buse (it )?(when|for)\b", desc, re.IGNORECASE):
                issues.append("description says nothing about when to use it")
            if (p / "SKILL.md").is_file():
                n = len((p / "SKILL.md").read_text(encoding="utf-8").splitlines())
                if n > MAX_SKILL_LINES:
                    issues.append(f"SKILL.md has {n} lines (> {MAX_SKILL_LINES})")
            st = self.state(p.name)
            rows.append({
                "name": p.name,
                "state": "linked" if p.is_symlink() else (self.which(p.name, st) if st else "unmanaged"),
                "description": desc,
                "issues": issues,
            })
        return rows


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Safe, reversible skill changes for Claude Code.")
    ap.add_argument("--root", required=True, help="Skills folder, e.g. ~/.claude/skills or .claude/skills")
    ap.add_argument("--store", help=f"Store folder (default: next to the skills folder, {STORE_DIRNAME}/)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("list").add_argument("--json", action="store_true", help="Machine-readable output")
    for cmd in ("draft", "diff", "apply", "retire", "restore"):
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
        elif a.cmd == "list":
            rows = ctl.roster()
            if a.json:
                print(json.dumps(rows, indent=2))
            elif not rows:
                print("No skills found.")
            for r in rows if not a.json else []:
                desc = r["description"] if len(r["description"]) <= 70 else r["description"][:67] + "..."
                print(f"{r['name']:32} {r['state']:10} {desc}")
                for issue in r["issues"]:
                    print(f"{'':32} ! {issue}")
        elif a.cmd == "retire":
            print(f"Retired `{a.skill}` to {ctl.retire(a.skill)}. `restore {a.skill}` brings it back.")
        elif a.cmd == "restore":
            ctl.restore(a.skill)
            print(f"`{a.skill}` restored.")
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
