#!/usr/bin/env python3
"""Unified diff & PR summary generator against upstream baseline.

Pure Python 3 standard library. Compares <upstream_dir> and <local_dir>,
scans added/modified lines for accidental personal data or secret leaks,
writes a standard unified diff to <output_patch_path>, and prints a Markdown
Pull Request summary.

Usage:
    python3 scripts/export_diff.py <upstream_dir> <local_dir> <output_patch_path>
"""

from __future__ import annotations

import dataclasses
import difflib
import re
import sys
from pathlib import Path

IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", "artifacts"}
IGNORED_FILES = {".DS_Store", "Thumbs.db"}
IGNORED_SUFFIXES = (".pyc", ".pyo", ".bak.md", ".patch")

SANITIZATION_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "Private email address",
        re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.com|users\.noreply\.github\.com)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "Local user home directory path",
        re.compile(r"(/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+|C:\\Users\\[A-Za-z0-9._-]+)"),
    ),
    (
        "API key or secret token",
        re.compile(r"\b(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,})\b"),
    ),
    (
        "Gemini Memory private state dump",
        re.compile(r"(?i)MEMORY_PRIVATE_DUMP|GEMINI_MEMORY_USER_ID"),
    ),
]


@dataclasses.dataclass
class DiffExportReport:
    patch_text: str
    added_files: list[str]
    modified_files: list[str]
    deleted_files: list[str]
    lines_added: int
    lines_removed: int
    sanitization_warnings: list[str]
    summary_markdown: str


def _should_skip(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    for part in rel_parts[:-1]:
        if part in IGNORED_DIRS:
            return True
    if path.name in IGNORED_FILES or path.name.endswith(IGNORED_SUFFIXES):
        return True
    return False


def _collect_relative_files(root: Path) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for p in root.rglob("*"):
        if p.is_file() and not _should_skip(p, root):
            rel = p.relative_to(root).as_posix()
            mapping[rel] = p
    return mapping


def _read_normalized_lines(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.splitlines(keepends=True)


def scan_added_lines_for_leaks(rel_path: str, diff_lines: list[str]) -> list[str]:
    warnings: list[str] = []
    for line in diff_lines:
        if not line.startswith("+") or line.startswith("+++"):
            continue
        added_content = line[1:]
        for label, pattern in SANITIZATION_RULES:
            match = pattern.search(added_content)
            if match:
                warnings.append(
                    f"{rel_path}: potential {label} detected ({match.group(0)!r})"
                )
    return warnings


def generate_diff_export(
    upstream_dir: str | Path,
    local_dir: str | Path,
    output_patch_path: str | Path | None = None,
) -> DiffExportReport:
    up_root = Path(upstream_dir).resolve()
    loc_root = Path(local_dir).resolve()

    if not up_root.is_dir():
        raise FileNotFoundError(f"Upstream directory not found: {upstream_dir}")
    if not loc_root.is_dir():
        raise FileNotFoundError(f"Local directory not found: {local_dir}")

    up_files = _collect_relative_files(up_root)
    loc_files = _collect_relative_files(loc_root)
    all_rel_paths = sorted(set(up_files.keys()) | set(loc_files.keys()))

    added_files: list[str] = []
    modified_files: list[str] = []
    deleted_files: list[str] = []
    lines_added = 0
    lines_removed = 0
    all_diff_chunks: list[str] = []
    sanitization_warnings: list[str] = []

    for rel in all_rel_paths:
        up_path = up_files.get(rel)
        loc_path = loc_files.get(rel)

        up_lines = _read_normalized_lines(up_path)
        loc_lines = _read_normalized_lines(loc_path)

        if up_lines == loc_lines:
            continue

        if up_path is None:
            added_files.append(rel)
            from_file = "/dev/null"
            to_file = f"b/{rel}"
        elif loc_path is None:
            deleted_files.append(rel)
            from_file = f"a/{rel}"
            to_file = "/dev/null"
        else:
            modified_files.append(rel)
            from_file = f"a/{rel}"
            to_file = f"b/{rel}"

        diff = list(
            difflib.unified_diff(
                up_lines,
                loc_lines,
                fromfile=from_file,
                tofile=to_file,
                lineterm="\n",
            )
        )
        if not diff:
            continue

        for dline in diff:
            if dline.startswith("+") and not dline.startswith("+++"):
                lines_added += 1
            elif dline.startswith("-") and not dline.startswith("---"):
                lines_removed += 1

        sanitization_warnings.extend(scan_added_lines_for_leaks(rel, diff))
        header = f"diff --git a/{rel} b/{rel}\n"
        all_diff_chunks.append(header + "".join(diff))

    patch_text = "".join(all_diff_chunks)

    if output_patch_path is not None:
        out_path = Path(output_patch_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(patch_text, encoding="utf-8")

    summary_lines = [
        "## Pull Request Diff Summary (`the-one-skill`)",
        "",
        f"- **Files Added:** {len(added_files)}",
        f"- **Files Modified:** {len(modified_files)}",
        f"- **Files Deleted:** {len(deleted_files)}",
        f"- **Line Delta:** `+{lines_added}` / `-{lines_removed}`",
    ]
    if added_files or modified_files or deleted_files:
        summary_lines.append("")
        summary_lines.append("### Changed Files")
        for f in added_files:
            summary_lines.append(f"- `[ADDED]` `{f}`")
        for f in modified_files:
            summary_lines.append(f"- `[MODIFIED]` `{f}`")
        for f in deleted_files:
            summary_lines.append(f"- `[DELETED]` `{f}`")

    if sanitization_warnings:
        summary_lines.append("")
        summary_lines.append("### Sanitization Warnings (Action Required Before PR)")
        for w in sanitization_warnings:
            summary_lines.append(f"- WARNING: {w}")

    summary_markdown = "\n".join(summary_lines) + "\n"

    return DiffExportReport(
        patch_text=patch_text,
        added_files=added_files,
        modified_files=modified_files,
        deleted_files=deleted_files,
        lines_added=lines_added,
        lines_removed=lines_removed,
        sanitization_warnings=sanitization_warnings,
        summary_markdown=summary_markdown,
    )


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 3:
        print(
            "Usage: python3 scripts/export_diff.py <upstream_dir> <local_dir> <output_patch_path>",
            file=sys.stderr,
        )
        return 2

    upstream_dir, local_dir, output_patch = args
    try:
        report = generate_diff_export(upstream_dir, local_dir, output_patch)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(report.summary_markdown)
    if report.sanitization_warnings:
        print(
            "FAIL: Sanitization check flagged potential personal data or secrets in the diff.",
            file=sys.stderr,
        )
        return 1

    print(f"PASS: Wrote clean unified diff to {output_patch}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
