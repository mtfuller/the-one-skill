#!/usr/bin/env python3
"""Reversible skill management for the-one-skill (pure Python 3 stdlib).

For agents that keep skills as folders on disk (Claude Code, Codex, and other local agents).

Model
-----
* The store (a sibling of the skills root) is the source of truth. For each managed skill it
  keeps the `original` (the skill as first seen, or as installed from upstream) and, once
  refined, one `tuned` copy. The installed folder is always a copy of one of them.
* Originals are never edited. An approved upstream `update` replaces the original, and the
  replaced original is kept as `previous`.
* Inactive versions live in the store, outside the skills root, so the host never loads them.
* Edits made by hand to an installed skill are never overwritten: swaps refuse, and `edit`
  starts its draft from the hand-edited version so `save` keeps those edits.
* Every change runs through a journal. If a command is interrupted, the next command finishes it.

Commands
--------
    status                                  list skills, their versions and health
    diff <skill> [--upstream]               show what a pending save (or the tuned copy) changes
    edit <skill> [--fresh]                  start a draft of the skill (in the store) to edit
    update <skill> <staged_dir> [--source URL]
                                            start a draft that merges a new upstream version
                                            with your changes; conflicts are marked in the draft
    save <skill> --reason "..."             install the draft (after the user approved the diff)
    cancel <skill>                          drop the draft (and a pending update)
    use <skill> original|tuned              switch which version is installed
    install <staged_dir> [--source URL] [--replaces A B ...]
                                            install a new skill (optionally replacing others)
    retire <skill>                          move a skill out of the skills root (restores any
                                            skills it replaced)
    restore <skill>                         put a retired skill back
    lock <skill> / unlock <skill>           a locked skill is never changed
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
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
JOURNAL = ".journal.json"
TMP = ".tmp"
SKIP_NAMES = {"__pycache__", ".DS_Store", "Thumbs.db", ".git"}
SKIP_SUFFIXES = (".pyc", ".pyo")
VERSIONS = ("original", "tuned")
CONFLICT_RE = re.compile(r"^(<<<<<<< yours|>>>>>>> upstream)$", re.MULTILINE)


class SkillCtlError(RuntimeError):
    """A refused or impossible operation. Nothing was changed."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _ignore(_dir: str, names: list[str]) -> set[str]:
    return {n for n in names if n in SKIP_NAMES or n.endswith(SKIP_SUFFIXES)}


def tree_files(folder: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    if not folder.is_dir():
        return files
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        if any(p in SKIP_NAMES for p in rel.parts) or path.suffix in SKIP_SUFFIXES:
            continue
        if path.is_file():
            files[rel.as_posix()] = path
    return files


def tree_hash(folder: Path) -> str | None:
    """Content hash of a skill folder (relative paths + bytes, ignoring caches); None if absent."""
    if not folder.is_dir():
        return None
    digest = hashlib.sha256()
    for rel, path in tree_files(folder).items():
        digest.update(rel.encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def tree_diff(old: Path, new: Path, old_label: str = "a", new_label: str = "b") -> str:
    """Unified diff of every file in two skill folders (binary files reported by name)."""
    old_files, new_files = tree_files(old), tree_files(new)
    chunks: list[str] = []
    for rel in sorted(set(old_files) | set(new_files)):
        a, b = old_files.get(rel), new_files.get(rel)
        a_bytes = a.read_bytes() if a else b""
        b_bytes = b.read_bytes() if b else b""
        if a_bytes == b_bytes and bool(a) == bool(b):
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


# ---------- three-way merge (for upstream updates) ----------
def _changes(base: list[str], other: list[str], side: int) -> list[tuple[int, int, list[str], int]]:
    sm = difflib.SequenceMatcher(None, base, other, autojunk=False)
    return [(i1, i2, other[j1:j2], side) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]


def merge3(base: list[str], ours: list[str], theirs: list[str]) -> tuple[list[str], bool]:
    """Line-level three-way merge. Overlapping changes become a marked conflict block."""
    if ours == theirs or theirs == base:
        return ours, False
    if ours == base:
        return theirs, False
    changes = sorted(_changes(base, ours, 0) + _changes(base, theirs, 1), key=lambda c: (c[0], c[1]))
    out: list[str] = []
    pos, k, conflict = 0, 0, False
    while k < len(changes):
        start, end = changes[k][0], changes[k][1]
        group = [changes[k]]
        k += 1
        while k < len(changes) and changes[k][0] <= end:
            end = max(end, changes[k][1])
            group.append(changes[k])
            k += 1

        def apply(side: int) -> list[str]:
            res, p = [], start
            for i1, i2, lines, s in group:
                if s == side:
                    res += base[p:i1] + lines
                    p = i2
            return res + base[p:end]

        out += base[pos:start]
        sides = {c[3] for c in group}
        if len(sides) == 1:
            out += apply(sides.pop())
        else:
            mine, up = apply(0), apply(1)
            if mine == up:
                out += mine
            else:
                conflict = True
                block = ["<<<<<<< yours\n", *mine, "=======\n", *up, ">>>>>>> upstream\n"]
                out += [ln if ln.endswith("\n") else ln + "\n" for ln in block]
        pos = end
    return out + base[pos:], conflict


def merge_folders(base: Path, ours: Path, theirs: Path, dest: Path) -> list[str]:
    """Write a per-file three-way merge of three skill folders into dest; return conflicted files."""
    b_files, o_files, t_files = tree_files(base), tree_files(ours), tree_files(theirs)
    conflicts: list[str] = []
    dest.mkdir(parents=True)
    for rel in sorted(set(b_files) | set(o_files) | set(t_files)):
        b, o, t = (f[rel].read_bytes() if rel in f else None for f in (b_files, o_files, t_files))
        result: bytes | None
        if o == t or t == b:
            result = o
        elif o == b:
            result = t
        elif o is None or t is None or b is None:
            # Changed on one side, added or deleted on the other: keep what exists, flag it.
            result = t if t is not None else o
            conflicts.append(f"{rel} (changed on one side, added or deleted on the other)")
        else:
            try:
                lines = [x.decode("utf-8").splitlines(keepends=True) for x in (b, o, t)]
            except UnicodeDecodeError:
                result = t
                conflicts.append(f"{rel} (binary file changed by both; kept upstream)")
            else:
                merged, conflict = merge3(*lines)
                result = "".join(merged).encode("utf-8")
                if conflict:
                    conflicts.append(f"{rel} (resolve the <<<<<<< yours / >>>>>>> upstream blocks)")
        if result is not None:
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(result)
    return conflicts


def read_skill_name(folder: Path) -> str:
    skill_md = folder / "SKILL.md"
    if not skill_md.is_file():
        raise SkillCtlError(f"No SKILL.md in {folder}")
    fm = lint_skills.parse_frontmatter(skill_md.read_text(encoding="utf-8").replace("\r\n", "\n"))
    return fm.get("name") or folder.name


def has_conflict_markers(folder: Path) -> list[str]:
    found = []
    for rel, path in tree_files(folder).items():
        try:
            if CONFLICT_RE.search(path.read_text(encoding="utf-8")):
                found.append(rel)
        except UnicodeDecodeError:
            continue
    return found


class SkillCtl:
    def __init__(self, root: str | Path, store: str | Path | None = None) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise SkillCtlError(f"Skills root not found: {self.root}")
        self.store = Path(store).expanduser().resolve() if store else self.root.parent / STORE_DIRNAME
        if self.store == self.root or self.root in self.store.parents:
            raise SkillCtlError("The store must be outside the skills root, or the host would load stored copies.")
        self.recovered = self._recover()

    # ---------- paths & manifest ----------
    def installed(self, name: str) -> Path:
        return self.root / name

    def sdir(self, name: str) -> Path:
        return self.store / name

    def vdir(self, m: dict[str, Any], version: str) -> Path:
        return self.sdir(m["name"]) / version

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

    def save_manifest(self, m: dict[str, Any]) -> None:
        folder = self.sdir(m["name"])
        folder.mkdir(parents=True, exist_ok=True)
        tmp = folder / (MANIFEST + ".tmp")
        tmp.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(folder / MANIFEST)

    @staticmethod
    def _log(m: dict[str, Any], action: str, detail: str = "") -> None:
        m.setdefault("log", []).append({"ts": _now(), "action": action, "detail": detail})

    def _tmpdir(self) -> Path:
        path = self.store / TMP / _now()
        path.mkdir(parents=True)
        return path

    def _copy(self, src: Path, dst: Path) -> str:
        """Copy a skill folder and confirm the copy matches; return its hash."""
        shutil.copytree(src, dst, symlinks=True, ignore=_ignore)
        digest = tree_hash(dst)
        if digest != tree_hash(src):
            raise SkillCtlError(f"Copy of {src} does not match the source; nothing was changed.")
        assert digest is not None
        return digest

    # ---------- journal: every change is all-or-nothing ----------
    def _write_journal(self, journal: dict[str, Any]) -> None:
        tmp = self.store / (JOURNAL + ".tmp")
        tmp.write_text(json.dumps(journal, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.store / JOURNAL)

    def _commit(self, moves: list[tuple[Path, Path]], manifests: list[dict[str, Any]], cleanup: list[Path]) -> None:
        """Record the plan, then carry it out. An interrupted plan is finished by the next command."""
        journal = {
            "moves": [[str(a), str(b)] for a, b in moves],
            "done": 0,
            "manifests": manifests,
            "cleanup": [str(p) for p in cleanup],
        }
        self.store.mkdir(parents=True, exist_ok=True)
        self._write_journal(journal)
        self._run_journal(journal)

    def _run_journal(self, journal: dict[str, Any]) -> None:
        moves = journal["moves"]
        while journal["done"] < len(moves):
            src, dst = (Path(p) for p in moves[journal["done"]])
            if src.exists() or src.is_symlink():
                if dst.exists():  # a cross-device move was interrupted part-way: dst is a partial copy
                    shutil.rmtree(dst)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
            elif not dst.exists():
                raise SkillCtlError(f"Interrupted operation cannot continue: neither {src} nor {dst} exists.")
            journal["done"] += 1
            self._write_journal(journal)
        for m in journal["manifests"]:
            self.save_manifest(m)
        for path in journal["cleanup"]:
            shutil.rmtree(path, ignore_errors=True)
        (self.store / JOURNAL).unlink()

    def _recover(self) -> bool:
        path = self.store / JOURNAL
        recovered = False
        if path.is_file():
            self._run_journal(json.loads(path.read_text(encoding="utf-8")))
            recovered = True
        if (self.store / TMP).is_dir():
            shutil.rmtree(self.store / TMP, ignore_errors=True)  # copies made before an interrupted plan
        return recovered

    # ---------- checks ----------
    def _check_unlocked(self, m: dict[str, Any]) -> None:
        if m.get("locked"):
            raise SkillCtlError(f"`{m['name']}` is locked; run `unlock {m['name']}` only if the user asks.")

    def _check_no_pending(self, m: dict[str, Any]) -> None:
        if m.get("pending"):
            raise SkillCtlError(f"`{m['name']}` has a pending {m['pending']}; `save` or `cancel` it first.")

    def _check_installed(self, m: dict[str, Any], also_ok: str | None = None) -> None:
        """Refuse if the installed folder is missing or was changed outside the-one-skill."""
        path = self.installed(m["name"])
        if not path.is_dir():
            raise SkillCtlError(f"`{m['name']}` is missing from {self.root}; expected the {m['active']} version.")
        digest = tree_hash(path)
        if digest not in (m[f"{m['active']}_hash"], also_ok):
            raise SkillCtlError(
                f"`{m['name']}` was edited outside the-one-skill. To keep those edits, run `edit {m['name']}` "
                f"(the draft starts from the edited version) and `save` it; nothing was changed."
            )

    def _check_intact(self, m: dict[str, Any], version: str) -> None:
        if tree_hash(self.vdir(m, version)) != m.get(f"{version}_hash"):
            raise SkillCtlError(
                f"The stored {version} of `{m['name']}` is missing or was changed ({self.vdir(m, version)}); "
                "nothing was changed."
            )

    def _adopt(self, name: str) -> dict[str, Any]:
        """Start managing an installed skill: keep an exact copy of it as the original."""
        src = self.installed(name)
        if src.is_symlink():
            raise SkillCtlError(
                f"`{name}` is a link to {src.resolve()}. the-one-skill does not manage linked skills: "
                "edit the linked folder directly, or replace the link with a real folder."
            )
        if not src.is_dir():
            raise SkillCtlError(f"No installed skill folder `{src}`.")
        if self.sdir(name).exists():
            raise SkillCtlError(f"The store has files for `{name}` but no manifest; inspect {self.sdir(name)}.")
        tmp = self._tmpdir()
        digest = self._copy(src, tmp / "original")
        m: dict[str, Any] = {
            "name": name,
            "source": None,
            "active": "original",
            "last_active": None,
            "locked": False,
            "original_hash": digest,
            "tuned_hash": None,
            "previous_hash": None,
            "replaces": [],
            "replaced_by": None,
            "pending": None,
            "draft_base": None,
            "incoming_hash": None,
            "conflicts": [],
        }
        self._log(m, "adopt", "kept an exact copy of the installed skill as the original")
        self._commit([(tmp / "original", self.vdir(m, "original"))], [m], [tmp])
        return m

    def _load_or_adopt(self, name: str) -> dict[str, Any]:
        return self.load(name) or self._adopt(name)

    # ---------- drafts: edit / update -> save / cancel ----------
    def edit(self, name: str, fresh: bool = False) -> Path:
        m = self._load_or_adopt(name)
        self._check_unlocked(m)
        if m["active"] is None:
            raise SkillCtlError(f"`{name}` is retired; `restore` it before editing.")
        if m.get("pending") and not fresh:
            raise SkillCtlError(f"`{name}` has a pending {m['pending']}; keep editing it, `save`, or `cancel`.")
        installed = self.installed(name)
        if not installed.is_dir():
            raise SkillCtlError(f"`{name}` is missing from {self.root}.")
        self._clear_draft(m)
        draft = self.vdir(m, "draft")
        m["draft_base"] = self._copy(installed, draft)  # includes any edits made by hand
        m["pending"] = "edit"
        self._log(m, "edit", str(draft))
        self.save_manifest(m)
        return draft

    def update(self, name: str, staged: str | Path, source: str | None = None) -> tuple[Path | None, list[str]]:
        """Stage a new upstream version. Returns (draft, conflicts); draft is None if already up to date."""
        m = self._load_or_adopt(name)
        self._check_unlocked(m)
        self._check_no_pending(m)
        if m["active"] is None:
            raise SkillCtlError(f"`{name}` is retired; `restore` it before updating.")
        staged_path = self._staged(staged)
        if read_skill_name(staged_path) != name:
            raise SkillCtlError(f"The staged skill's frontmatter `name` must be `{name}`.")
        self._security_gate(staged_path, "update")
        self._check_installed(m)
        self._check_intact(m, "original")
        if tree_hash(staged_path) == m["original_hash"]:
            return None, []
        incoming, draft = self.vdir(m, "incoming"), self.vdir(m, "draft")
        m["incoming_hash"] = self._copy(staged_path, incoming)
        if m["tuned_hash"]:
            self._check_intact(m, "tuned")
            conflicts = merge_folders(self.vdir(m, "original"), self.vdir(m, "tuned"), incoming, draft)
        else:
            self._copy(incoming, draft)
            conflicts = []
        m["pending"] = "update"
        m["pending_source"] = source or m.get("source")
        m["draft_base"] = m[f"{m['active']}_hash"]
        m["conflicts"] = conflicts
        self._log(m, "update-start", f"from {source or m.get('source') or staged_path}")
        self.save_manifest(m)
        return draft, conflicts

    def _clear_draft(self, m: dict[str, Any]) -> None:
        for d in ("draft", "incoming"):
            shutil.rmtree(self.vdir(m, d), ignore_errors=True)
        m.update(pending=None, draft_base=None, incoming_hash=None, conflicts=[])
        m.pop("pending_source", None)

    def cancel(self, name: str) -> None:
        m = self.require(name)
        if not m.get("pending"):
            raise SkillCtlError(f"Nothing pending for `{name}`.")
        self._clear_draft(m)
        self._log(m, "cancel")
        self.save_manifest(m)

    def save(self, name: str, reason: str) -> lint_skills.SkillLintResult:
        """Install the draft. The caller must have shown the diff and had the user approve it."""
        m = self.require(name)
        self._check_unlocked(m)
        if not m.get("pending"):
            raise SkillCtlError(f"Nothing to save for `{name}`; run `edit` or `update` first.")
        sd = self.sdir(name)
        draft = sd / "draft"
        if not draft.is_dir():
            raise SkillCtlError(f"The draft for `{name}` is missing; run `cancel` and start again.")
        if read_skill_name(draft) != name:
            raise SkillCtlError("The draft's frontmatter `name` must stay the same as the installed skill.")
        marked = has_conflict_markers(draft)
        if marked:
            raise SkillCtlError("Resolve the merge conflict blocks first: " + ", ".join(marked))
        result = self._security_gate(draft, "save")
        self._check_installed(m, also_ok=m.get("draft_base"))
        is_update = m["pending"] == "update"
        if is_update and tree_hash(sd / "incoming") != m["incoming_hash"]:
            raise SkillCtlError(f"The staged upstream copy for `{name}` changed; `cancel` and run `update` again.")

        draft_hash = tree_hash(draft)
        new_original_hash = m["incoming_hash"] if is_update else m["original_hash"]
        tmp = self._tmpdir()
        self._copy(draft, tmp / "new")
        moves: list[tuple[Path, Path]] = [
            (self.installed(name), tmp / "old"),
            (tmp / "new", self.installed(name)),
        ]
        if is_update:
            if (sd / "previous").exists():
                moves.append((sd / "previous", tmp / "previous-old"))
            moves += [(sd / "original", sd / "previous"), (sd / "incoming", sd / "original")]
        if (sd / "tuned").exists():
            moves.append((sd / "tuned", tmp / "tuned-old"))
        new = dict(m)
        if draft_hash == new_original_hash:
            # The draft is the original itself: no tuned copy is needed.
            moves.append((draft, tmp / "draft"))
            new.update(active="original", tuned_hash=None)
        else:
            moves.append((draft, sd / "tuned"))
            new.update(active="tuned", tuned_hash=draft_hash)
        if is_update:
            new.update(
                previous_hash=m["original_hash"],
                original_hash=m["incoming_hash"],
                source=m.get("pending_source") or m.get("source"),
            )
        self._clear_draft_fields(new)
        self._log(new, "update" if is_update else "save", reason)
        self._commit(moves, [new], [tmp])
        return result

    @staticmethod
    def _clear_draft_fields(m: dict[str, Any]) -> None:
        m.update(pending=None, draft_base=None, incoming_hash=None, conflicts=[])
        m.pop("pending_source", None)

    def diff(self, name: str, upstream: bool = False) -> str:
        m = self.require(name)
        sd = self.sdir(name)
        if upstream:
            if m.get("pending") != "update":
                raise SkillCtlError(f"No pending update for `{name}`.")
            return tree_diff(sd / "original", sd / "incoming", "current-upstream", "new-upstream")
        if m.get("pending"):
            return tree_diff(self.installed(name), sd / "draft", "installed", "draft")
        if m["tuned_hash"]:
            return tree_diff(sd / "original", sd / "tuned", "original", "tuned")
        return ""

    # ---------- switching & installing ----------
    def use(self, name: str, version: str) -> None:
        if version not in VERSIONS:
            raise SkillCtlError(f"Version must be one of {VERSIONS}.")
        m = self.require(name)
        self._check_unlocked(m)
        self._check_no_pending(m)
        if m["active"] is None:
            raise SkillCtlError(f"`{name}` is retired; `restore` it first.")
        if m["active"] == version:
            return
        if not m[f"{version}_hash"]:
            raise SkillCtlError(f"`{name}` has no {version} version.")
        self._check_installed(m)
        self._check_intact(m, version)
        tmp = self._tmpdir()
        self._copy(self.vdir(m, version), tmp / "new")
        new = dict(m, active=version)
        self._log(new, "use", version)
        self._commit([(self.installed(name), tmp / "old"), (tmp / "new", self.installed(name))], [new], [tmp])

    def _staged(self, staged: str | Path) -> Path:
        path = Path(staged).expanduser().resolve()
        if path == self.root or self.root in path.parents:
            raise SkillCtlError("Stage the skill outside the skills root first.")
        if not (path / "SKILL.md").is_file():
            raise SkillCtlError(f"No SKILL.md in {path}.")
        return path

    @staticmethod
    def _security_gate(folder: Path, what: str) -> lint_skills.SkillLintResult:
        result = lint_skills.lint_skill_file(folder / "SKILL.md")
        if result.security_findings:
            raise SkillCtlError(f"Security findings block this {what}:\n  " + "\n  ".join(result.security_findings))
        return result

    def install(self, staged: str | Path, source: str | None = None, replaces: Sequence[str] = ()) -> str:
        """Install a staged skill. Replaced skills are retired (merge / split); `retire` restores them."""
        src = self._staged(staged)
        name = read_skill_name(src)
        if self.installed(name).exists() or self.installed(name).is_symlink():
            raise SkillCtlError(f"A skill named `{name}` is already installed; use `update` or `edit` instead.")
        if self.load(name) is not None:
            raise SkillCtlError(f"`{name}` is retired in the store; `restore` it, then `update` it.")
        self._security_gate(src, "install")
        names = list(dict.fromkeys(replaces))
        if name in names:
            raise SkillCtlError("A skill cannot replace itself.")
        replaced = [self._load_or_adopt(r) for r in names]
        for r in replaced:
            self._check_unlocked(r)
            self._check_no_pending(r)
            if r["active"] is None:
                raise SkillCtlError(f"`{r['name']}` is retired; only installed skills can be replaced.")
            self._check_installed(r)
        tmp = self._tmpdir()
        digest = self._copy(src, tmp / "original")
        self._copy(src, tmp / "new")
        m: dict[str, Any] = {
            "name": name,
            "source": source,
            "active": "original",
            "last_active": None,
            "locked": False,
            "original_hash": digest,
            "tuned_hash": None,
            "previous_hash": None,
            "replaces": names,
            "replaced_by": None,
            "pending": None,
            "draft_base": None,
            "incoming_hash": None,
            "conflicts": [],
        }
        self._log(m, "install", f"from {source or src}; replaces {names}")
        moves = [(tmp / "original", self.sdir(name) / "original"), (tmp / "new", self.installed(name))]
        manifests = [m]
        for r in replaced:
            moves.append((self.installed(r["name"]), tmp / f"old-{r['name']}"))
            manifests.append(self._retired(r, replaced_by=name))
        self._commit(moves, manifests, [tmp])
        return name

    def _retired(self, m: dict[str, Any], replaced_by: str | None = None) -> dict[str, Any]:
        new = dict(m, last_active=m["active"], active=None, replaced_by=replaced_by)
        self._log(new, "retire", f"replaced by {replaced_by}" if replaced_by else "")
        return new

    def retire(self, name: str) -> list[str]:
        """Remove the skill from the skills root. Skills it replaced are put back. Returns restored names."""
        m = self._load_or_adopt(name)
        self._check_unlocked(m)
        self._check_no_pending(m)
        if m["active"] is None:
            raise SkillCtlError(f"`{name}` is already retired.")
        self._check_installed(m)
        tmp = self._tmpdir()
        moves = [(self.installed(name), tmp / "old")]
        manifests = [self._retired(m)]
        restored = []
        for rname in m.get("replaces", []):
            r = self.load(rname)
            if not r or r["active"] is not None or r.get("replaced_by") != name:
                continue
            if self.installed(rname).exists():
                raise SkillCtlError(f"Cannot restore `{rname}`: another `{rname}` is installed.")
            self._check_intact(r, r["last_active"])
            self._copy(self.vdir(r, r["last_active"]), tmp / f"new-{rname}")
            moves.append((tmp / f"new-{rname}", self.installed(rname)))
            back = dict(r, active=r["last_active"], last_active=None, replaced_by=None)
            self._log(back, "restore", f"{name} was retired")
            manifests.append(back)
            restored.append(rname)
        self._commit(moves, manifests, [tmp])
        return restored

    def restore(self, name: str) -> list[str]:
        """Put a retired skill back. If it had replaced other skills, they are retired again."""
        m = self.require(name)
        if m["active"] is not None:
            raise SkillCtlError(f"`{name}` is not retired.")
        by = m.get("replaced_by")
        if by and (self.load(by) or {}).get("active"):
            raise SkillCtlError(f"`{name}` was replaced by `{by}`; `retire {by}` puts `{name}` back.")
        if self.installed(name).exists():
            raise SkillCtlError(f"Another `{name}` is installed at {self.installed(name)}.")
        version = m["last_active"] or "original"
        self._check_intact(m, version)
        to_retire = []
        for rname in m.get("replaces", []):
            r = self.load(rname)
            if r and r["active"] is not None:
                self._check_unlocked(r)
                self._check_no_pending(r)
                self._check_installed(r)
                to_retire.append(r)
        tmp = self._tmpdir()
        self._copy(self.vdir(m, version), tmp / "new")
        moves = [(tmp / "new", self.installed(name))]
        back = dict(m, active=version, last_active=None, replaced_by=None)
        self._log(back, "restore")
        manifests = [back]
        for r in to_retire:
            moves.append((self.installed(r["name"]), tmp / f"old-{r['name']}"))
            manifests.append(self._retired(r, replaced_by=name))
        self._commit(moves, manifests, [tmp])
        return [r["name"] for r in to_retire]

    def set_lock(self, name: str, locked: bool) -> None:
        m = self._load_or_adopt(name)
        m["locked"] = locked
        self._log(m, "lock" if locked else "unlock")
        self.save_manifest(m)

    # ---------- status ----------
    def status(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        managed: set[str] = set()
        if self.store.is_dir():
            for manifest in sorted(self.store.glob(f"*/{MANIFEST}")):
                m = json.loads(manifest.read_text(encoding="utf-8"))
                managed.add(m["name"])
                installed = self.installed(m["name"])
                if m["active"] is None:
                    health = "CONFLICT" if installed.exists() else "ok"
                    state = "retired"
                else:
                    state = m["active"]
                    digest = tree_hash(installed)
                    if digest is None:
                        health = "MISSING"
                    elif digest == m[f"{state}_hash"]:
                        health = "ok"
                    elif m.get("pending") == "edit" and digest == m.get("draft_base"):
                        health = "ok"
                    else:
                        health = "EDITED"
                for v in VERSIONS:
                    if m.get(f"{v}_hash") and tree_hash(self.vdir(m, v)) != m[f"{v}_hash"]:
                        health = "STORE-DAMAGED"
                rows.append(
                    {
                        "name": m["name"],
                        "state": state,
                        "health": health,
                        "locked": m.get("locked", False),
                        "has_tuned": bool(m.get("tuned_hash")),
                        "pending": m.get("pending"),
                        "source": m.get("source"),
                        "replaces": m.get("replaces", []),
                        "replaced_by": m.get("replaced_by"),
                    }
                )
        for skill_md in sorted(self.root.glob("*/SKILL.md")):
            name = skill_md.parent.name
            if name not in managed:
                rows.append({"name": name, "state": "unmanaged", "health": "ok", "locked": False,
                             "has_tuned": False, "pending": None, "source": None,
                             "replaces": [], "replaced_by": None})
        return rows


def _print_status(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("No skills found.")
        return
    print(f"{'skill':32} {'installed':10} {'health':14} {'lock':5} notes")
    for r in rows:
        notes = []
        if r["has_tuned"] and r["state"] == "original":
            notes.append("tuned copy available")
        if r["pending"]:
            notes.append(f"pending {r['pending']}")
        if r["source"]:
            notes.append(f"source {r['source']}")
        if r["replaces"]:
            notes.append("replaces " + ", ".join(r["replaces"]))
        if r["replaced_by"]:
            notes.append("replaced by " + r["replaced_by"])
        print(f"{r['name']:32} {r['state']:10} {r['health']:14} {'yes' if r['locked'] else '-':5} {'; '.join(notes)}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reversible skill management for the-one-skill.")
    parser.add_argument("--root", required=True, help="Skills root the host loads from (e.g. ~/.claude/skills).")
    parser.add_argument("--store", default=None, help=f"Store dir (default: <root>/../{STORE_DIRNAME}).")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p = sub.add_parser("diff")
    p.add_argument("skill")
    p.add_argument("--upstream", action="store_true", help="Show what changed upstream (pending update).")
    p = sub.add_parser("edit")
    p.add_argument("skill")
    p.add_argument("--fresh", action="store_true", help="Drop a pending draft and start over.")
    p = sub.add_parser("update")
    p.add_argument("skill")
    p.add_argument("staged_dir")
    p.add_argument("--source", default=None)
    p = sub.add_parser("save")
    p.add_argument("skill")
    p.add_argument("--reason", required=True)
    p = sub.add_parser("use")
    p.add_argument("skill")
    p.add_argument("version", choices=VERSIONS)
    p = sub.add_parser("install")
    p.add_argument("staged_dir")
    p.add_argument("--source", default=None)
    p.add_argument("--replaces", nargs="*", default=[])
    for cmd in ("cancel", "retire", "restore", "lock", "unlock"):
        sub.add_parser(cmd).add_argument("skill")
    args = parser.parse_args(argv)

    try:
        ctl = SkillCtl(args.root, args.store)
        if ctl.recovered:
            print("Note: finished an operation that was interrupted earlier.")
        if args.cmd == "status":
            _print_status(ctl.status())
        elif args.cmd == "diff":
            print(ctl.diff(args.skill, args.upstream) or "(no differences)", end="")
        elif args.cmd == "edit":
            draft = ctl.edit(args.skill, fresh=args.fresh)
            print(f"Draft ready: {draft}\nEdit files there, show `diff`, and `save` after the user approves.")
        elif args.cmd == "update":
            draft, conflicts = ctl.update(args.skill, args.staged_dir, args.source)
            if draft is None:
                print(f"`{args.skill}` is already up to date.")
            else:
                print(f"Update draft ready: {draft}")
                for c in conflicts:
                    print(f"CONFLICT: {c}")
                print("Show `diff --upstream` and `diff`, resolve any conflicts, then `save` after approval.")
        elif args.cmd == "save":
            res = ctl.save(args.skill, args.reason)
            for err in res.errors:
                print(f"LINT ERROR: {err}")
            for warn in res.warnings:
                print(f"LINT WARNING: {warn}")
            print(f"Saved `{args.skill}` (tokens={res.token_count}). `use {args.skill} original` switches back.")
        elif args.cmd == "cancel":
            ctl.cancel(args.skill)
            print(f"Draft for `{args.skill}` dropped.")
        elif args.cmd == "use":
            ctl.use(args.skill, args.version)
            print(f"`{args.skill}`: the {args.version} version is installed.")
        elif args.cmd == "install":
            name = ctl.install(args.staged_dir, args.source, args.replaces)
            print(f"Installed `{name}`" + (f"; retired {', '.join(args.replaces)}" if args.replaces else ""))
        elif args.cmd == "retire":
            restored = ctl.retire(args.skill)
            print(f"`{args.skill}` retired (moved to the store; `restore` puts it back).")
            if restored:
                print("Restored: " + ", ".join(restored))
        elif args.cmd == "restore":
            retired = ctl.restore(args.skill)
            print(f"`{args.skill}` is installed again." + (f" Retired: {', '.join(retired)}" if retired else ""))
        elif args.cmd in ("lock", "unlock"):
            ctl.set_lock(args.skill, args.cmd == "lock")
            print(f"`{args.skill}` {args.cmd}ed.")
    except SkillCtlError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
