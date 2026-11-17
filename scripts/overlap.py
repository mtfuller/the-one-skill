#!/usr/bin/env python3
"""Find skills that overlap, in what triggers them and in what they do (pure Python 3 standard library).

Two skills are orthogonal when they neither answer the same requests nor carry the same procedure.
This module measures both, so the-one-skill can flag overlap before it creates, installs, or
rewrites a skill, and during a roster review:

* **Triggers:** TF-IDF cosine between descriptions, ignoring "Do not use ..." sentences (they name
  the neighbours a skill hands off to, which is a boundary, not an overlap).
* **Procedure:** how much of the smaller skill's instructions (SKILL.md body plus its text
  references) also appears in the other one, by shared word shingles, so reworded copies still count.
* **Shared blocks:** instruction lines repeated across two or more skills, grouped by which skills
  carry them. A block repeated in three skills is a policy that should have one owner.
* **Boundaries:** whether either description names the other skill in a "Do not use ..." sentence
  (for example "Do not use for slides in general (use pptx).").
* **Shadowing:** the same skill name in two scanned folders.

It only reads. Folders passed with `also` are scanned for comparison but treated as read-only
(personal, plugin, or built-in skills).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

TRIGGER_FLAG = 0.30     # description similarity at which two skills compete for the same requests
PROCEDURE_FLAG = 0.30   # share of the smaller skill's instructions found in the other
LINE_SHARED = 0.6       # share of a line's shingles found in another skill for the line to count as shared
MIN_LINE_WORDS = 6      # shorter lines are too generic to compare
MIN_BLOCK_WORDS = 20    # smallest repeated block worth reporting
SHINGLE = 4
TEXT_SUFFIXES = {".md", ".txt"}
SELF = "the-one-skill"

STOP = set("""
a about above after again against all also am an and any are as at be because been before being below
between both but by can could did do does doing don done down during each either etc even every few
for from further had has have having he her here hers him his how i if in into is it its itself just
me more most my no nor not now of off on once only or other our ours out over own same she should so
some such than that the their theirs them then there these they this those through to too under until
up upon very via was we were what when where whether which while who whom why will with would you
your yours use used uses using user users ask asks asked want wants wanted need needs skill skills
request requests task tasks help make makes like e g eg ie one may must always never every new
""".split())


def words(text: str) -> list[str]:
    """Content words, lower case, with plurals folded to the singular."""
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in STOP or len(w) < 2:
            continue
        if len(w) > 4 and re.search(r"(sh|ch|[sxz])es$", w):
            w = w[:-2]
        elif len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
            w = w[:-1]
        out.append(w)
    return out


def _shingles(tokens: Sequence[str]) -> set[tuple[str, ...]]:
    return {tuple(tokens[i:i + SHINGLE]) for i in range(len(tokens) - SHINGLE + 1)}


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.S)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    key = None
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if kv:
            key = kv.group(1)
            fm[key] = kv.group(2).strip().strip("\"'")
        elif key and line.startswith((" ", "\t")):
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return fm, text[m.end():]


def _sentences(description: str) -> list[tuple[str, bool]]:
    """(sentence, is_boundary) pairs; boundary sentences say when NOT to use the skill."""
    parts = re.split(r"(?<=[.!?;])\s+", description)
    return [(p, bool(re.match(r"^\s*(do not|don't|not for|never)\b", p, re.I))) for p in parts]


def trigger_text(description: str) -> str:
    """The part of a description that says when to use the skill: drops "Do not use ..." sentences."""
    return " ".join(p for p, boundary in _sentences(description) if not boundary)


def boundary_text(description: str) -> str:
    """The "Do not use ..." sentences of a description."""
    return " ".join(p for p, boundary in _sentences(description) if boundary)


@dataclass
class Skill:
    name: str
    folder: Path
    origin: str                 # "roster", "candidate", or the --also folder it came from
    description: str = ""
    lines: list[str] = field(default_factory=list)   # instruction lines long enough to compare
    readonly: bool = False

    def __post_init__(self) -> None:
        self.line_shingles = [_shingles(words(l)) for l in self.lines]
        self.shingles: set[tuple[str, ...]] = set().union(*self.line_shingles) if self.lines else set()


def load(folder: Path, origin: str, readonly: bool = False) -> Skill | None:
    """Read one skill folder. Returns None when it has no SKILL.md."""
    md = folder / "SKILL.md"
    if not md.is_file():
        return None
    fm, body = _split_frontmatter(md.read_text(encoding="utf-8", errors="replace"))
    texts = [body]
    for p in sorted(folder.rglob("*")):
        if p.is_file() and p != md and p.suffix.lower() in TEXT_SUFFIXES and ".git" not in p.parts \
                and not p.name.startswith("readonly-"):
            texts.append(p.read_text(encoding="utf-8", errors="replace"))
    lines = []
    for t in texts:
        for raw in t.splitlines():
            line = raw.strip()
            if line.startswith(("#", "|", "```")) or len(words(line)) < MIN_LINE_WORDS:
                continue
            lines.append(line)
    return Skill(fm.get("name") or folder.name, folder, origin, fm.get("description", ""), lines, readonly)


def scan(folder: Path, origin: str, readonly: bool = False) -> list[Skill]:
    if not folder.is_dir():
        return []
    out = []
    for p in sorted(folder.iterdir()):
        if p.is_dir() and not p.name.startswith("."):
            s = load(p, origin, readonly)
            if s:
                out.append(s)
    return out


def _tfidf(docs: list[list[str]]) -> list[dict[str, float]]:
    n = len(docs)
    df = Counter(w for d in docs for w in set(d))
    vecs = []
    for d in docs:
        tf = Counter(d)
        v = {w: (1 + math.log(c)) * (math.log((n + 1) / (df[w] + 1)) + 1) for w, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({w: x / norm for w, x in v.items()})
    return vecs


def _cos(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(w, 0.0) for w, x in a.items())


def _names(text: str, name: str) -> bool:
    return re.search(rf"(?<![a-z0-9-]){re.escape(name)}(?![a-z0-9-])", text, re.I) is not None


def analyze(skills: list[Skill], focus: str | None = None) -> dict[str, Any]:
    """Compare every pair (or only pairs with `focus`) and group repeated instruction blocks."""
    skills = [s for s in skills if s.name != SELF or s.name == focus]
    trig = _tfidf([words(trigger_text(s.description)) for s in skills])
    pairs = []
    for i, a in enumerate(skills):
        for j in range(i + 1, len(skills)):
            b = skills[j]
            if focus and focus not in (a.name, b.name):
                continue
            if a.readonly and b.readonly:
                continue  # neither can be changed; nothing to propose
            t = _cos(trig[i], trig[j])
            small = min(len(a.shingles), len(b.shingles))
            p = len(a.shingles & b.shingles) / small if small else 0.0
            if t < TRIGGER_FLAG and p < PROCEDURE_FLAG:
                continue
            boundary = _names(boundary_text(a.description), b.name) or _names(boundary_text(b.description), a.name)
            if t >= TRIGGER_FLAG and p >= PROCEDURE_FLAG:
                verdict = "same job twice: merge, or keep one and retire the other"
            elif p >= PROCEDURE_FLAG:
                verdict = "same procedure, different triggers: give the procedure one owner"
            elif boundary:
                verdict = "triggers overlap, boundary stated: fine as long as the boundary is right"
            else:
                verdict = "triggers overlap: add a 'Do not use when ... (use <other>)' boundary"
            ro = [s.name for s in (a, b) if s.readonly]
            if ro:
                verdict += f" (never change {', '.join(ro)}: the other skill defers to it)"
            pairs.append({"a": a.name, "b": b.name, "triggers": round(t, 2), "procedure": round(p, 2),
                          "boundary_stated": boundary, "readonly": ro, "verdict": verdict})
    pairs.sort(key=lambda r: -max(r["triggers"], r["procedure"]))

    # Shared blocks: for each line, which other skills carry (most of) it.
    groups: dict[tuple[str, ...], list[str]] = {}
    for a in skills:
        for line, sh in zip(a.lines, a.line_shingles):
            if not sh:
                continue
            owners = {a.name} | {b.name for b in skills if b is not a
                                 and len(sh & b.shingles) / len(sh) >= LINE_SHARED}
            key = tuple(sorted(owners))
            if len(key) < 2 or key[0] != a.name or (focus and focus not in key):
                continue  # recorded once, from the first owner alphabetically
            groups.setdefault(key, []).append(line)
    ro_names = {s.name for s in skills if s.readonly}
    blocks = []
    for key, lines in groups.items():
        n_words = sum(len(words(l)) for l in lines)
        if n_words < MIN_BLOCK_WORDS or all(k in ro_names for k in key):
            continue
        blocks.append({"skills": list(key), "lines": len(lines), "words": n_words, "sample": lines[:3],
                       "readonly": sorted(k for k in key if k in ro_names)})
    blocks.sort(key=lambda b: (-len(b["skills"]), -b["words"]))

    seen: dict[str, list[str]] = {}
    for s in skills:
        seen.setdefault(s.name, []).append(f"{s.origin}:{s.folder}")
    shadowed = {n: where for n, where in seen.items() if len(where) > 1}
    return {"pairs": pairs, "shared_blocks": blocks, "shadowed": shadowed}


def report(result: dict[str, Any]) -> str:
    out: list[str] = []
    for n, where in result["shadowed"].items():
        out.append(f"SAME NAME  {n} is in more than one place: " + "; ".join(where))
    for r in result["pairs"]:
        out.append(f"PAIR       {r['a']} <> {r['b']}  triggers {r['triggers']:.2f}  procedure {r['procedure']:.2f}"
                   f"{'  boundary stated' if r['boundary_stated'] else ''}")
        out.append(f"           -> {r['verdict']}")
    for b in result["shared_blocks"]:
        n = len(b["skills"])
        what = "policy repeated in" if n >= 3 else "block repeated in"
        out.append(f"SHARED     {what} {n} skills ({', '.join(b['skills'])}): {b['lines']} line(s), {b['words']} words")
        for line in b["sample"]:
            out.append(f"           | {line[:100]}")
        if b["readonly"]:
            out.append(f"           -> {', '.join(b['readonly'])} is protected: the others should defer to it")
        else:
            out.append("           -> give it one owner: merge these skills, or move it into one skill the others defer to")
    return "\n".join(out) if out else "No overlap found: triggers and procedures are distinct."


def skills_for(roots: Iterable[tuple[Path, str, bool]], candidate: Skill | None = None) -> list[Skill]:
    """Scan (folder, origin, readonly) roots; a candidate replaces the roster skill of the same name."""
    out: list[Skill] = []
    for folder, origin, ro in roots:
        out.extend(scan(folder, origin, ro))
    if candidate:
        out = [s for s in out if not (s.name == candidate.name and s.origin == "roster")] + [candidate]
    return out
