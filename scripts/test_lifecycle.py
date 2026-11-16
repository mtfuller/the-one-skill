#!/usr/bin/env python3
"""Deterministic unit & round-trip lifecycle test suite for the-one-skill.

Pure Python 3 standard library (unittest). Tests:
  1. Trusted upstream source verification (config/trusted-sources.json):
     official Anthropic, OpenAI, and Google Gemini skill URLs pass; untrusted URLs fail.
  2. Explicit frontmatter 'Use when' / 'Do not use when' description enforcement.
  3. Delimiter block mounting, idempotency, and clean unmounting round-trip
     (mount -> strip restores original content byte-for-byte).
  4. Consent lock enforcement (the-one-skill:ignore prevents mounting or edits).
  5. Snapshot & revert round-trip restoration.
  6. export_diff.py: unified diff generation, file summary, and PII leak detection.
  7. lint_skills.py: 800-token ceiling, frontmatter, trigger overlap detection,
     and security-policy.json trap blocking.

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
description: Format markdown tables and align columns deterministically. Use when aligning markdown tables in documentation files. Do not use when editing CSV files or JSON schemas.
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

    def test_trusted_sources_url_verification(self) -> None:
        sources_path = REPO_ROOT / "config" / "trusted-sources.json"
        self.assertTrue(sources_path.is_file(), "config/trusted-sources.json must exist")
        data = json.loads(sources_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data.get("trusted_sources", [])), 3)

        # Official Anthropic, OpenAI, and Google Gemini URLs must pass
        for valid_url in [
            "https://github.com/anthropics/skills/tree/main/skills/pdf",
            "https://raw.githubusercontent.com/anthropics/skills/main/skills/xlsx/SKILL.md",
            "https://github.com/openai/skills/tree/main/skills",
            "https://github.com/google-gemini/gemini-skills/tree/main/skills",
        ]:
            passed, msg = lint_skills.verify_trusted_source_url(valid_url)
            self.assertTrue(passed, f"Expected trusted URL to pass: {valid_url} ({msg})")

        # Untrusted third-party URLs must fail
        for untrusted_url in [
            "https://github.com/random-user/unverified-skills/blob/main/SKILL.md",
            "https://evil.example.com/skills/SKILL.md",
        ]:
            passed, msg = lint_skills.verify_trusted_source_url(untrusted_url)
            self.assertFalse(passed, f"Expected untrusted URL to fail: {untrusted_url} ({msg})")

    def test_frontmatter_requires_explicit_use_when_and_do_not_use_when(self) -> None:
        skill_file = self.tmp_dir / "SKILL.md"
        vague_frontmatter = VANILLA_SKILL_SAMPLE.replace(
            "description: Format markdown tables and align columns deterministically. Use when aligning markdown tables in documentation files. Do not use when editing CSV files or JSON schemas.",
            "description: Format markdown tables and align columns deterministically.",
        )
        skill_file.write_text(vague_frontmatter, encoding="utf-8")
        res = lint_skills.lint_skill_file(skill_file)
        self.assertFalse(res.passed)
        self.assertTrue(any("Use when" in e for e in res.errors))
        self.assertTrue(any("Do not use when" in e for e in res.errors))

    def test_mount_and_strip_round_trip_restores_exact_bytes(self) -> None:
        skill_file = self.tmp_dir / "SKILL.md"
        skill_file.write_text(VANILLA_SKILL_SAMPLE, encoding="utf-8")

        mounted = mount_integration_block(skill_file)
        self.assertIn(OPT_IN_MARKER, mounted)
        self.assertIn(BLOCK_START, mounted)
        self.assertIn(BLOCK_END, mounted)

        mounted_again = mount_integration_block(skill_file)
        self.assertEqual(mounted, mounted_again)

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

        mount_integration_block(skill_file)
        skill_file.write_text(
            skill_file.read_text(encoding="utf-8") + "\n<!-- extra edit -->\n",
            encoding="utf-8",
        )
        self.assertNotEqual(skill_file.read_text(encoding="utf-8"), VANILLA_SKILL_SAMPLE)

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

        (local / "references" / "edge-cases.md").write_text(
            "Contact developer@private-domain.org or see /Users/alice/secret.txt\n",
            encoding="utf-8",
        )
        dirty_report = export_diff.generate_diff_export(upstream, local)
        self.assertGreaterEqual(len(dirty_report.sanitization_warnings), 2)

    def test_repository_skills_and_fixtures_lint(self) -> None:
        exit_code = lint_skills.verify_repository()
        self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestTheOneSkillLifecycle)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
