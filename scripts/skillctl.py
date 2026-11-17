#!/usr/bin/env python3
"""Reversible, swap-based skill management for the-one-skill (pure Python 3 stdlib).

Model
-----
* Original skills are never edited. The first refinement moves a pristine copy of the
  original into the store and installs ONE working copy (same name, same path) in its place.
* Every later refinement edits that single working copy. The working copy's previous
  states are kept as history inside the store (outside the skills root), so the number of
  installed skills never grows.
* "Disabled" means "not inside the skills root": the host cannot load what is not there.
* Revert = park the working copy in the store and put the original back. Reapply = swap back.
* Before every swap the installed folder's content hash is checked against the manifest, so
  edits made by hand outside the-one-skill are never silently overwritten.

Layout (default store is a sibling of the skills root, e.g. ~/.claude/the-one-skill-store):

    <store>/<skill>/manifest.json
    <store>/<skill>/original/        pristine original (existing skills only; never modified)
    <store>/<skill>/draft/           staging copy being edited (refine-start -> commit)
    <store>/<skill>/parked/          working copy / new skill while reverted
    <store>/<skill>/retired/         installed folder while retired
    <store>/<skill>/history/NNNN/    previous states of the working copy (for undo)
    <store>/<skill>/discarded/...    states replaced by undo or a fresh refinement

Usage:
    python3 scripts/skillctl.py --root <skills_root> status
    python3 scripts/skillctl.py --root <skills_root> refine-start <skill>
    python3 scripts/skillctl.py --root <skills_root> diff <skill> [--against original]
    python3 scripts/skillctl.py --root <skills_root> commit <skill> --reason "..."
    python3 scripts/skillctl.py --root <skills_root> abort <skill>
    python3 scripts/skillctl.py --root <skills_root> undo <skill>
    python3 scripts/skillctl.py --root <skills_root> revert <skill>
    python3 scripts/skillctl.py --root <skills_root> reapply <skill>
    python3 scripts/skillctl.py --root <skills_root> install <staged_dir> [--replaces A B ...]
    python3 scripts/skillctl.py --root <skills_root> retire <skill>
    python3 scripts/skillctl.py --root <skills_root> unretire <skill>
    python3 scripts/skillctl.py --root <skills_root> lock|unlock <skill>
    python3 scripts/skillctl.py --root <skills_root> accept <skill>
    python3 scripts/skillctl.py --root <skills_root> prune <skill> [--keep N]
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import lint_skills  # noqa: E402

STORE_DIRNAME = "the-one-skill-store"
MANIFEST = "manifest.json"
SKIP_NAMES = {"__pycache__", ".DS_Store", "Thumbs.db", ".git"}

# States of a managed skill.
ORIGINAL = "original"  # the original is installed (any working copy is parked)
TUNED = "tuned"  # the working copy is installed
NEW = "new"  # a skill installed by the-one-skill is installed
UNINSTALLED = "uninstalled"  # a skill installed by the-one-skill is parked
RETIRED = "retired"  # nothing is installed; the last installed folder is in retired/
ACTIVE_STATES = {ORIGINAL, TUNED, NEW}


class SkillCtlError(RuntimeError):
    """A refused or impossible operation. Nothing was changed."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _ignore(_dir: str, names: list[str]) -> set[str]:
    return {n for n in names if n in SKIP_NAMES or n.endswith((".pyc", ".pyo"))}


def tree_hash(folder: Path) -> str:
    """Content hash of a skill folder: relative paths + bytes, ignoring caches."""
    digest = hashlib.sha256()
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        if any(part in SKIP_NAMES for part in rel.parts) or path.suffix in (".pyc", ".pyo"):
            continue
        if not path.is_file():
            continue
        digest.update(rel.as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def tree_files(folder: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    if not folder.is_dir():
        return files
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        if path.is_file() and not any(p in SKIP_NAMES for p in rel.parts) and path.suffix not in (".pyc", ".pyo"):
            files[rel.as_posix()] = path
    return files


def tree_diff(old: Path, new: Path, old_label: str = "a", new_label: str = "b") -> str:
    """Unified diff of every file in two skill folders (binary files reported by name)."""
    old_files, new_files = tree_files(old), tree_files(new)
    chunks: list[str] = []
    for rel in sorted(set(old_files) | set(new_files)):
        a, b = old_files.get(rel), new_files.get(rel)
        a_bytes = a.read_bytes() if a else b""
        b_bytes = b.read_bytes() if b else b""
        if a_bytes == b_bytes:
            continue
        try:
            a_lines = a_bytes.decode("utf-8").splitlines(keepends=True)
            b_lines = b_bytes.decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            chunks.append(f"Binary file {rel} differs\n")
            continue
        for line in difflib.unified_diff(
            a_lines,
            b_lines,
            fromfile=f"{old_label}/{rel}" if a else "/dev/null",
            tofile=f"{new_label}/{rel}" if b else "/dev/null",
        ):
            chunks.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
    return "".join(chunks)


def read_skill_name(folder: Path) -> str:
    skill_md = folder / "SKILL.md"
    if not skill_md.is_file():
        raise SkillCtlError(f"No SKILL.md in {folder}")
    fm = lint_skills.parse_frontmatter(skill_md.read_text(encoding="utf-8").replace("\r\n", "\n"))
    return fm.get("name") or folder.name


class SkillCtl:
    def __init__(self, root: str | Path, store: str | Path | None = None) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise SkillCtlError(f"Skills root not found: {self.root}")
        self.store = Path(store).expanduser().resolve() if store else self.root.parent / STORE_DIRNAME
        if self.store == self.root or self.root in self.store.parents:
            raise SkillCtlError("The store must be outside the skills root, or the host would load stored copies.")

    # ---------- paths & manifest ----------
    def installed(self, name: str) -> Path:
        return self.root / name

    def sdir(self, name: str) -> Path:
        return self.store / name

    def load(self, name: str) -> dict[str, Any] | None:
        path = self.sdir(name) / MANIFEST
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def require(self, name: str) -> dict[str, Any]:
        m = self.load(name)
        if m is None:
            raise SkillCtlError(f"`{name}` is not managed by the-one-skill yet.")
        return m

    def save(self, m: dict[str, Any]) -> None:
        folder = self.sdir(m["name"])
        folder.mkdir(parents=True, exist_ok=True)
        tmp = folder / (MANIFEST + ".tmp")
        tmp.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(folder / MANIFEST)

    @staticmethod
    def _log(m: dict[str, Any], action: str, detail: str = "") -> None:
        m.setdefault("log", []).append({"ts": _now(), "action": action, "detail": detail})

    def _adopt(self, name: str) -> dict[str, Any]:
        """Start managing an existing installed skill: save a pristine copy of the original."""
        src = self.installed(name)
        if not src.is_dir():
            raise SkillCtlError(f"No installed skill folder `{src}`.")
        folder = self.sdir(name)
        if (folder / "original").exists():
            raise SkillCtlError(f"Store already has an original for `{name}` but no manifest; inspect {folder}.")
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, folder / "original", symlinks=True, ignore=_ignore)
        digest = tree_hash(src)
        if tree_hash(folder / "original") != digest:
            raise SkillCtlError("Copy of the original does not match; aborting adoption.")
        m: dict[str, Any] = {
            "name": name,
            "root": str(self.root),
            "kind": "existing",
            "state": ORIGINAL,
            "locked": False,
            "original_hash": digest,
            "active_hash": digest,
            "history": [],
            "replaces": [],
            "replaced_by": None,
            "prev_state": None,
        }
        self._log(m, "adopt", "saved pristine original")
        self.save(m)
        return m

    def _load_or_adopt(self, name: str) -> dict[str, Any]:
        return self.load(name) or self._adopt(name)

    def _check_installed(self, m: dict[str, Any]) -> None:
        """Refuse if the installed folder is missing or was changed outside the-one-skill."""
        path = self.installed(m["name"])
        if not path.is_dir():
            raise SkillCtlError(f"`{m['name']}` is missing from {self.root}; expected state `{m['state']}`.")
        if tree_hash(path) != m["active_hash"]:
            raise SkillCtlError(
                f"`{m['name']}` was modified outside the-one-skill since its last recorded state. "
                f"Review with `diff`, then run `accept {m['name']}` to keep those edits."
            )

    def _check_unlocked(self, m: dict[str, Any]) -> None:
        if m.get("locked"):
            raise SkillCtlError(f"`{m['name']}` is locked; run `unlock {m['name']}` only if the user asks.")

    def _next_history_id(self, m: dict[str, Any]) -> str:
        ids = [int(h["id"]) for h in m["history"]]
        return f"{(max(ids) + 1) if ids else 1:04d}"

    def _discard(self, src: Path, name: str, label: str) -> Path:
        dest = self.sdir(name) / "discarded" / f"{_now()}-{label}"
        n = 1
        while dest.exists():
            dest = dest.with_name(f"{_now()}-{label}-{n}")
            n += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        return dest

    # ---------- refinement ----------
    def refine_start(self, name: str, restart: bool = False) -> Path:
        m = self._load_or_adopt(name)
        self._check_unlocked(m)
        if m["state"] not in ACTIVE_STATES:
            raise SkillCtlError(f"`{name}` is {m['state']}; reapply or unretire it before refining.")
        self._check_installed(m)
        draft = self.sdir(name) / "draft"
        if draft.exists():
            if not restart:
                raise SkillCtlError(f"A draft already exists at {draft}; edit it, `commit`, or `abort`.")
            shutil.rmtree(draft)
        shutil.copytree(self.installed(name), draft, symlinks=True, ignore=_ignore)
        self._log(m, "refine-start", str(draft))
        self.save(m)
        return draft

    def abort(self, name: str) -> None:
        m = self.require(name)
        draft = self.sdir(name) / "draft"
        if not draft.exists():
            raise SkillCtlError(f"No draft for `{name}`.")
        shutil.rmtree(draft)
        self._log(m, "abort")
        self.save(m)

    def diff(self, name: str, against: str = "auto") -> str:
        m = self.require(name)
        folder = self.sdir(name)
        installed = self.installed(name)
        if against == "original":
            if m["kind"] != "existing":
                raise SkillCtlError(f"`{name}` was installed by the-one-skill and has no original.")
            return tree_diff(folder / "original", installed, "original", "installed")
        if (folder / "draft").is_dir():
            return tree_diff(installed, folder / "draft", "installed", "draft")
        if m["state"] == TUNED:
            return tree_diff(folder / "original", installed, "original", "installed")
        if m["state"] == ORIGINAL and (folder / "parked").is_dir():
            return tree_diff(installed, folder / "parked", "installed", "parked")
        return ""

    def lint_draft(self, name: str) -> lint_skills.SkillLintResult:
        draft = self.sdir(name) / "draft"
        if not (draft / "SKILL.md").is_file():
            raise SkillCtlError(f"No draft SKILL.md for `{name}`.")
        return lint_skills.lint_skill_file(draft / "SKILL.md")

    def commit(self, name: str, reason: str) -> lint_skills.SkillLintResult:
        """Install the draft as the working copy. Security findings always block."""
        m = self.require(name)
        self._check_unlocked(m)
        folder = self.sdir(name)
        draft = folder / "draft"
        if not draft.is_dir():
            raise SkillCtlError(f"No draft for `{name}`; run `refine-start` first.")
        if read_skill_name(draft) != name:
            raise SkillCtlError("The draft's frontmatter `name` must stay the same as the installed skill.")
        result = self.lint_draft(name)
        if result.security_findings:
            raise SkillCtlError("Security findings block this commit:\n  " + "\n  ".join(result.security_findings))
        self._check_installed(m)
        installed = self.installed(name)

        if m["state"] == ORIGINAL:
            # Starting a fresh working copy from the original: older working-copy states are discarded
            # (kept on disk under discarded/), and the installed original is identical to original/.
            if (folder / "parked").exists():
                self._discard(folder / "parked", name, "parked")
            if (folder / "history").exists():
                self._discard(folder / "history", name, "history")
            m["history"] = []
            shutil.rmtree(installed)
            new_state = TUNED
        elif m["state"] in (TUNED, NEW):
            hid = self._next_history_id(m)
            dest = folder / "history" / hid
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(installed), str(dest))
            m["history"].append({"id": hid, "ts": _now(), "reason": m.get("last_reason", "")})
            new_state = m["state"]
        else:
            raise SkillCtlError(f"Cannot commit while `{name}` is {m['state']}.")

        shutil.move(str(draft), str(installed))
        m["state"] = new_state
        m["active_hash"] = tree_hash(installed)
        m["last_reason"] = reason
        self._log(m, "commit", reason)
        self.save(m)
        return result

    def undo(self, name: str) -> None:
        """Restore the working copy to its state before the last commit."""
        m = self.require(name)
        if m["state"] not in (TUNED, NEW):
            raise SkillCtlError(f"Nothing to undo: `{name}` is {m['state']}.")
        if not m["history"]:
            hint = "use `revert` to go back to the original" if m["state"] == TUNED else "use `revert` to uninstall it"
            raise SkillCtlError(f"No earlier working-copy state for `{name}`; {hint}.")
        self._check_installed(m)
        entry = m["history"].pop()
        self._discard(self.installed(name), name, "undone")
        shutil.move(str(self.sdir(name) / "history" / entry["id"]), str(self.installed(name)))
        m["active_hash"] = tree_hash(self.installed(name))
        m["last_reason"] = entry.get("reason", "")
        self._log(m, "undo", f"restored history {entry['id']}")
        self.save(m)

    # ---------- swaps ----------
    def revert(self, name: str) -> list[str]:
        """Swap back: original replaces the working copy, or a new skill is uninstalled."""
        m = self.require(name)
        folder = self.sdir(name)
        self._check_installed(m)
        if (folder / "parked").exists():
            raise SkillCtlError(f"Unexpected parked copy in {folder}; inspect it before reverting.")
        changed = [name]
        if m["state"] == TUNED:
            shutil.move(str(self.installed(name)), str(folder / "parked"))
            shutil.copytree(folder / "original", self.installed(name), symlinks=True)
            m["state"] = ORIGINAL
            m["active_hash"] = m["original_hash"]
        elif m["state"] == NEW:
            replaced = [self.require(r) for r in m["replaces"]]
            for r in replaced:
                if r["state"] != RETIRED or self.installed(r["name"]).exists():
                    raise SkillCtlError(f"Cannot restore `{r['name']}` (state {r['state']}); resolve it first.")
            shutil.move(str(self.installed(name)), str(folder / "parked"))
            m["state"] = UNINSTALLED
            m["active_hash"] = None
            for r in replaced:
                self._unretire(r)
                changed.append(r["name"])
        else:
            raise SkillCtlError(f"Nothing to revert: `{name}` is {m['state']}.")
        self._log(m, "revert")
        self.save(m)
        return changed

    def reapply(self, name: str) -> list[str]:
        """Undo a revert: the parked working copy (or new skill) is installed again."""
        m = self.require(name)
        folder = self.sdir(name)
        if not (folder / "parked").is_dir():
            raise SkillCtlError(f"Nothing parked for `{name}`.")
        changed = [name]
        if m["state"] == ORIGINAL:
            self._check_installed(m)
            shutil.rmtree(self.installed(name))  # identical to the stored original
            shutil.move(str(folder / "parked"), str(self.installed(name)))
            m["state"] = TUNED
        elif m["state"] == UNINSTALLED:
            if self.installed(name).exists():
                raise SkillCtlError(f"Another `{name}` is installed at {self.installed(name)}.")
            replaced = [self.require(r) for r in m["replaces"]]
            for r in replaced:
                self._check_unlocked(r)
                if r["state"] not in ACTIVE_STATES:
                    raise SkillCtlError(f"`{r['name']}` is {r['state']}; cannot retire it again.")
                self._check_installed(r)
            for r in replaced:
                self._retire(r, replaced_by=name)
                changed.append(r["name"])
            shutil.move(str(folder / "parked"), str(self.installed(name)))
            m["state"] = NEW
        else:
            raise SkillCtlError(f"Cannot reapply while `{name}` is {m['state']}.")
        m["active_hash"] = tree_hash(self.installed(name))
        self._log(m, "reapply")
        self.save(m)
        return changed

    # ---------- install / retire ----------
    def install(self, src: str | Path, replaces: Sequence[str] = ()) -> str:
        """Install a staged skill folder. Replaced skills are retired (merge / split)."""
        src_path = Path(src).expanduser().resolve()
        if self.root in src_path.parents or src_path == self.root:
            raise SkillCtlError("Stage the new skill outside the skills root before installing it.")
        name = read_skill_name(src_path)
        if self.installed(name).exists():
            raise SkillCtlError(f"A skill named `{name}` is already installed; refine it instead.")
        if self.load(name) is not None:
            raise SkillCtlError(f"The store already tracks `{name}`; pick another name or inspect {self.sdir(name)}.")
        result = lint_skills.lint_skill_file(src_path / "SKILL.md")
        if result.security_findings:
            raise SkillCtlError("Security findings block this install:\n  " + "\n  ".join(result.security_findings))
        replaced = [self._load_or_adopt(r) for r in replaces]
        for r in replaced:
            self._check_unlocked(r)
            if r["state"] not in ACTIVE_STATES:
                raise SkillCtlError(f"`{r['name']}` is {r['state']}; only installed skills can be replaced.")
            self._check_installed(r)
        for r in replaced:
            self._retire(r, replaced_by=name)
        shutil.copytree(src_path, self.installed(name), symlinks=True, ignore=_ignore)
        m: dict[str, Any] = {
            "name": name,
            "root": str(self.root),
            "kind": "new",
            "state": NEW,
            "locked": False,
            "original_hash": None,
            "active_hash": tree_hash(self.installed(name)),
            "history": [],
            "replaces": [r["name"] for r in replaced],
            "replaced_by": None,
            "prev_state": None,
        }
        self._log(m, "install", f"from {src_path}; replaces {m['replaces']}")
        self.save(m)
        return name

    def _retire(self, m: dict[str, Any], replaced_by: str | None = None) -> None:
        shutil.move(str(self.installed(m["name"])), str(self.sdir(m["name"]) / "retired"))
        m["prev_state"] = m["state"]
        m["state"] = RETIRED
        m["replaced_by"] = replaced_by
        m["active_hash"] = None
        self._log(m, "retire", f"replaced by {replaced_by}" if replaced_by else "")
        self.save(m)

    def _unretire(self, m: dict[str, Any]) -> None:
        if self.installed(m["name"]).exists():
            raise SkillCtlError(f"Another `{m['name']}` is installed; cannot unretire.")
        shutil.move(str(self.sdir(m["name"]) / "retired"), str(self.installed(m["name"])))
        m["state"] = m["prev_state"] or ORIGINAL
        m["prev_state"] = None
        m["replaced_by"] = None
        m["active_hash"] = tree_hash(self.installed(m["name"]))
        self._log(m, "unretire")
        self.save(m)

    def retire(self, name: str) -> None:
        m = self._load_or_adopt(name)
        self._check_unlocked(m)
        if m["state"] not in ACTIVE_STATES:
            raise SkillCtlError(f"`{name}` is {m['state']}; nothing installed to retire.")
        self._check_installed(m)
        self._retire(m)

    def unretire(self, name: str) -> None:
        m = self.require(name)
        if m["state"] != RETIRED:
            raise SkillCtlError(f"`{name}` is not retired.")
        if m.get("replaced_by"):
            raise SkillCtlError(f"`{name}` was replaced by `{m['replaced_by']}`; run `revert {m['replaced_by']}`.")
        self._unretire(m)

    # ---------- consent & housekeeping ----------
    def set_lock(self, name: str, locked: bool) -> None:
        m = self._load_or_adopt(name)
        m["locked"] = locked
        self._log(m, "lock" if locked else "unlock")
        self.save(m)

    def accept(self, name: str) -> None:
        """Keep edits made outside the-one-skill as the new recorded state of the installed skill."""
        m = self.require(name)
        installed = self.installed(name)
        if m["state"] not in ACTIVE_STATES or not installed.is_dir():
            raise SkillCtlError(f"`{name}` is not installed.")
        digest = tree_hash(installed)
        if digest == m["active_hash"]:
            return
        if m["state"] == ORIGINAL:
            # The user edited their own original: that becomes the original.
            self._discard(self.sdir(name) / "original", name, "original")
            shutil.copytree(installed, self.sdir(name) / "original", symlinks=True, ignore=_ignore)
            m["original_hash"] = digest
        m["active_hash"] = digest
        self._log(m, "accept", "kept edits made outside the-one-skill")
        self.save(m)

    def prune(self, name: str, keep: int = 5) -> int:
        m = self.require(name)
        folder = self.sdir(name)
        removed = 0
        while len(m["history"]) > keep:
            entry = m["history"].pop(0)
            shutil.rmtree(folder / "history" / entry["id"], ignore_errors=True)
            removed += 1
        if (folder / "discarded").exists():
            shutil.rmtree(folder / "discarded")
            removed += 1
        self._log(m, "prune", f"kept {keep} history entries")
        self.save(m)
        return removed

    def status(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        managed: set[str] = set()
        if self.store.is_dir():
            for manifest in sorted(self.store.glob(f"*/{MANIFEST}")):
                m = json.loads(manifest.read_text(encoding="utf-8"))
                managed.add(m["name"])
                installed = self.installed(m["name"])
                if m["state"] in ACTIVE_STATES:
                    if not installed.is_dir():
                        health = "MISSING"
                    elif tree_hash(installed) != m["active_hash"]:
                        health = "EDITED-OUTSIDE"
                    else:
                        health = "ok"
                else:
                    health = "CONFLICT" if installed.exists() else "ok"
                rows.append(
                    {
                        "name": m["name"],
                        "state": m["state"],
                        "health": health,
                        "locked": m.get("locked", False),
                        "history": len(m["history"]),
                        "draft": (self.sdir(m["name"]) / "draft").is_dir(),
                        "replaces": m.get("replaces", []),
                        "replaced_by": m.get("replaced_by"),
                    }
                )
        for skill_md in sorted(self.root.glob("*/SKILL.md")):
            name = skill_md.parent.name
            if name not in managed:
                rows.append({"name": name, "state": "unmanaged", "health": "ok", "locked": False,
                             "history": 0, "draft": False, "replaces": [], "replaced_by": None})
        return rows


def _print_status(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("No skills found.")
        return
    print(f"{'skill':32} {'state':12} {'health':15} {'lock':5} {'hist':4} draft  notes")
    for r in rows:
        notes = []
        if r["replaces"]:
            notes.append("replaces " + ", ".join(r["replaces"]))
        if r["replaced_by"]:
            notes.append("replaced by " + r["replaced_by"])
        print(
            f"{r['name']:32} {r['state']:12} {r['health']:15} {'yes' if r['locked'] else '-':5} "
            f"{r['history']:<4} {'yes' if r['draft'] else '-':6} {'; '.join(notes)}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reversible, swap-based skill management for the-one-skill.")
    parser.add_argument("--root", required=True, help="Skills root the host loads from (e.g. ~/.claude/skills).")
    parser.add_argument("--store", default=None, help=f"Store dir (default: <root>/../{STORE_DIRNAME}).")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p = sub.add_parser("refine-start")
    p.add_argument("skill")
    p.add_argument("--restart", action="store_true", help="Discard an existing draft and start over.")
    p = sub.add_parser("diff")
    p.add_argument("skill")
    p.add_argument("--against", choices=["auto", "original"], default="auto")
    p = sub.add_parser("commit")
    p.add_argument("skill")
    p.add_argument("--reason", required=True)
    for cmd in ("abort", "undo", "revert", "reapply", "retire", "unretire", "lock", "unlock", "accept"):
        sub.add_parser(cmd).add_argument("skill")
    p = sub.add_parser("install")
    p.add_argument("staged_dir")
    p.add_argument("--replaces", nargs="*", default=[])
    p = sub.add_parser("prune")
    p.add_argument("skill")
    p.add_argument("--keep", type=int, default=5)
    args = parser.parse_args(argv)

    try:
        ctl = SkillCtl(args.root, args.store)
        if args.cmd == "status":
            _print_status(ctl.status())
        elif args.cmd == "refine-start":
            draft = ctl.refine_start(args.skill, restart=args.restart)
            print(f"Draft ready: {draft}\nEdit files there, then run `diff` and `commit`.")
        elif args.cmd == "diff":
            print(ctl.diff(args.skill, args.against) or "(no differences)", end="")
        elif args.cmd == "commit":
            res = ctl.commit(args.skill, args.reason)
            for err in res.errors:
                print(f"LINT WARNING: {err}")
            print(f"Committed `{args.skill}` (tokens={res.token_count}). The working copy is installed.")
        elif args.cmd == "abort":
            ctl.abort(args.skill)
            print(f"Draft for `{args.skill}` discarded.")
        elif args.cmd == "undo":
            ctl.undo(args.skill)
            print(f"`{args.skill}` restored to its previous working-copy state.")
        elif args.cmd == "revert":
            print("Reverted: " + ", ".join(ctl.revert(args.skill)))
        elif args.cmd == "reapply":
            print("Reapplied: " + ", ".join(ctl.reapply(args.skill)))
        elif args.cmd == "install":
            name = ctl.install(args.staged_dir, args.replaces)
            print(f"Installed `{name}`" + (f"; retired {', '.join(args.replaces)}" if args.replaces else ""))
        elif args.cmd == "retire":
            ctl.retire(args.skill)
            print(f"`{args.skill}` retired (moved out of the skills root; `unretire` restores it).")
        elif args.cmd == "unretire":
            ctl.unretire(args.skill)
            print(f"`{args.skill}` is installed again.")
        elif args.cmd in ("lock", "unlock"):
            ctl.set_lock(args.skill, args.cmd == "lock")
            print(f"`{args.skill}` {args.cmd}ed.")
        elif args.cmd == "accept":
            ctl.accept(args.skill)
            print(f"Recorded the current contents of `{args.skill}`.")
        elif args.cmd == "prune":
            print(f"Removed {ctl.prune(args.skill, args.keep)} stored item(s).")
    except SkillCtlError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
