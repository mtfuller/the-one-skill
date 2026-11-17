"""Tests for scripts/skillctl.py. Run: python3 -m unittest discover tests"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import skillctl  # noqa: E402
from skillctl import Refused, SkillCtl, folder_hash  # noqa: E402

SKILL = """---
name: csv-inspector
description: Inspect CSV files. Use when the user shares a CSV.
---
# csv-inspector

## Steps
1. Read the file.
"""


class SkillCtlTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "skills"
        self.skill = self.root / "csv-inspector"
        (self.skill / "references").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text(SKILL)
        (self.skill / "references" / "delimiters.md").write_text("Comma only.\n")
        self.original = folder_hash(self.skill)
        self.ctl = SkillCtl(self.root)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def change(self, line: str) -> None:
        d = self.ctl.draft("csv-inspector")
        (d / "SKILL.md").write_text((d / "SKILL.md").read_text() + line + "\n")
        self.ctl.apply("csv-inspector")

    def test_store_and_draft_are_outside_the_skills_folder(self) -> None:
        d = self.ctl.draft("csv-inspector")
        self.assertNotIn(self.root, d.parents)
        self.assertEqual([p.name for p in self.root.iterdir()], ["csv-inspector"])
        with self.assertRaises(Refused):
            SkillCtl(self.root, self.root / "store")

    def test_apply_then_use_original_restores_exact_folder(self) -> None:
        d = self.ctl.draft("csv-inspector")
        (d / "references" / "delimiters.md").unlink()
        (d / "references" / "encoding.md").write_text("Handle utf-8-sig.\n")
        self.assertIn("+Handle utf-8-sig.", self.ctl.diff("csv-inspector"))
        self.ctl.apply("csv-inspector")
        tuned = folder_hash(self.skill)
        self.assertNotEqual(tuned, self.original)

        self.ctl.use("csv-inspector", "original")
        self.assertEqual(folder_hash(self.skill), self.original)
        self.assertEqual((self.skill / "SKILL.md").read_text(), SKILL)
        self.ctl.use("csv-inspector", "tuned")
        self.assertEqual(folder_hash(self.skill), tuned)

    def test_original_never_changes_across_many_changes(self) -> None:
        for i in range(3):
            self.change(f"{i + 2}. Step {i}.")
        st = self.ctl.state("csv-inspector")
        self.assertEqual(st["original"], self.original)
        self.assertEqual(folder_hash(self.ctl.version("csv-inspector", self.original)), self.original)
        self.assertEqual(len(list((self.ctl.sdir("csv-inspector") / "versions").iterdir())), 2)
        self.ctl.use("csv-inspector", "original")
        self.assertEqual(folder_hash(self.skill), self.original)

    def test_hand_edits_are_never_overwritten(self) -> None:
        self.change("2. Tuned step.")
        (self.skill / "SKILL.md").write_text((self.skill / "SKILL.md").read_text() + "3. Hand edit.\n")
        self.assertEqual(self.ctl.which("csv-inspector", self.ctl.state("csv-inspector")), "edited")
        with self.assertRaises(Refused):
            self.ctl.use("csv-inspector", "original")
        self.assertIn("Hand edit", (self.skill / "SKILL.md").read_text())
        # draft starts from the hand edit, so apply keeps it
        self.ctl.draft("csv-inspector")
        self.ctl.apply("csv-inspector")
        self.assertIn("Hand edit", (self.skill / "SKILL.md").read_text())
        self.ctl.use("csv-inspector", "original")
        self.assertEqual(folder_hash(self.skill), self.original)

    def test_edit_during_draft_blocks_apply(self) -> None:
        self.ctl.draft("csv-inspector")
        (self.skill / "SKILL.md").write_text(SKILL + "Edited meanwhile.\n")
        with self.assertRaises(Refused):
            self.ctl.apply("csv-inspector")
        self.assertIn("Edited meanwhile", (self.skill / "SKILL.md").read_text())

    def test_name_change_is_refused(self) -> None:
        d = self.ctl.draft("csv-inspector")
        (d / "SKILL.md").write_text(SKILL.replace("name: csv-inspector", "name: user:csv-inspector"))
        with self.assertRaises(Refused):
            self.ctl.apply("csv-inspector")
        self.assertEqual(folder_hash(self.skill), self.original)

    def test_damaged_store_copy_is_never_installed(self) -> None:
        self.change("2. Tuned.")
        (self.ctl.version("csv-inspector", self.original) / "SKILL.md").write_text("tampered\n")
        with self.assertRaises(Refused):
            self.ctl.use("csv-inspector", "original")
        self.assertIn("Tuned", (self.skill / "SKILL.md").read_text())

    def test_linked_skill_is_refused(self) -> None:
        (self.root / "linked").symlink_to(self.skill)
        with self.assertRaises(Refused):
            self.ctl.draft("linked")

    def test_interrupted_apply_is_finished_by_running_it_again(self) -> None:
        d = self.ctl.draft("csv-inspector")
        (d / "SKILL.md").write_text(SKILL + "2. New.\n")
        real_move = shutil.move
        calls = []

        def flaky(src: str, dst: str) -> str:
            calls.append(src)
            if len(calls) == 2:  # installed folder moved out, new one not yet in
                raise OSError("disk full")
            return real_move(src, dst)

        with mock.patch.object(skillctl.shutil, "move", flaky):
            with self.assertRaises(OSError):
                self.ctl.apply("csv-inspector")
        self.assertFalse(self.skill.exists())
        self.ctl.apply("csv-inspector")  # same command again
        self.assertIn("2. New.", (self.skill / "SKILL.md").read_text())
        self.ctl.use("csv-inspector", "original")
        self.assertEqual(folder_hash(self.skill), self.original)

    def test_cli(self) -> None:
        args = ["--root", str(self.root)]
        self.assertEqual(skillctl.main(args + ["draft", "csv-inspector"]), 0)
        d = self.ctl.sdir("csv-inspector") / "draft" / "SKILL.md"
        d.write_text(d.read_text() + "2. CLI.\n")
        self.assertEqual(skillctl.main(args + ["apply", "csv-inspector"]), 0)
        self.assertEqual(skillctl.main(args + ["use", "csv-inspector", "original"]), 0)
        self.assertEqual(folder_hash(self.skill), self.original)
        self.assertEqual(skillctl.main(args + ["status"]), 0)
        self.assertEqual(skillctl.main(args + ["use", "missing-skill", "original"]), 1)


if __name__ == "__main__":
    unittest.main()
