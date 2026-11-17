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

    def test_readonly_files_are_never_changed_by_apply(self) -> None:
        (self.skill / "references" / "readonly-policy.md").write_text("Rule.\n")
        d = self.ctl.draft("csv-inspector")
        (d / "SKILL.md").write_text(SKILL + "2. Fine.\n")
        (d / "references" / "readonly-policy.md").write_text("Weaker rule.\n")
        with self.assertRaises(Refused):
            self.ctl.apply("csv-inspector")
        (d / "references" / "readonly-policy.md").unlink()
        with self.assertRaises(Refused):  # deleting is a change too
            self.ctl.apply("csv-inspector")
        (d / "references" / "readonly-policy.md").write_text("Rule.\n")
        self.ctl.apply("csv-inspector")  # other changes go through
        self.assertIn("2. Fine.", (self.skill / "SKILL.md").read_text())
        self.assertEqual((self.skill / "references" / "readonly-policy.md").read_text(), "Rule.\n")

    def test_git_checkout_keeps_its_git_folder(self) -> None:
        (self.skill / ".git").mkdir()
        (self.skill / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
        self.change("2. Tuned.")
        self.assertTrue((self.skill / ".git" / "HEAD").is_file())
        self.ctl.use("csv-inspector", "original")
        self.assertTrue((self.skill / ".git" / "HEAD").is_file())
        self.assertEqual(folder_hash(self.skill), self.original)
        self.assertFalse((self.ctl.version("csv-inspector", self.original) / ".git").exists())

    def test_roster_lists_every_skill_with_problems(self) -> None:
        bad = self.root / "Bad_Skill"
        bad.mkdir()
        (bad / "SKILL.md").write_text("---\nname: other\ndescription: Does things.\n---\n")
        (self.root / "empty").mkdir()
        folded = self.root / "folded"
        folded.mkdir()
        (folded / "SKILL.md").write_text("---\nname: folded\ndescription: >\n  Plan trips.\n  Use when asked.\n---\n")
        self.change("2. Tuned.")
        rows = {r["name"]: r for r in self.ctl.roster()}
        self.assertEqual(rows["csv-inspector"]["state"], "tuned")
        self.assertEqual(rows["csv-inspector"]["issues"], [])
        self.assertEqual(rows["folded"]["description"], "Plan trips. Use when asked.")
        self.assertEqual(rows["folded"]["issues"], [])
        self.assertEqual(rows["Bad_Skill"]["state"], "unmanaged")
        joined = " ".join(rows["Bad_Skill"]["issues"])
        for issue in ("differs from folder", "invalid folder name", "when to use"):
            self.assertIn(issue, joined)
        self.assertIn("no SKILL.md", rows["empty"]["issues"])

    def test_retire_and_restore_round_trip(self) -> None:
        (self.skill / ".git").mkdir()
        self.ctl.retire("csv-inspector")
        self.assertFalse(self.skill.exists())
        self.assertEqual(self.ctl.status(), [("csv-inspector", "retired")])
        with self.assertRaises(Refused):
            self.ctl.retire("csv-inspector")
        self.ctl.restore("csv-inspector")
        self.assertEqual(folder_hash(self.skill), self.original)
        self.assertTrue((self.skill / ".git").is_dir())
        with self.assertRaises(Refused):
            self.ctl.restore("csv-inspector")

    def test_restore_never_overwrites_a_skill(self) -> None:
        self.ctl.retire("csv-inspector")
        self.skill.mkdir()
        (self.skill / "SKILL.md").write_text("new\n")
        with self.assertRaises(Refused):
            self.ctl.restore("csv-inspector")
        self.assertEqual((self.skill / "SKILL.md").read_text(), "new\n")

    def test_cli(self) -> None:
        args = ["--root", str(self.root)]
        self.assertEqual(skillctl.main(args + ["draft", "csv-inspector"]), 0)
        d = self.ctl.sdir("csv-inspector") / "draft" / "SKILL.md"
        d.write_text(d.read_text() + "2. CLI.\n")
        self.assertEqual(skillctl.main(args + ["apply", "csv-inspector"]), 0)
        self.assertEqual(skillctl.main(args + ["use", "csv-inspector", "original"]), 0)
        self.assertEqual(folder_hash(self.skill), self.original)
        self.assertEqual(skillctl.main(args + ["status"]), 0)
        self.assertEqual(skillctl.main(args + ["list"]), 0)
        self.assertEqual(skillctl.main(args + ["list", "--json"]), 0)
        self.assertEqual(skillctl.main(args + ["retire", "csv-inspector"]), 0)
        self.assertEqual(skillctl.main(args + ["restore", "csv-inspector"]), 0)
        self.assertEqual(folder_hash(self.skill), self.original)
        self.assertEqual(skillctl.main(args + ["use", "missing-skill", "original"]), 1)


if __name__ == "__main__":
    unittest.main()
