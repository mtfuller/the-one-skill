#!/usr/bin/env python3
"""Deterministic unit & round-trip lifecycle test suite for the-one-skill.

Pure Python 3 standard library (unittest). Tests:
  1. verify_hash.py: deterministic pass, tamper rejection, CRLF normalization,
     and ignored OS noise (.DS_Store, __pycache__).
  2. Delimiter block mounting, idempotency, and clean unmounting round-trip
     (mount -> strip restores original content byte-for-byte).
  3. Consent lock enforcement (the-one-skill:ignore prevents mounting or edits).
  4. Snapshot & revert round-trip restoration.
  5. export_diff.py: unified diff generation, file summary, and PII leak detection.
  6. lint_skills.py: 800-token ceiling, frontmatter, trigger overlap detection,
     and security-policy.json trap blocking.
  7. registry.json integrity: verifies every entry's SHA-256 and pinned commit format.

Usage:
    python3 scripts/test_lifecycle.py
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import export_diff  # noqa: E402
import lint_skills  # noqa: E402
import verify_hash  # noqa: E402

OPT_IN_MARKER = "<!-- the-one-skill:opt-in -->"
IGNORE_MARKER = "<!-- the-one-skill:ignore -->"
BLOCK_START = "<!-- the-one-skill:start -->"
BLOCK_END = "<!-- the-one-skill:end -->"


class IgnoredSkillLockError(PermissionError):
    """Raised when attempting to mount or modify a skill marked with ignore."""


def mount_integration_block(skill_md_path: Path, integration_block_path: Path | None = None) -> str:
    """Mount templates/integration-block.md onto a skill unless locked with ignore."""
    content = skill_md_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if IGNORE_MARKER in content:
        raise IgnoredSkillLockError(
            f"Refusing to modify {skill_md_path}: locked with {IGNORE_MARKER}"
        )

    # Idempotent if already mounted
    if OPT_IN_MARKER in content and BLOCK_START in content and BLOCK_END in content:
        return content

    tpl_path = integration_block_path or (REPO_ROOT / "templates" / "integration-block.md")
    block = tpl_path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()

    stripped_body = content.rstrip("\n")
    mounted = f"{stripped_body}\n\n{block}\n"

    tokens = lint_skills.estimate_tokens(mounted)
    if tokens > lint_skills.MAX_SKILL_TOKENS:
        raise ValueError(
            f"Mounting integration block would exceed {lint_skills.MAX_SKILL_TOKENS} token cap ({tokens} tokens)."
        )

    skill_md_path.write_text(mounted, encoding="utf-8")
    return mounted


def strip_integration_block(skill_md_path: Path) -> str:
    """Strip the-one-skill markers and delimited block, restoring vanilla SKILL.md."""
    content = skill_md_path.read_text(encoding="utf-8").replace("\r\n", "\n")

    # Remove opt-in / ignore markers and the start..end block
    content = re.sub(
        r"\n*<!-- the-one-skill:opt-in -->\s*<!-- the-one-skill:start -->.*?<!-- the-one-skill:end -->\s*",
        "\n",
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r"\n*<!-- the-one-skill:start -->.*?<!-- the-one-skill:end -->\s*",
        "\n",
        content,
        flags=re.DOTALL,
    )
    content = re.sub(r"\n*<!-- the-one-skill:(?:opt-in|ignore) -->\s*", "\n", content)
    cleaned = content.rstrip("\n") + "\n"
    skill_md_path.write_text(cleaned, encoding="utf-8")
    return cleaned


def set_ignore_lock(skill_md_path: Path) -> str:
    """Strip any active integration block and append the-one-skill:ignore lock marker."""
    vanilla = strip_integration_block(skill_md_path).rstrip("\n")
    locked = f"{vanilla}\n\n{IGNORE_MARKER}\n"
    skill_md_path.write_text(locked, encoding="utf-8")
    return locked


def save_snapshot(skill_md_path: Path, snapshot_dir: Path, skill_name: str) -> Path:
    """Save a pre-patch snapshot of skill_md_path."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snap_path = snapshot_dir / f"{skill_name}.{ts}.bak.md"
    shutil.copyfile(skill_md_path, snap_path)
    return snap_path


def revert_from_snapshot(skill_md_path: Path, snapshot_path: Path) -> str:
    """Restore skill_md_path from snapshot_path."""
    if not snapshot_path.is_file():
        raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")
    shutil.copyfile(snapshot_path, skill_md_path)
    return skill_md_path.read_text(encoding="utf-8")


VANILLA_SKILL_SAMPLE = """---
name: sample-formatter
description: Format markdown tables and align columns deterministically.
---

# Sample Formatter

 Align markdown table columns cleanly without modifying prose.

## Use when

- The user wants to align or format markdown tables in documentation files.

## Do not use when

- The user is editing CSV files or JSON schemas.

## Workflow

1. Parse the markdown table rows.
2. Pad cells to uniform width and emit the aligned table.
"""


class TestTheOneSkillLifecycle(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="the-one-skill-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_verify_hash_pass_and_tamper_rejection(self) -> None:
        skill_dir = self.tmp_dir / "candidate-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(VANILLA_SKILL_SAMPLE, encoding="utf-8")

        digest = verify_hash.compute_canonical_hash(skill_dir)
        self.assertEqual(len(digest), 64)

        passed, actual = verify_hash.verify_directory_hash(skill_dir, digest)
        self.assertTrue(passed)
        self.assertEqual(actual, digest)

        # OS noise files (.DS_Store, __pycache__) must not change the canonical hash
        (skill_dir / ".DS_Store").write_bytes(b"\x00\x01\x02")
        pycache = skill_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "helper.cpython-311.pyc").write_bytes(b"\xde\xad\xbe\xef")
        self.assertEqual(verify_hash.compute_canonical_hash(skill_dir), digest)

        # CRLF vs LF line endings must produce the exact same canonical hash
        crlf_text = VANILLA_SKILL_SAMPLE.replace("\n", "\r\n")
        skill_file.write_bytes(crlf_text.encode("utf-8"))
        self.assertEqual(verify_hash.compute_canonical_hash(skill_dir), digest)

        # Tampering with a single character must fail verification
        skill_file.write_text(VANILLA_SKILL_SAMPLE + "\n<!-- tampered -->\n", encoding="utf-8")
        passed_after_tamper, tampered_hash = verify_hash.verify_directory_hash(skill_dir, digest)
        self.assertFalse(passed_after_tamper)
        self.assertNotEqual(tampered_hash, digest)

    def test_mount_and_strip_round_trip_restores_exact_bytes(self) -> None:
        skill_file = self.tmp_dir / "SKILL.md"
        skill_file.write_text(VANILLA_SKILL_SAMPLE, encoding="utf-8")

        mounted = mount_integration_block(skill_file)
        self.assertIn(OPT_IN_MARKER, mounted)
        self.assertIn(BLOCK_START, mounted)
        self.assertIn(BLOCK_END, mounted)

        # Mounting a second time is idempotent
        mounted_again = mount_integration_block(skill_file)
        self.assertEqual(mounted, mounted_again)

        # Stripping restores exact original content byte-for-byte
        restored = strip_integration_block(skill_file)
        self.assertEqual(restored, VANILLA_SKILL_SAMPLE)

    def test_ignore_marker_enforces_lock(self) -> None:
        skill_file = self.tmp_dir / "SKILL.md"
        skill_file.write_text(VANILLA_SKILL_SAMPLE, encoding="utf-8")

        locked = set_ignore_lock(skill_file)
        self.assertIn(IGNORE_MARKER, locked)
        self.assertNotIn(OPT_IN_MARKER, locked)
        self.assertEqual(lint_skills.detect_consent_state(locked), "ignore")

        with self.assertRaises(IgnoredSkillLockError):
            mount_integration_block(skill_file)

    def test_snapshot_and_revert_round_trip(self) -> None:
        skill_file = self.tmp_dir / "SKILL.md"
        snap_dir = self.tmp_dir / "artifacts" / "snapshots"
        skill_file.write_text(VANILLA_SKILL_SAMPLE, encoding="utf-8")

        snap_path = save_snapshot(skill_file, snap_dir, "sample-formatter")
        self.assertTrue(snap_path.is_file())

        # Mutate the skill via mount + edit
        mount_integration_block(skill_file)
        skill_file.write_text(
            skill_file.read_text(encoding="utf-8") + "\n<!-- extra edit -->\n",
            encoding="utf-8",
        )
        self.assertNotEqual(skill_file.read_text(encoding="utf-8"), VANILLA_SKILL_SAMPLE)

        # Revert restores exact snapshot
        reverted = revert_from_snapshot(skill_file, snap_path)
        self.assertEqual(reverted, VANILLA_SKILL_SAMPLE)

    def test_export_diff_and_sanitization_guard(self) -> None:
        upstream = self.tmp_dir / "upstream"
        local = self.tmp_dir / "local"
        upstream.mkdir()
        local.mkdir()

        (upstream / "SKILL.md").write_text(VANILLA_SKILL_SAMPLE, encoding="utf-8")
        updated_skill = VANILLA_SKILL_SAMPLE.replace(
            "2. Pad cells to uniform width and emit the aligned table.",
            "2. Pad cells to uniform width, preserve alignment colons, and emit the table.",
        )
        (local / "SKILL.md").write_text(updated_skill, encoding="utf-8")
        (local / "references").mkdir()
        (local / "references" / "edge-cases.md").write_text(
            "# Table Edge Cases\n\nEscape pipe characters inside inline code spans.\n",
            encoding="utf-8",
        )

        patch_path = self.tmp_dir / "artifacts" / "changes.patch"
        report = export_diff.generate_diff_export(upstream, local, patch_path)

        self.assertTrue(patch_path.is_file())
        self.assertEqual(report.modified_files, ["SKILL.md"])
        self.assertEqual(report.added_files, ["references/edge-cases.md"])
        self.assertEqual(report.deleted_files, [])
        self.assertEqual(report.sanitization_warnings, [])
        self.assertIn("diff --git a/SKILL.md b/SKILL.md", report.patch_text)

        # Now inject a personal email and local /Users/ path and verify sanitization catches both
        (local / "references" / "edge-cases.md").write_text(
            "Contact developer@private-domain.org or see /Users/alice/secret.txt\n",
            encoding="utf-8",
        )
        dirty_report = export_diff.generate_diff_export(upstream, local)
        self.assertGreaterEqual(len(dirty_report.sanitization_warnings), 2)

    def test_repository_skills_and_fixtures_lint(self) -> None:
        exit_code = lint_skills.verify_repository()
        self.assertEqual(exit_code, 0)

    def test_registry_json_integrity_and_fixture_hashes(self) -> None:
        registry_path = REPO_ROOT / "registry.json"
        self.assertTrue(registry_path.is_file(), "registry.json must exist")
        data = json.loads(registry_path.read_text(encoding="utf-8"))

        self.assertIn("skills", data)
        skills = data["skills"]
        self.assertGreaterEqual(len(skills), 3)

        commit_re = re.compile(r"^[0-9a-f]{40}$|^v\d+\.\d+\.\d+$")
        for entry in skills:
            name = entry["name"]
            commit_sha = entry["commit_sha"]
            expected_hash = entry["sha256"]

            self.assertRegex(
                commit_sha,
                commit_re,
                f"Registry skill {name} must be pinned to a 40-char commit SHA or vX.Y.Z tag",
            )
            self.assertRegex(expected_hash, verify_hash.SHA256_RE)

            fixture_dir = REPO_ROOT / entry["fixture_path"]
            self.assertTrue(
                fixture_dir.is_dir(),
                f"Fixture path {fixture_dir} for registry skill {name} must exist",
            )
            passed, actual = verify_hash.verify_directory_hash(fixture_dir, expected_hash)
            self.assertTrue(
                passed,
                f"Registry hash mismatch for {name}: expected {expected_hash}, got {actual}",
            )


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestTheOneSkillLifecycle)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
