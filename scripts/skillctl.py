#!/usr/bin/env python3
"""Safe, reversible skill changes for Claude Code (pure Python 3 standard library).

How it works
------------
* The first `draft` of a skill saves an exact copy of the installed skill as its original, in a
  store outside the skills folder (default: <project>/.tos-store for <project>/.claude/skills, see
  default_store). It is never modified.
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
* `upgrade <skill> --from <folder>` drafts a new release merged three ways: changes in the release
  go in, your local changes since the last release you installed stay, `--keep` paths (such as
  references/agentspace) are kept as they are, and both-changed lines become conflict markers to
  resolve in the draft. `readonly-*` files may change only to exactly the release's version.
* `overlap` compares skills in what triggers them and in what they do, and lists instruction blocks
  repeated across skills (scripts/overlap.py). `--candidate` checks one draft or folder against the
  roster before it is proposed; `--also` adds read-only folders (personal, plugin, built-in skills).
* `new --from <folder> --published` installs a skill exactly as its publisher released it and keeps
  that copy as the base, so a later `upgrade` from the publisher keeps your tweaks.
* `usage` counts how often, and when last, each skill was used in Claude Code transcripts.
* `--set <name>` on apply/use/retire/restore records the step in a change set (in the store, so it
  needs no extra approval). `sets` lists them; `undo-set <name>` shows the reverse steps and
  `undo-set <name> --apply` runs them, newest first, after checking nothing changed since.

Commands
--------
    python3 scripts/skillctl.py --root <skills_folder> list [--json] [--languages python,bash]
    python3 scripts/skillctl.py --root <skills_folder> overlap [--candidate <skill|folder>] [--also <folder> ...] [--json]
    python3 scripts/skillctl.py --root <skills_folder> status
    python3 scripts/skillctl.py --root <skills_folder> draft <skill>
    python3 scripts/skillctl.py --root <skills_folder> diff <skill>
    python3 scripts/skillctl.py --root <skills_folder> apply <skill>
    python3 scripts/skillctl.py --root <skills_folder> use <skill> original|previous|tuned|<version>
    python3 scripts/skillctl.py --root <skills_folder> history <skill>
    python3 scripts/skillctl.py --root <skills_folder> new <skill> [--from <folder> [--published]]
    python3 scripts/skillctl.py --root <skills_folder> usage [--transcripts ~/.claude/projects] [--json]
    python3 scripts/skillctl.py --root <skills_folder> sets
    python3 scripts/skillctl.py --root <skills_folder> guard     (prints the Claude Code hook setting)
    python3 scripts/skillctl.py --root <skills_folder> upgrade <skill> --from <folder> [--keep <path> ...]
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overlap as _overlap  # noqa: E402

STORE_DIRNAME = ".tos-store"
LEGACY_STORE_DIRNAME = "the-one-skill-store"


def default_store(root: Path) -> Path:
    """Where the store goes when --store isn't given.

    <x>/.claude/skills -> <x>/.tos-store (outside .claude/, so editing drafts needs no permission
    prompt on Claude Code); any other skills folder -> a .tos-store next to it. A store already in
    the old place (<skills folder's parent>/the-one-skill-store) keeps being used until
    `move-store` moves it."""
    legacy = root.parent / LEGACY_STORE_DIRNAME
    if legacy.is_dir():
        return legacy
    if root.name == "skills" and root.parent.name == ".claude":
        return root.parent.parent / STORE_DIRNAME
    return root.parent / STORE_DIRNAME
SKIP = {"__pycache__", ".DS_Store", "Thumbs.db", ".git"}
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
READONLY_PREFIX = "readonly-"
MAX_SKILL_LINES = 500
SETS_FILE = "changesets.json"
KEEP_APPLIED = 5  # applied versions kept per skill, besides the original
MAX_DESCRIPTION = 1024  # Claude's limit for a skill description; other hosts are similar or larger
NEW_SKILL_TEMPLATE = """---
name: {name}
description: <What it does, in the words a user would use>. Use when <the requests and situations that call for it>. Do not use when <a neighbouring job> (use <other-skill>).
---

# {name}

<One or two sentences: the job, and what a good result looks like.>

## Inputs
- <What the skill needs, and where it comes from.>

## Steps
1. <Judgement stays in the instructions: what to look at, what to decide, how to word the result.>
2. Run `python3 scripts/<script>.py <args>` for <the part that must come out the same every time>. It prints <what>.

## Output
<The exact shape of the result, with a short example.>

## Edge cases
- <A case that went wrong before, and what to do instead.>

## More detail
- `references/<topic>.md`: <read when ...>

<!-- Anything that must come out the same way every time (parsing, validating, converting, computing,
exact formats) belongs in a script under scripts/, run from the Steps above, not in prose. -->
"""
TEMPLATE_MARKERS = ("<What it does", "<One or two sentences", "<What the skill needs", "<Judgement stays",
                    "<the part that must", "<The exact shape", "<A case that went wrong", "references/<topic>.md",
                    "scripts/<script>.py")
CODE_SUFFIXES = _overlap.CODE_SUFFIXES
LANGUAGES = {  # name -> script file suffixes, for `list --languages`
    "python": (".py",), "bash": (".sh", ".bash"), "sh": (".sh",), "javascript": (".js", ".mjs", ".cjs"),
    "node": (".js", ".mjs", ".cjs"), "typescript": (".ts",), "ruby": (".rb",), "perl": (".pl",),
    "powershell": (".ps1",), "r": (".r",), "go": (".go",), "rust": (".rs",), "java": (".java",),
    "kotlin": (".kt",), "swift": (".swift",), "php": (".php",), "lua": (".lua",), "sql": (".sql",),
}


def shebang_suffix(f: Path) -> str:
    """The suffix a script with no extension would have, from its #! line ("" if none)."""
    try:
        with f.open("rb") as fh:
            first = fh.readline(200).decode("utf-8", "replace")
    except OSError:
        return ""
    if not first.startswith("#!"):
        return ""
    words = first[2:].replace("/", " ").split()
    for w in reversed(words):
        w = re.sub(r"[\d.]+$", "", w)  # python3 -> python
        if w in LANGUAGES:
            return LANGUAGES[w][0]
    return ""


def language_suffixes(languages: Sequence[str]) -> set[str]:
    """File suffixes for language names such as "python,bash"; refuses names it doesn't know."""
    out: set[str] = set()
    for name in (n.strip().lower() for n in languages if n.strip()):
        if name not in LANGUAGES:
            raise Refused(f"Unknown script language `{name}`; known: {', '.join(sorted(LANGUAGES))}.")
        out.update(LANGUAGES[name])
    return out
ABSOLUTE_PATH_RE = re.compile(r"(?<![\w.~])(/home/[^\s`'\")]+|/Users/[^\s`'\")]+|[A-Za-z]:\\\\Users\\\\[^\s`'\")]+)")


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


def structure_issues(folder: Path) -> list[str]:
    """Problems in how a skill's files fit together (SKILL.md must exist)."""
    issues: list[str] = []
    skill_md = (folder / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    files = {rel: p for rel, p in files_of(folder).items() if not rel.startswith(".")}
    texts = {rel: p.read_text(encoding="utf-8", errors="replace") for rel, p in files.items()
             if p.suffix.lower() in (".md", ".txt")}
    if any(m in skill_md for m in TEMPLATE_MARKERS):
        issues.append("template placeholders left in SKILL.md")
    # Files reached from SKILL.md: by path in text, by file name, or by `import` from a reached script.
    path_re = re.compile(r"(?<![\w/.-])((?:references|scripts|assets|templates|examples)/[\w./-]*\w)(?![\w*<{-])")
    code = {rel: p.read_text(encoding="utf-8", errors="replace") for rel, p in files.items()
            if p.suffix.lower() in CODE_SUFFIXES}
    docs = dict(texts)  # instructions only: SKILL.md and text references
    mentioned: set[str] = set()       # paths named in instructions
    from_docs: set[str] = set()       # files the instructions themselves reach (not only other scripts)
    reached = {"SKILL.md"}
    queue = ["SKILL.md"]
    while queue:
        src = queue.pop()
        t = texts.get(src) or ""
        new = {m.rstrip(".") for m in path_re.findall(t)}
        if src in docs:
            mentioned |= new
        for rel in files:
            if rel in reached:
                continue
            name, stem = Path(rel).name, Path(rel).stem
            if rel in new or any(rel.startswith(d + "/") for d in new if (folder / d).is_dir()) \
                    or re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", t) \
                    or (rel in code and re.search(rf"^\s*(?:from|import)\s+{re.escape(stem)}\b", t, re.M)):
                reached.add(rel)
                queue.append(rel)
                if src in docs:
                    from_docs.add(rel)
        texts.update({k: v for k, v in code.items() if k in reached and k not in texts})
    for m in sorted(mentioned):
        if m.startswith("references/agentspace/"):
            continue  # written later, on the user's own system
        if m not in files and not (folder / m).is_dir():
            issues.append(f"points to `{m}`, which doesn't exist")
    run_re = lambda rel: re.compile(rf"`[^`\n]*{re.escape(Path(rel).name)}[^`\n]*`|^\s*\$?\s*\S+\s+\S*{re.escape(rel)}", re.M)
    for rel in sorted(files):
        top = rel.split("/")[0]
        if rel == "SKILL.md" or top not in ("references", "scripts") or rel.startswith("references/agentspace/"):
            continue
        if Path(rel).name.startswith(("readonly-", "__init__")):
            continue
        if rel not in reached:
            issues.append(f"`{rel}` is never mentioned, so it is never read or run")
        elif top == "scripts" and rel in code and rel in from_docs and not any(
                run_re(rel).search(t) for t in docs.values()):
            issues.append(f"`{rel}` has no line saying how to run it (a command in backticks)")
    for rel, t in docs.items():
        if ABSOLUTE_PATH_RE.search(t):
            issues.append(f"`{rel}` has an absolute path into one machine")
            break
    return issues


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


CONFLICT_START = "<<<<<<< yours (installed)"
CONFLICT_MID = "======="
CONFLICT_END = ">>>>>>> new release"


def _changes(base: list[str], other: list[str]) -> list[tuple[int, int, list[str]]]:
    sm = difflib.SequenceMatcher(None, base, other, autojunk=False)
    return [(i1, i2, other[j1:j2]) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]


def _apply(base: list[str], start: int, end: int, changes: list[tuple[int, int, list[str]]]) -> list[str]:
    out, pos = [], start
    for i1, i2, rep in changes:
        out += base[pos:i1] + rep
        pos = i2
    return out + base[pos:end]


def merge3(base: list[str], mine: list[str], theirs: list[str]) -> tuple[list[str], bool]:
    """Line-based three-way merge. Returns (lines, had_conflict); conflicts get markers."""
    tagged = sorted([(c, 0) for c in _changes(base, mine)] + [(c, 1) for c in _changes(base, theirs)],
                    key=lambda t: (t[0][0], t[0][1]))
    out: list[str] = []
    pos, conflict, k = 0, False, 0
    while k < len(tagged):
        group = [tagged[k]]
        lo, hi = tagged[k][0][0], tagged[k][0][1]
        k += 1
        while k < len(tagged):
            (i1, i2, _), _side = tagged[k]
            if i1 < hi or (i1 == i2 == lo == hi):  # overlapping ranges, or two insertions at one point
                group.append(tagged[k])
                hi = max(hi, i2)
                k += 1
            else:
                break
        out += base[pos:lo]
        sides = {side for _, side in group}
        mine_ch = [c for c, side in group if side == 0]
        theirs_ch = [c for c, side in group if side == 1]
        a = _apply(base, lo, hi, mine_ch)
        b = _apply(base, lo, hi, theirs_ch)
        if len(sides) == 1 or a == b:
            out += a if sides == {0} else b
        else:
            conflict = True
            out += [CONFLICT_START + "\n"] + a + [CONFLICT_MID + "\n"] + b + [CONFLICT_END + "\n"]
        pos = hi
    return out + base[pos:], conflict


RELEASE_EXTS = (".md", ".py")
RELEASE_ROOT_FILES = {"SKILL.md", "README.md", "CHANGELOG.md", "VERSION.md", "LICENSE.md"}


def in_release(rel: str) -> bool:
    """Whether a path belongs in a release package: what a host needs to run the skill.

    Every file has an extension skill hosts accept (.md or .py). Development files (tests,
    evals, CI, release tooling) and private agentspace notes are not part of a release, so an
    upgrade from a package never treats them as removed."""
    parts = rel.split("/")
    if not rel.endswith(RELEASE_EXTS):
        return False
    if len(parts) == 1:
        return rel in RELEASE_ROOT_FILES
    if parts[0] == "references":
        return parts[1] != "agentspace" or rel == "references/agentspace/index.md"
    return parts[0] == "scripts" and len(parts) == 2 and rel.endswith(".py")


def _version_tuple(folder: Path) -> tuple[int, ...] | None:
    f = folder / "VERSION.md" if (folder / "VERSION.md").is_file() else folder / "VERSION"
    try:
        return tuple(int(x) for x in f.read_text(encoding="utf-8").strip().split("."))
    except (OSError, ValueError):
        return None


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class SkillCtl:
    def __init__(self, root: str | Path, store: str | Path | None = None) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise Refused(f"Skills folder not found: {self.root}")
        self.store = Path(store).expanduser().resolve() if store else default_store(self.root)
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
        return {st.get("original"), st.get("upstream"), (st.get("upgrade") or {}).get("upstream"), *self._digests(st)}

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
        st.pop("upgrade", None)  # a fresh draft replaces any pending upgrade
        st["draft_base"] = self._copy(installed, d)
        self._save_state(name, st)
        return d

    def new(self, name: str, source: str | Path | None = None, published: bool = False) -> Path:
        """Start a new skill created by the-one-skill: a draft in the store, installed by `apply`.

        `published`: the source is a skill exactly as its publisher released it. It is kept as the
        base for later `upgrade`s from the publisher, so local tweaks survive their releases."""
        if published and source is None:
            raise Refused("--published needs --from <folder>.")
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
        st: dict[str, Any] = {"name": name, "original": None, "created": True, "tuned": None, "history": []}
        if published:
            st["upgrade"] = {"upstream": self._store_version(name, d), "readonly": {}, "conflicts": []}
        self._save_state(name, st)
        return d

    def upgrade(self, name: str, source: str | Path, keep: Sequence[str] = (),
                allow_downgrade: bool = False) -> dict[str, Any]:
        """Draft a new release of a skill, merged three ways with the installed copy.

        Base = the release installed last (or the original). Returns a report; nothing is installed
        until `apply`, after the user's yes."""
        installed = self.installed(name)
        if installed.is_symlink() or not (installed / "SKILL.md").is_file():
            raise Refused(f"No installed skill `{name}` in {self.root} (links are not supported).")
        up = Path(source).expanduser().resolve()
        if not (up / "SKILL.md").is_file():
            raise Refused(f"{up} has no SKILL.md; point --from at the unpacked skill folder.")
        if frontmatter_name(up) != name:
            raise Refused(f"{up} is `{frontmatter_name(up)}`, not `{name}`; nothing was changed.")
        v_local, v_up = _version_tuple(installed), _version_tuple(up)
        if v_local and v_up and v_up < v_local and not allow_downgrade:
            raise Refused(f"{up} is older ({'.'.join(map(str, v_up))}) than the installed "
                          f"{'.'.join(map(str, v_local))}; pass --allow-downgrade if that is intended.")
        st = self.state(name)
        if st is None:
            self.sdir(name).mkdir(parents=True, exist_ok=True)
            st = {"name": name, "original": self._store_version(name, installed), "tuned": None, "history": []}
        base_digest = st.get("upstream") or st["original"]
        base_dir = self.version(name, base_digest) if base_digest else self.sdir(name) / "(none)"
        if base_digest and folder_hash(base_dir) != base_digest:
            raise Refused(f"The stored copy of the last release of `{name}` is damaged; nothing was changed.")
        up_digest = self._store_version(name, up)

        keep_prefixes = [k.strip("/") for k in keep]
        def kept(rel: str) -> bool:
            return any(rel == k or rel.startswith(k + "/") for k in keep_prefixes)

        B, L, U = files_of(base_dir), files_of(installed), files_of(up)
        d = self.sdir(name) / "draft"
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
        report: dict[str, Any] = {k: [] for k in ("from_release", "yours_kept", "merged", "conflicts",
                                                   "kept_paths", "readonly_updated", "removed")}
        readonly_ok: dict[str, str | None] = {}

        def put(rel: str, data: bytes) -> None:
            dst = d / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)

        for rel in sorted(set(B) | set(L) | set(U)):
            b = B[rel].read_bytes() if rel in B else None
            l = L[rel].read_bytes() if rel in L else None
            u = U[rel].read_bytes() if rel in U else None
            if kept(rel):
                if l is not None:
                    put(rel, l)
                    report["kept_paths"].append(rel)
                continue
            if not in_release(rel):  # not part of a release package (tests, CI, your own notes)
                if l is not None:
                    put(rel, l)
                continue
            if Path(rel).name.startswith(READONLY_PREFIX):
                if u == b or u == l:
                    result = l
                elif l == b:
                    result = u
                    readonly_ok[rel] = _sha(u) if u is not None else None
                    report["readonly_updated"].append(rel)
                else:
                    shutil.rmtree(d, ignore_errors=True)
                    raise Refused(f"`{rel}` was edited by hand and also changed in the release. Read-only "
                                  "files are reconciled by the user, by hand; nothing was changed.")
                if result is not None:
                    put(rel, result)
                continue
            if u == b or l == u:  # release didn't touch it, or both agree
                result, bucket = l, ("yours_kept" if l != b else None)
            elif l == b:  # only the release changed it
                result, bucket = u, ("from_release" if u is not None else "removed")
            elif u is None:  # release removed it, you changed it
                result, bucket = l, "yours_kept"
            elif l is None:  # you removed it, release changed it
                result, bucket = u, "conflicts"
            else:
                try:
                    lines, clash = merge3((b or b"").decode().splitlines(keepends=True),
                                          l.decode().splitlines(keepends=True),
                                          u.decode().splitlines(keepends=True))
                    result, bucket = "".join(lines).encode(), ("conflicts" if clash else "merged")
                except UnicodeDecodeError:
                    result, bucket = l, "conflicts"
            if result is not None:
                put(rel, result)
            if bucket:
                report[bucket].append(rel)

        st["draft_base"] = folder_hash(installed)
        st["upgrade"] = {"upstream": up_digest, "readonly": readonly_ok, "conflicts": report["conflicts"],
                         "from": ".".join(map(str, v_local)) if v_local else None,
                         "to": ".".join(map(str, v_up)) if v_up else None}
        self._save_state(name, st)
        report["draft"] = str(d)
        report["from_version"], report["to_version"] = st["upgrade"]["from"], st["upgrade"]["to"]
        return report

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
        upg = st.get("upgrade") or {}
        for rel in upg.get("conflicts", []):
            f = d / rel
            if f.is_file() and CONFLICT_START.encode() in f.read_bytes():
                raise Refused(f"`{rel}` still has conflict markers; resolve them in the draft first.")
        if self.installed(name).is_dir():
            allowed_ro = upg.get("readonly", {})
            locked = [
                rel for rel in readonly_changes(self.installed(name), d)
                if not (rel in allowed_ro and (
                    (allowed_ro[rel] is None and not (d / rel).exists())
                    or ((d / rel).is_file() and _sha((d / rel).read_bytes()) == allowed_ro[rel])))
            ]
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
        if upg:
            st["upstream"] = upg["upstream"]  # the base for the next upgrade
            st.pop("upgrade", None)
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

    def move_store(self, to: str | Path | None = None) -> Path:
        """Move the whole store (originals, versions, drafts, change sets) to a new folder."""
        dest = Path(to).expanduser().resolve() if to else None
        if dest is None:
            dest = (self.root.parent.parent / STORE_DIRNAME if self.root.name == "skills" and self.root.parent.name == ".claude"
                    else self.root.parent / STORE_DIRNAME)
        if dest == self.store:
            raise Refused(f"The store is already at {dest}.")
        if dest.exists():
            raise Refused(f"{dest} already exists; nothing was changed.")
        if dest == self.root or self.root in dest.parents:
            raise Refused("The store must be outside the skills folder.")
        if not self.store.is_dir():
            raise Refused(f"There is no store at {self.store} to move.")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(self.store), str(dest))
        self.store = dest
        return dest

    def guard_settings(self) -> dict[str, Any]:
        """Claude Code settings that block direct Edit/Write inside this skills folder."""
        script = Path(__file__).resolve().parent / "guard_skills.py"
        return {"hooks": {"PreToolUse": [{
            "matcher": "Edit|Write|MultiEdit|NotebookEdit",
            "hooks": [{"type": "command", "command": f'python3 "{script}" "{self.root}"'}],
        }]}}

    def overlap(self, candidate: str | Path | None = None, also: Sequence[str | Path] = ()) -> dict[str, Any]:
        """Overlap in triggers and procedure across the roster (plus read-only `also` folders).

        `candidate` is a folder, or the name of a skill with a draft in the store (from `draft` or
        `new`); only findings that involve it are returned."""
        cand = None
        if candidate is not None:
            path = Path(candidate).expanduser()
            if not (path / "SKILL.md").is_file() and NAME_RE.match(str(candidate)):
                path = self.sdir(str(candidate)) / "draft"
            cand = _overlap.load(path.resolve(), "candidate")
            if cand is None:
                raise Refused(f"No SKILL.md for `{candidate}`: pass a folder, or a skill with a draft (`draft`/`new`).")
            if path.name == "draft" and self.sdir(path.parent.name) == path.parent:
                cand.name = path.parent.name  # a draft is the skill it drafts, whatever its frontmatter says
        roots = [(self.root, "roster", False)] + [(Path(a).expanduser().resolve(), str(a), True) for a in also]
        return _overlap.analyze(_overlap.skills_for(roots, cand), cand.name if cand else None)

    # ----- usage -----
    @staticmethod
    def usage(transcripts: str | Path) -> dict[str, dict[str, Any]]:
        """How often, and when last, each skill was used in Claude Code session transcripts (*.jsonl).

        Counts Skill tool calls and /slash invocations. Reads of a SKILL.md don't count: a roster
        review reads every skill, which would make them all look used. Reads only skill names and
        timestamps; nothing else from the transcripts is kept or printed."""
        root = Path(transcripts).expanduser()
        if not root.is_dir():
            raise Refused(f"{root} is not a folder of transcripts.")
        seen: dict[str, dict[str, Any]] = {}
        slash = re.compile(r"<command-name>/?([a-z0-9:-]{1,128})</command-name>")

        def hit(name: str, when: str | None) -> None:
            name = name.split(":")[-1]
            if not NAME_RE.match(name):
                return
            r = seen.setdefault(name, {"uses": 0, "last": None})
            r["uses"] += 1
            if when and (r["last"] is None or when > r["last"]):
                r["last"] = when

        def walk(obj: Any, when: str | None) -> None:
            if isinstance(obj, dict):
                if obj.get("type") == "tool_use" and isinstance(obj.get("input"), dict):
                    inp = obj["input"]
                    if obj.get("name") == "Skill" and isinstance(inp.get("skill") or inp.get("command"), str):
                        hit(inp.get("skill") or inp.get("command"), when)
                for v in obj.values():
                    walk(v, when)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v, when)
            elif isinstance(obj, str) and "<command-name>" in obj:
                for m in slash.findall(obj):
                    hit(m, when)

        for f in sorted(root.rglob("*.jsonl")):
            with f.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    when = rec.get("timestamp") if isinstance(rec, dict) else None
                    walk(rec, when[:10] if isinstance(when, str) else None)
        return seen

    def roster(self, languages: Sequence[str] = ()) -> list[dict[str, Any]]:
        """Every skill in the skills folder with its state and any problems found.

        `languages`: the script languages this host can run (from the adapter). Scripts in any other
        language are flagged, because the host would fail to run them."""
        allowed = language_suffixes(languages) if languages else None
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
            if re.search(r"<[A-Za-z/][^<>]*>", desc):
                issues.append("description has angle-bracket tags, which Claude rejects")
            if re.search(r"anthropic|claude", p.name):
                issues.append("name contains a reserved word (anthropic, claude), which Claude rejects")
            if len(desc) > MAX_DESCRIPTION:
                issues.append(f"description has {len(desc)} characters (> {MAX_DESCRIPTION})")
            if (p / "SKILL.md").is_file():
                n = len((p / "SKILL.md").read_text(encoding="utf-8").splitlines())
                if n > MAX_SKILL_LINES:
                    issues.append(f"SKILL.md has {n} lines (> {MAX_SKILL_LINES})")
                issues.extend(structure_issues(p))
            if allowed is not None:
                for rel, f in sorted(files_of(p).items()):
                    suffix = Path(rel).suffix.lower() or shebang_suffix(f)
                    if suffix in CODE_SUFFIXES and suffix not in allowed:
                        issues.append(f"`{rel}` is in a language this host can't run (it runs: {', '.join(languages)})")
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
    ap.add_argument("--store", help=f"Store folder (default: <project>/{STORE_DIRNAME} for <project>/.claude/skills)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p = sub.add_parser("list")
    p.add_argument("--json", action="store_true", help="Machine-readable output")
    p.add_argument("--languages", help="Script languages this host runs, e.g. python,bash (flags any other)")
    rec = argparse.ArgumentParser(add_help=False)
    rec.add_argument("--set", dest="change_set", help="Record this step in a change set, e.g. merge-csv-skills")
    rec.add_argument("--note", help="Why (stored with the change set)")
    for cmd in ("draft", "diff", "history"):
        sub.add_parser(cmd).add_argument("skill")
    for cmd in ("apply", "retire", "restore"):
        sub.add_parser(cmd, parents=[rec]).add_argument("skill")
    sub.add_parser("sets")
    p = sub.add_parser("overlap", help="Find skills that overlap in triggers or procedure (read-only)")
    p.add_argument("--candidate", help="A draft (skill name) or folder to check against the roster")
    p.add_argument("--also", action="append", default=[], help="Extra read-only skills folder (repeatable)")
    p.add_argument("--json", action="store_true", help="Machine-readable output")
    p = sub.add_parser("move-store", help="Move the store (e.g. from the old .claude/the-one-skill-store to .tos-store)")
    p.add_argument("--to", help=f"Destination (default: <project>/{STORE_DIRNAME})")
    sub.add_parser("guard", help="Print the Claude Code hook setting that blocks direct edits to skills")
    p = sub.add_parser("undo-set")
    p.add_argument("name")
    p.add_argument("--apply", action="store_true", help="Run the reverse steps (default: only show them)")
    p = sub.add_parser("upgrade", help="Draft a new release merged with your local changes")
    p.add_argument("skill")
    p.add_argument("--from", dest="source", required=True, help="Unpacked folder of the new release")
    p.add_argument("--keep", action="append", default=[], help="Path to keep exactly as installed (repeatable)")
    p.add_argument("--allow-downgrade", action="store_true")
    p = sub.add_parser("new")
    p.add_argument("skill")
    p.add_argument("--from", dest="source", help="Folder with the new skill's files (default: a SKILL.md template)")
    p.add_argument("--published", action="store_true",
                   help="The folder is the skill exactly as its publisher released it (base for later `upgrade`s)")
    p = sub.add_parser("usage", help="How often each skill was used, from Claude Code transcripts (read-only)")
    p.add_argument("--transcripts", default="~/.claude/projects", help="Folder of *.jsonl transcripts")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("use", parents=[rec])
    p.add_argument("skill")
    p.add_argument("version", help="original, previous, tuned, or a version id from `history`")
    a = ap.parse_args(argv)
    try:
        ctl = SkillCtl(a.root, a.store)
        if getattr(a, "change_set", None):
            ctl.begin_set(a.change_set, a.note)
        if a.cmd != "move-store" and ctl.store.name == LEGACY_STORE_DIRNAME:
            print(f"Note: using the store at its old place, {ctl.store}. `move-store` moves it to "
                  f"<project>/{STORE_DIRNAME}, outside .claude/.", file=sys.stderr)
        if a.cmd == "status":
            rows = ctl.status()
            print("\n".join(f"{n:32} {s}" for n, s in rows) if rows else "No skills changed by the-one-skill yet.")
        elif a.cmd == "list":
            rows = ctl.roster(a.languages.split(",") if a.languages else ())
            if a.json:
                print(json.dumps(rows, indent=2))
            elif not rows:
                print("No skills found.")
            for r in rows if not a.json else []:
                desc = r["description"] if len(r["description"]) <= 70 else r["description"][:67] + "..."
                print(f"{r['name']:32} {r['state']:10} {desc}")
                for issue in r["issues"]:
                    print(f"{'':32} ! {issue}")
        elif a.cmd == "overlap":
            r = ctl.overlap(a.candidate, a.also)
            print(json.dumps(r, indent=2) if a.json else _overlap.report(r))
        elif a.cmd == "move-store":
            old = ctl.store
            print(f"Store moved from {old} to {ctl.move_store(a.to)}. Pass --store if you use a non-default place.")
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
        elif a.cmd == "upgrade":
            r = ctl.upgrade(a.skill, a.source, a.keep, a.allow_downgrade)
            print(f"Upgrade draft: {r['draft']}  ({r['from_version'] or '?'} -> {r['to_version'] or '?'})")
            labels = {"from_release": "from the release", "yours_kept": "your changes kept",
                      "merged": "merged (both changed, no clash)", "conflicts": "CONFLICTS (resolve in the draft)",
                      "kept_paths": "kept as installed", "readonly_updated": "read-only, updated to the release",
                      "removed": "removed by the release"}
            for key, label in labels.items():
                if r[key]:
                    print(f"{label}:")
                    for rel in r[key]:
                        print(f"  {rel}")
            print("Nothing is installed yet. Resolve any conflicts, then `apply` after the user's yes.")
        elif a.cmd == "new":
            print(f"New skill draft: {ctl.new(a.skill, a.source, a.published)}\n"
                  "Write its files there, show `diff`, and `apply` after approval.")
        elif a.cmd == "usage":
            used = ctl.usage(a.transcripts)
            installed = {r["name"] for r in ctl.roster()}
            rows = {n: used.get(n, {"uses": 0, "last": None}) for n in sorted(installed | set(used))}
            if a.json:
                print(json.dumps({n: {**r, "installed": n in installed} for n, r in rows.items()}, indent=2))
            for n, r in rows.items() if not a.json else []:
                if n in installed:  # the rest are other folders' skills or built-in commands
                    print(f"{n:32} {r['uses']:5} use(s)  last {r['last'] or 'never'}")
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
