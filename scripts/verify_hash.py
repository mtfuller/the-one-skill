#!/usr/bin/env python3
"""Deterministic, cross-platform SHA-256 verifier for staged Agent Skills.

Pure Python 3 standard library. Computes a canonical manifest hash across
all files in a directory by sorting POSIX relative paths, ignoring OS/cache
noise (.DS_Store, __pycache__, .git, *.pyc), and normalizing CRLF -> LF on
UTF-8 text files so hashes match across macOS, Linux, Windows, and Gemini Web.

Usage:
    python3 scripts/verify_hash.py <staged_dir> <expected_sha256>
    python3 scripts/verify_hash.py --compute <staged_dir>
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Iterable

IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
IGNORED_FILES = {".DS_Store", "Thumbs.db"}
IGNORED_SUFFIXES = (".pyc", ".pyo", ".bak.md")
SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")


def _should_ignore(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    for part in rel_parts[:-1]:
        if part in IGNORED_DIRS:
            return True
    name = path.name
    if name in IGNORED_FILES or name.endswith(IGNORED_SUFFIXES):
        return True
    return False


def _iter_canonical_files(root: Path) -> Iterable[Path]:
    files = [
        p for p in root.rglob("*") if p.is_file() and not _should_ignore(p, root)
    ]
    files.sort(key=lambda p: p.relative_to(root).as_posix())
    return files


def _normalize_bytes(raw: bytes) -> bytes:
    """Normalize CRLF/CR line endings to LF for valid UTF-8 text files."""
    if b"\x00" in raw:
        return raw
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.encode("utf-8")


def compute_canonical_hash(target: str | Path) -> str:
    """Return the canonical 64-char hex SHA-256 digest for a skill directory or file."""
    root = Path(target).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Target path does not exist: {target}")

    manifest = hashlib.sha256()

    if root.is_file():
        norm = _normalize_bytes(root.read_bytes())
        file_digest = hashlib.sha256(norm).hexdigest()
        manifest.update(f"{root.name}\0{len(norm)}\0{file_digest}\n".encode("utf-8"))
        return manifest.hexdigest()

    files = list(_iter_canonical_files(root))
    if not files:
        raise ValueError(f"No verifiable files found in directory: {target}")

    for file_path in files:
        rel_posix = file_path.relative_to(root).as_posix()
        norm = _normalize_bytes(file_path.read_bytes())
        file_digest = hashlib.sha256(norm).hexdigest()
        entry = f"{rel_posix}\0{len(norm)}\0{file_digest}\n".encode("utf-8")
        manifest.update(entry)

    return manifest.hexdigest()


def verify_directory_hash(target: str | Path, expected_sha256: str) -> tuple[bool, str]:
    """Verify target against expected_sha256. Returns (passed, actual_sha256_or_error)."""
    cleaned_expected = expected_sha256.strip().lower()
    if not SHA256_RE.match(cleaned_expected):
        return False, f"Invalid expected SHA-256 format: {expected_sha256!r}"

    try:
        actual = compute_canonical_hash(target)
    except Exception as exc:
        return False, str(exc)

    return (actual == cleaned_expected), actual


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if len(args) == 2 and args[0] == "--compute":
        try:
            digest = compute_canonical_hash(args[1])
            print(digest)
            return 0
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if len(args) != 2:
        print(
            "Usage:\n"
            "  python3 scripts/verify_hash.py <staged_dir> <expected_sha256>\n"
            "  python3 scripts/verify_hash.py --compute <staged_dir>",
            file=sys.stderr,
        )
        return 2

    target_dir, expected = args[0], args[1]
    passed, actual_or_err = verify_directory_hash(target_dir, expected)
    if passed:
        print(f"PASS: {actual_or_err}")
        return 0
    else:
        print(f"FAIL: expected {expected.strip().lower()} got {actual_or_err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
