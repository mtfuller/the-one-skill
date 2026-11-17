#!/usr/bin/env python3
"""Safe, reversible skill changes for Claude Code (pure Python 3 standard library).

How it works
------------
* The first `draft` of a skill saves an exact copy of the installed skill as its original, in a
  store next to the skills folder (e.g. ~/.claude/the-one-skill-store/). It is never modified.
* You edit the draft (also in the store, so Claude Code never loads it), then `apply` installs it.
  The store keeps the original and the last few applied versions (the newest is "tuned").
* `use <skill> original` puts the original back, `use <skill> previous` steps back one applied
  version, `use <skill> tuned` swaps the newest change back in, and `history <skill>` lists them.
* `new <skill>` starts a skill the-one-skill creates. Its "original" is "not installed", so
  `status` lists it and going back to vanilla means retiring it.
* A skill folder is only ever replaced when its contents match a copy in the store, so edits
  made by hand are never lost: `draft` starts from them and `apply` keeps them.
* Files named `readonly-*` are never changed by `apply`; only the user edits them by hand.
* A skill folder that is a git checkout keeps its `.git` across every swap.
* `retire` moves a skill into the store (Claude Code stops loading it); `restore` brings it back.
* `--set <name>` on apply/use/retire/restore records the step in a change set (in the store, so it
  needs no extra approval). `sets` lists them; `undo-set <name>` shows the reverse steps and
  `undo-set <name> --apply` runs them, newest first, after checking nothing changed since.

Commands
--------
    python3 scripts/skillctl.py --root <skills_folder> list [--json]
    python3 scripts/skillctl.py --root <skills_folder> status
    python3 scripts/skillctl.py --root <skills_folder> draft <skill>
    python3 scripts/skillctl.py --root <skills_folder> diff <skill>
    python3 scripts/skillctl.py --root <skills_folder> apply <skill>
    python3 scripts/skillctl.py --root <skills_folder> use <skill> original|previous|tuned|<version>
    python3 scripts/skillctl.py --root <skills_folder> history <skill>
    python3 scripts/skillctl.py --root <skills_folder> new <skill> [--from <folder>]
    python3 scripts/skillctl.py --root <skills_folder> sets
    python3 scripts/skillctl.py --root <skills_folder> guard     (prints the Claude Code hook setting)
    python3 scripts/skillctl.py --root <skills_folder> undo-set <name> [--apply]
    (apply, use, retire, restore also take: --set <name> [--note "<why>"])
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
SETS_FILE = "changesets.json"
KEEP_APPLIED = 5  # applied versions kept per skill, besides the original
NEW_SKILL_TEMPLATE = """---
name: {name}
description: <what it does>. Use when <situation>. Do not use when <situation>.
---

# {name}

## Steps
1. ...
"""


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
        self.change_set: tuple[str, str | None] | None = None  # (name, note) while recording
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
        if not p.is_file():
            return None
        st = json.loads(p.read_text(encoding="utf-8"))
        if "history" not in st:  # state written before version history existed
            st["history"] = [{"digest": st["tuned"], "applied": None}] if st.get("tuned") else []
        return st

    @staticmethod
    def _digests(st: dict[str, Any]) -> list[str]:
        return [h["digest"] for h in st.get("history", [])]

    def _known(self, st: dict[str, Any]) -> set[str | None]:
        return {st.get("original"), *self._digests(st)}

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
        """Which version is installed: original, tuned, earlier (an older applied version), missing, or edited."""
        digest = folder_hash(self.installed(name))
        if digest is None:
            return "missing"
        if digest == st["original"]:
            return "original"
        if digest == st.get("tuned"):
            return "tuned"
        if digest in self._digests(st):
            return "earlier"
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

    def new(self, name: str, source: str | Path | None = None) -> Path:
        """Start a new skill created by the-one-skill: a draft in the store, installed by `apply`."""
        if not NAME_RE.match(name):
            raise Refused(f"`{name}` is not a valid skill name (lowercase letters, numbers, hyphens).")
        if self.installed(name).exists() or self.installed(name).is_symlink():
            raise Refused(f"`{name}` already exists in {self.root}; choose another name or `draft` it.")
        if self.sdir(name).exists():
            raise Refused(f"The store already has `{name}` ({self.sdir(name)}); `restore` it or choose another name.")
        self.sdir(name).mkdir(parents=True)
        d = self.sdir(name) / "draft"
        try:
            if source is not None:
                src = Path(source).expanduser().resolve()
                if not (src / "SKILL.md").is_file():
                    raise Refused(f"{src} has no SKILL.md.")
                self._copy(src, d)
            else:
                d.mkdir()
                (d / "SKILL.md").write_text(NEW_SKILL_TEMPLATE.format(name=name), encoding="utf-8")
        except Exception:
            shutil.rmtree(self.sdir(name), ignore_errors=True)
            raise
        self._save_state(name, {"name": name, "original": None, "created": True, "tuned": None, "history": []})
        return d

    def history(self, name: str) -> list[dict[str, Any]]:
        """Versions that `use` can install, oldest first, with which one is installed."""
        st = self.state(name)
        if st is None:
            raise Refused(f"`{name}` has not been changed by the-one-skill.")
        current = folder_hash(self.installed(name))
        rows = [{"label": "original", "version": st["original"] or "(not installed: created by the-one-skill)",
                 "applied": None, "installed": current is not None and current == st["original"]}]
        digests = self._digests(st)
        for i, h in enumerate(st["history"]):
            label = "tuned" if i == len(digests) - 1 else ("previous" if i == len(digests) - 2 else "earlier")
            if h["digest"] == st["original"]:
                label += " (= original)"
            rows.append({"label": label, "version": h["digest"], "applied": h["applied"],
                         "installed": current == h["digest"]})
        return rows

    def diff(self, name: str) -> str:
        st = self.state(name)
        if st is None:
            raise Refused(f"`{name}` has not been changed by the-one-skill.")
        d = self.sdir(name) / "draft"
        if d.is_dir():
            return folder_diff(self.installed(name), d, "installed", "draft")
        if st.get("tuned"):
            old = self.version(name, st["original"]) if st["original"] else self.sdir(name) / "(none)"
            return folder_diff(old, self.version(name, st["tuned"]), "original", "tuned")
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
        allowed = self._known(st) | {st.get("draft_base"), digest}
        before = folder_hash(self.installed(name))
        self._install(name, digest, allowed)
        self._record("apply", name, before, digest)
        # Every apply is recorded, even one that matches the original, so `previous` always means
        # "the version before the last apply".
        hist = [h for h in st["history"] if h["digest"] != digest]
        hist.append({"digest": digest, "applied": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
        st["history"] = hist[-KEEP_APPLIED:]
        st["tuned"] = digest
        st.pop("draft_base", None)
        self._save_state(name, st)
        shutil.rmtree(d, ignore_errors=True)
        self._prune(name, st)
        warnings = []
        if len((self.installed(name) / "SKILL.md").read_text(encoding="utf-8").splitlines()) > MAX_SKILL_LINES:
            warnings.append(f"SKILL.md is over {MAX_SKILL_LINES} lines; consider moving detail into references/.")
        return warnings

    def use(self, name: str, which: str) -> str:
        """Install a kept version: original, previous, tuned, or a version id (or its first 6+ characters)."""
        st = self.state(name)
        if st is None:
            raise Refused(f"`{name}` has not been changed by the-one-skill.")
        digests = self._digests(st)
        if which == "original":
            if st["original"] is None:
                raise Refused(f"`{name}` was created by the-one-skill, so it has no original. `retire {name}` removes it.")
            digest = st["original"]
        elif which == "tuned":
            digest = st.get("tuned")
        elif which == "previous":
            digest = digests[-2] if len(digests) >= 2 else None
        else:
            matches = [d for d in digests if len(which) >= 6 and d.startswith(which)]
            digest = matches[0] if len(matches) == 1 else None
        if not digest:
            raise Refused(f"`{name}` has no `{which}` version. `history {name}` lists the kept versions.")
        before = folder_hash(self.installed(name))
        if before == digest:
            return digest
        self._install(name, digest, self._known(st))
        self._record("use", name, before, digest)
        return digest

    def _prune(self, name: str, st: dict[str, Any]) -> None:
        keep = self._known(st)
        for p in (self.sdir(name) / "versions").iterdir():
            if p.name not in keep:
                shutil.rmtree(p, ignore_errors=True)

    # ----- change sets -----
    def _sets(self) -> dict[str, Any]:
        p = self.store / SETS_FILE
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}

    def _save_sets(self, sets: dict[str, Any]) -> None:
        self.store.mkdir(parents=True, exist_ok=True)
        p = self.store / SETS_FILE
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(sets, indent=2) + "\n", encoding="utf-8")
        tmp.replace(p)

    def begin_set(self, set_name: str, note: str | None = None) -> None:
        """Record the following operations in change set `set_name` (created on first use)."""
        if not NAME_RE.match(set_name):
            raise Refused(f"`{set_name}` is not a valid change-set name (lowercase letters, numbers, hyphens).")
        cs = self._sets().get(set_name)
        if cs and cs.get("undone"):
            raise Refused(f"Change set `{set_name}` was undone; start a new one with another name.")
        self.change_set = (set_name, note)

    def _record(self, op: str, skill: str, before: str | None, after: str | None) -> None:
        if self.change_set is None:
            return
        set_name, note = self.change_set
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        sets = self._sets()
        cs = sets.setdefault(set_name, {"note": note, "started": now, "steps": [], "undone": None})
        if note and not cs.get("note"):
            cs["note"] = note
        cs["steps"].append({"op": op, "skill": skill, "before": before, "after": after, "at": now})
        self._save_sets(sets)

    def sets(self) -> dict[str, Any]:
        return self._sets()

    def undo_plan(self, set_name: str) -> list[tuple[str, str, str | None]]:
        """The reverse steps of a change set, newest first, as (action, skill, version).

        Refuses, changing nothing, if any skill changed since the set or a needed version is gone."""
        cs = self._sets().get(set_name)
        if cs is None:
            raise Refused(f"No change set `{set_name}`. `sets` lists them.")
        if cs.get("undone"):
            raise Refused(f"Change set `{set_name}` was already undone ({cs['undone']}).")
        sim: dict[str, tuple[str | None, bool]] = {}  # skill -> (installed digest, has retired copy)

        def now(skill: str) -> tuple[str | None, bool]:
            if skill not in sim:
                sim[skill] = (folder_hash(self.installed(skill)), (self.sdir(skill) / "retired").is_dir())
            return sim[skill]

        plan: list[tuple[str, str, str | None]] = []
        for step in reversed(cs["steps"]):
            skill, op = step["skill"], step["op"]
            cur, retired = now(skill)
            if op == "retire":
                if cur is not None or not retired:
                    raise Refused(f"`{skill}` is no longer retired as `{set_name}` left it; nothing was changed.")
                plan.append(("restore", skill, None))
                sim[skill] = (step["before"], False)
                continue
            if cur != step["after"]:
                raise Refused(f"`{skill}` changed after `{set_name}`; undo or keep that change first. Nothing was changed.")
            if op == "restore" or step["before"] is None:
                if retired:
                    raise Refused(f"`{skill}` already has a retired copy; nothing was changed.")
                plan.append(("retire", skill, None))
                sim[skill] = (None, True)
            else:
                st = self.state(skill)
                if st is None or step["before"] not in self._known(st) or \
                        folder_hash(self.version(skill, step["before"])) != step["before"]:
                    raise Refused(f"The version of `{skill}` from before `{set_name}` is no longer kept; nothing was changed.")
                plan.append(("install", skill, step["before"]))
                sim[skill] = (step["before"], retired)
        return plan

    def undo_set(self, set_name: str) -> list[tuple[str, str, str | None]]:
        plan = self.undo_plan(set_name)
        recording, self.change_set = self.change_set, None
        try:
            for action, skill, digest in plan:
                if action == "restore":
                    self.restore(skill)
                elif action == "retire":
                    self.retire(skill)
                else:
                    assert digest
                    st = self.state(skill)
                    assert st is not None
                    self._install(skill, digest, self._known(st))
        finally:
            self.change_set = recording
        sets = self._sets()
        sets[set_name]["undone"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._save_sets(sets)
        return plan

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
        self._record("retire", name, digest, None)
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
        self._record("restore", name, None, digest)

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
                if st.get("created"):
                    notes.append("(created by the-one-skill)")
                if (sd / "draft").is_dir():
                    notes.append("(draft in progress)")
            if retired:
                notes.append("retired" if st is None else "(retired copy saved)")
            rows.append((sd.name, " ".join(notes)))
        return rows

    def guard_settings(self) -> dict[str, Any]:
        """Claude Code settings that block direct Edit/Write inside this skills folder."""
        script = Path(__file__).resolve().parent / "guard_skills.py"
        return {"hooks": {"PreToolUse": [{
            "matcher": "Edit|Write|MultiEdit|NotebookEdit",
            "hooks": [{"type": "command", "command": f'python3 "{script}" "{self.root}"'}],
        }]}}

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
    rec = argparse.ArgumentParser(add_help=False)
    rec.add_argument("--set", dest="change_set", help="Record this step in a change set, e.g. merge-csv-skills")
    rec.add_argument("--note", help="Why (stored with the change set)")
    for cmd in ("draft", "diff", "history"):
        sub.add_parser(cmd).add_argument("skill")
    for cmd in ("apply", "retire", "restore"):
        sub.add_parser(cmd, parents=[rec]).add_argument("skill")
    sub.add_parser("sets")
    sub.add_parser("guard", help="Print the Claude Code hook setting that blocks direct edits to skills")
    p = sub.add_parser("undo-set")
    p.add_argument("name")
    p.add_argument("--apply", action="store_true", help="Run the reverse steps (default: only show them)")
    p = sub.add_parser("new")
    p.add_argument("skill")
    p.add_argument("--from", dest="source", help="Folder with the new skill's files (default: a SKILL.md template)")
    p = sub.add_parser("use", parents=[rec])
    p.add_argument("skill")
    p.add_argument("version", help="original, previous, tuned, or a version id from `history`")
    a = ap.parse_args(argv)
    try:
        ctl = SkillCtl(a.root, a.store)
        if getattr(a, "change_set", None):
            ctl.begin_set(a.change_set, a.note)
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
        elif a.cmd == "guard":
            print(json.dumps(ctl.guard_settings(), indent=2))
            print("Merge this into .claude/settings.local.json (keep any hooks already there).", file=sys.stderr)
        elif a.cmd == "sets":
            sets = ctl.sets()
            if not sets:
                print("No change sets recorded.")
            for n, cs in sets.items():
                state = f"undone {cs['undone']}" if cs.get("undone") else f"{len(cs['steps'])} step(s)"
                print(f"{n:32} {cs['started']}  {state}  {cs.get('note') or ''}")
                for st in cs["steps"]:
                    print(f"{'':34}{st['op']:8} {st['skill']}")
        elif a.cmd == "undo-set":
            plan = ctl.undo_set(a.name) if a.apply else ctl.undo_plan(a.name)
            for action, skill, digest in plan:
                print(f"{action:8} {skill}" + (f" -> {digest}" if digest else ""))
            print("Undone." if a.apply else f"Nothing changed yet. Run `undo-set {a.name} --apply` after approval.")
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
            print(f"Applied. `use {a.skill} previous` steps back one version; `history {a.skill}` lists them all.")
        elif a.cmd == "use":
            digest = ctl.use(a.skill, a.version)
            print(f"`{a.skill}`: {a.version} version installed ({digest}).")
        elif a.cmd == "new":
            print(f"New skill draft: {ctl.new(a.skill, a.source)}\nWrite its files there, show `diff`, and `apply` after approval.")
        elif a.cmd == "history":
            for r in ctl.history(a.skill):
                mark = "*" if r["installed"] else " "
                print(f"{mark} {r['label']:22} {r['version']:18} {r['applied'] or ''}")
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
