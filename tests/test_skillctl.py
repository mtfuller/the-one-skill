"""Tests for scripts/skillctl.py. Run: python3 -m unittest discover tests"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import bundle  # noqa: E402
import guard_skills  # noqa: E402
import skillctl  # noqa: E402
from skillctl import Refused, SkillCtl, folder_hash  # noqa: E402

SKILL = """---
name: csv-inspector
description: Inspect CSV files. Use when the user shares a CSV.
---
# csv-inspector

## Steps
1. Read the file. For delimiters, read `references/delimiters.md`.
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
        self.assertEqual(len(list((self.ctl.sdir("csv-inspector") / "versions").iterdir())), 4)
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

    def test_previous_steps_back_one_applied_version(self) -> None:
        self.change("2. First.")
        first = folder_hash(self.skill)
        self.change("3. Second.")
        second = folder_hash(self.skill)
        self.ctl.use("csv-inspector", "previous")
        self.assertEqual(folder_hash(self.skill), first)
        self.assertEqual(self.ctl.which("csv-inspector", self.ctl.state("csv-inspector")), "earlier")
        self.ctl.use("csv-inspector", "tuned")
        self.assertEqual(folder_hash(self.skill), second)
        self.ctl.use("csv-inspector", first[:8])  # by version id prefix
        self.assertEqual(folder_hash(self.skill), first)
        with self.assertRaises(Refused):
            self.ctl.use("csv-inspector", "abc")  # too short / unknown

    def test_history_keeps_the_last_few_versions_and_the_original(self) -> None:
        for i in range(skillctl.KEEP_APPLIED + 2):
            self.change(f"{i + 2}. Step {i}.")
        rows = self.ctl.history("csv-inspector")
        self.assertEqual(rows[0]["label"], "original")
        self.assertEqual(rows[0]["version"], self.original)
        self.assertEqual(len(rows), 1 + skillctl.KEEP_APPLIED)
        self.assertEqual([r["label"] for r in rows[-2:]], ["previous", "tuned"])
        self.assertTrue(rows[-1]["installed"])
        kept = {p.name for p in (self.ctl.sdir("csv-inspector") / "versions").iterdir()}
        self.assertEqual(kept, {r["version"] for r in rows})
        self.ctl.use("csv-inspector", "original")
        self.assertEqual(folder_hash(self.skill), self.original)

    def test_removing_one_rule_keeps_the_version_that_had_it(self) -> None:
        self.change("- Rule that causes trouble.")
        with_rule = folder_hash(self.skill)
        d = self.ctl.draft("csv-inspector")
        (d / "SKILL.md").write_text((d / "SKILL.md").read_text().replace("- Rule that causes trouble.\n", ""))
        self.ctl.apply("csv-inspector")
        self.assertNotIn("causes trouble", (self.skill / "SKILL.md").read_text())
        self.ctl.use("csv-inspector", "previous")
        self.assertEqual(folder_hash(self.skill), with_rule)

    def test_new_skill_is_tracked_and_retired_to_go_back(self) -> None:
        d = self.ctl.new("weekly-report")
        self.assertIn("name: weekly-report", (d / "SKILL.md").read_text())
        self.assertFalse((self.root / "weekly-report").exists())
        self.assertIn("+name: weekly-report", self.ctl.diff("weekly-report"))
        self.ctl.apply("weekly-report")
        self.assertTrue((self.root / "weekly-report" / "SKILL.md").is_file())
        self.assertIn(("weekly-report", "tuned (created by the-one-skill)"), self.ctl.status())
        with self.assertRaises(Refused):  # no original to go back to
            self.ctl.use("weekly-report", "original")
        self.ctl.retire("weekly-report")
        self.assertFalse((self.root / "weekly-report").exists())
        self.ctl.restore("weekly-report")
        self.assertTrue((self.root / "weekly-report").is_dir())

    def test_new_from_folder_and_name_checks(self) -> None:
        src = self.tmp / "incoming"
        src.mkdir()
        (src / "SKILL.md").write_text("---\nname: tf-guard\ndescription: x. Use when y.\n---\n")
        (src / "scripts").mkdir()
        (src / "scripts" / "check.sh").write_text("echo ok\n")
        d = self.ctl.new("tf-guard", src)
        self.assertTrue((d / "scripts" / "check.sh").is_file())
        self.ctl.apply("tf-guard")
        with self.assertRaises(Refused):
            self.ctl.new("csv-inspector")  # already installed
        with self.assertRaises(Refused):
            self.ctl.new("Bad_Name")
        with self.assertRaises(Refused):
            self.ctl.new("tf-guard")  # already tracked

    def _add_skill(self, name: str) -> Path:
        d = self.root / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x. Use when y.\n---\n# {name}\n")
        return d

    def test_change_set_undo_reverses_a_merge(self) -> None:
        other = self._add_skill("csv-analyzer")
        other_hash = folder_hash(other)
        self.ctl.begin_set("merge-csv", "two CSV skills overlapped")
        d = self.ctl.draft("csv-inspector")
        (d / "SKILL.md").write_text(SKILL + "2. Stats from csv-analyzer.\n")
        self.ctl.apply("csv-inspector")
        self.ctl.retire("csv-analyzer")
        new = self.ctl.new("csv-notes")
        self.ctl.apply("csv-notes")
        self.ctl.change_set = None
        cs = self.ctl.sets()["merge-csv"]
        self.assertEqual([st["op"] for st in cs["steps"]], ["apply", "retire", "apply"])
        self.assertEqual(cs["note"], "two CSV skills overlapped")

        plan = self.ctl.undo_plan("merge-csv")  # dry run: nothing changes
        self.assertEqual([(a, k) for a, k, _ in plan],
                         [("retire", "csv-notes"), ("restore", "csv-analyzer"), ("install", "csv-inspector")])
        self.assertFalse(other.exists())

        self.ctl.undo_set("merge-csv")
        self.assertEqual(folder_hash(self.skill), self.original)
        self.assertEqual(folder_hash(other), other_hash)
        self.assertFalse((self.root / "csv-notes").exists())
        self.assertTrue(self.ctl.sets()["merge-csv"]["undone"])
        with self.assertRaises(Refused):
            self.ctl.undo_set("merge-csv")  # only once
        with self.assertRaises(Refused):
            self.ctl.begin_set("merge-csv")  # an undone set is closed

    def test_undo_refuses_when_a_skill_changed_since(self) -> None:
        self.ctl.begin_set("tweak")
        self.change("2. In the set.")
        self.ctl.change_set = None
        self.change("3. After the set.")
        with self.assertRaises(Refused):
            self.ctl.undo_plan("tweak")
        self.assertIn("After the set", (self.skill / "SKILL.md").read_text())

    def test_undo_handles_several_steps_on_one_skill(self) -> None:
        self.ctl.begin_set("rework")
        self.change("2. First.")
        self.change("3. Second.")
        self.ctl.retire("csv-inspector")
        self.ctl.undo_set("rework")
        self.assertEqual(folder_hash(self.skill), self.original)

    def test_steps_outside_a_set_are_not_recorded(self) -> None:
        self.change("2. Unrecorded.")
        self.assertEqual(self.ctl.sets(), {})
        with self.assertRaises(Refused):
            self.ctl.begin_set("Bad Name")

    def test_guard_blocks_direct_edits_inside_skills_only(self) -> None:
        roots = [self.root.resolve()]
        inside = {"tool_name": "Edit", "tool_input": {"file_path": str(self.skill / "SKILL.md")}}
        self.assertIsNotNone(guard_skills.check(inside, roots))
        relative = {"tool_name": "Write", "tool_input": {"file_path": "skills/new/SKILL.md"}, "cwd": str(self.tmp)}
        self.assertIsNotNone(guard_skills.check(relative, roots))
        draft = self.ctl.draft("csv-inspector")  # drafts live in the store, outside the skills folder
        self.assertIsNone(guard_skills.check({"tool_name": "Edit", "tool_input": {"file_path": str(draft / "SKILL.md")}}, roots))
        self.assertIsNone(guard_skills.check({"tool_name": "Bash", "tool_input": {"command": "ls"}}, roots))
        sibling = {"tool_name": "Write", "tool_input": {"file_path": str(self.tmp / "skills-notes.md")}}
        self.assertIsNone(guard_skills.check(sibling, roots))

    def test_guard_hook_end_to_end(self) -> None:
        import json as _json
        import subprocess
        cmd = self.ctl.guard_settings()["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        event = _json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(self.skill / "SKILL.md")}})
        r = subprocess.run(cmd, shell=True, input=event, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("the-one-skill", r.stderr)
        ok = _json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(self.tmp / "elsewhere.md")}})
        self.assertEqual(subprocess.run(cmd, shell=True, input=ok, capture_output=True, text=True).returncode, 0)
        self.assertEqual(subprocess.run(cmd, shell=True, input="not json", capture_output=True, text=True).returncode, 0)

    # ----- upgrade -----
    def _release(self, version: str, edit=None) -> Path:
        """A release folder of csv-inspector, built from the original files."""
        rel = self.tmp / f"release-{version}"
        shutil.rmtree(rel, ignore_errors=True)
        shutil.copytree(self.ctl.version("csv-inspector", self.ctl.state("csv-inspector")["original"]), rel)
        (rel / "VERSION.md").write_text(version + "\n")
        if edit:
            edit(rel)
        return rel

    def _setup_installed_release(self) -> None:
        (self.skill / "VERSION.md").write_text("1.0.0\n")
        (self.skill / "references" / "readonly-policy.md").write_text("Rule v1.\n")
        (self.skill / "references" / "agentspace").mkdir()
        (self.skill / "references" / "agentspace" / "index.md").write_text("# index (empty)\n")
        self.original = folder_hash(self.skill)
        d = self.ctl.draft("csv-inspector")  # local life: an adapter note and a local tweak
        (d / "references" / "agentspace" / "claude-code.md").write_text("Detect: here\n")
        (d / "references" / "agentspace" / "index.md").write_text("# index\n| claude-code.md |\n")
        (d / "SKILL.md").write_text((d / "SKILL.md").read_text().replace("1. Read the file.", "1. Read the file (local tweak)."))
        self.ctl.apply("csv-inspector")

    def test_merge3(self) -> None:
        base = ["a\n", "b\n", "c\n", "d\n"]
        merged, clash = skillctl.merge3(base, ["A\n", "b\n", "c\n", "d\n"], ["a\n", "b\n", "c\n", "D\n"])
        self.assertEqual((merged, clash), (["A\n", "b\n", "c\n", "D\n"], False))
        merged, clash = skillctl.merge3(base, ["a\n", "X\n", "c\n", "d\n"], ["a\n", "X\n", "c\n", "d\n"])
        self.assertEqual((merged, clash), (["a\n", "X\n", "c\n", "d\n"], False))
        merged, clash = skillctl.merge3(base, ["a\n", "mine\n", "c\n", "d\n"], ["a\n", "theirs\n", "c\n", "d\n"])
        self.assertTrue(clash)
        self.assertIn(skillctl.CONFLICT_START + "\n", merged)
        merged, clash = skillctl.merge3(base, ["a\n", "b\n", "c\n", "D\n"], base + ["e\n"])  # adjacent: fine
        self.assertEqual((merged, clash), (["a\n", "b\n", "c\n", "D\n", "e\n"], False))
        merged, clash = skillctl.merge3(base, base + ["mine\n"], base + ["theirs\n"])  # same insertion point
        self.assertTrue(clash)

    def test_upgrade_keeps_local_changes_and_agentspace(self) -> None:
        self._setup_installed_release()
        def edit(rel: Path) -> None:
            (rel / "SKILL.md").write_text((rel / "SKILL.md").read_text() + "2. New step from the release.\n")
            (rel / "references" / "new-ref.md").write_text("New reference.\n")
            (rel / "references" / "readonly-policy.md").write_text("Rule v2.\n")
        report = self.ctl.upgrade("csv-inspector", self._release("1.1.0", edit), keep=["references/agentspace"])
        self.assertEqual(report["conflicts"], [])
        self.assertIn("SKILL.md", report["merged"])
        self.assertIn("references/new-ref.md", report["from_release"])
        self.assertIn("references/readonly-policy.md", report["readonly_updated"])
        self.assertFalse((self.skill / "references" / "new-ref.md").exists())  # nothing installed yet
        before = folder_hash(self.skill)
        self.ctl.apply("csv-inspector")
        text = (self.skill / "SKILL.md").read_text()
        self.assertIn("local tweak", text)
        self.assertIn("New step from the release", text)
        self.assertEqual((self.skill / "VERSION.md").read_text(), "1.1.0\n")
        self.assertEqual((self.skill / "references" / "readonly-policy.md").read_text(), "Rule v2.\n")
        self.assertEqual((self.skill / "references" / "agentspace" / "claude-code.md").read_text(), "Detect: here\n")
        self.assertIn("claude-code.md", (self.skill / "references" / "agentspace" / "index.md").read_text())
        self.ctl.use("csv-inspector", "previous")  # undo the update
        self.assertEqual(folder_hash(self.skill), before)
        self.ctl.use("csv-inspector", "tuned")
        # next release: base is now 1.1.0, so the earlier release changes don't clash again
        def edit2(rel: Path) -> None:
            edit(rel)
            (rel / "references" / "new-ref.md").write_text("New reference, revised.\n")
        report = self.ctl.upgrade("csv-inspector", self._release("1.2.0", edit2), keep=["references/agentspace"])
        self.assertEqual(report["conflicts"], [])
        self.assertEqual(report["from_release"], ["VERSION.md", "references/new-ref.md"])

    def test_upgrade_conflict_must_be_resolved(self) -> None:
        self._setup_installed_release()
        def edit(rel: Path) -> None:
            (rel / "SKILL.md").write_text((rel / "SKILL.md").read_text().replace("1. Read the file.", "1. Read the file (release)."))
        report = self.ctl.upgrade("csv-inspector", self._release("1.1.0", edit), keep=["references/agentspace"])
        self.assertEqual(report["conflicts"], ["SKILL.md"])
        with self.assertRaises(Refused):
            self.ctl.apply("csv-inspector")
        draft = Path(report["draft"]) / "SKILL.md"
        lines = [ln for ln in draft.read_text().splitlines(keepends=True)
                 if not ln.startswith(("<<<<<<<", "=======", ">>>>>>>")) and "(release)" not in ln]
        draft.write_text("".join(lines))
        self.ctl.apply("csv-inspector")
        self.assertIn("local tweak", (self.skill / "SKILL.md").read_text())

    def test_upgrade_guards(self) -> None:
        self._setup_installed_release()
        with self.assertRaises(Refused):  # older release
            self.ctl.upgrade("csv-inspector", self._release("0.9.0"))
        with self.assertRaises(Refused):  # a different skill
            other = self._release("1.1.0", lambda r: (r / "SKILL.md").write_text(SKILL.replace("csv-inspector", "other")))
            self.ctl.upgrade("csv-inspector", other)
        # the agent may not edit a read-only file away from the release's exact version
        def edit(rel: Path) -> None:
            (rel / "references" / "readonly-policy.md").write_text("Rule v2.\n")
        report = self.ctl.upgrade("csv-inspector", self._release("1.1.0", edit), keep=["references/agentspace"])
        (Path(report["draft"]) / "references" / "readonly-policy.md").write_text("Rule v2, loosened.\n")
        with self.assertRaises(Refused):
            self.ctl.apply("csv-inspector")
        # a hand-edited read-only file that the release also changed is left to the user
        (Path(report["draft"]) / "references" / "readonly-policy.md").write_text("Rule v2.\n")
        self.ctl.draft("csv-inspector")  # abandon that upgrade
        (self.skill / "references" / "readonly-policy.md").write_text("Rule v1, hand edit.\n")
        with self.assertRaises(Refused):
            self.ctl.upgrade("csv-inspector", self._release("1.1.0", edit), keep=["references/agentspace"])

    def test_bundle_round_trip_without_private_agentspace(self) -> None:
        (self.skill / "VERSION.md").write_text("1.2.3\n")
        (self.skill / "references" / "agentspace").mkdir()
        (self.skill / "references" / "agentspace" / "index.md").write_text("# index\n")
        (self.skill / "references" / "agentspace" / "private.md").write_text("secret\n")
        text = bundle.pack(self.skill)
        self.assertIn("Version: 1.2.3", text)
        self.assertNotIn("secret", text)
        b = self.tmp / "b.md"
        b.write_text(text)
        out = self.tmp / "unpacked"
        written = bundle.unpack(b, out)
        self.assertIn("references/agentspace/index.md", written)
        self.assertEqual((out / "SKILL.md").read_text(), SKILL)
        self.assertEqual((out / "references" / "delimiters.md").read_text(), "Comma only.\n")
        self.assertFalse((out / "references" / "agentspace" / "private.md").exists())
        (self.skill / "tests").mkdir()
        (self.skill / "tests" / "test_x.py").write_text("pass\n")
        (self.skill / "NOTES").write_text("no extension\n")
        text = bundle.pack(self.skill)
        self.assertNotIn("tests/test_x.py", text)  # a release is the package, not the dev tree
        self.assertNotIn("=== FILE: NOTES ===", text)
        z = self.tmp / "pkg.zip"
        names = bundle.make_zip(self.skill, z)
        self.assertIn("the-one-skill/SKILL.md", names)
        self.assertTrue(all(n.endswith((".md", ".py")) for n in names))
        self.assertNotIn("the-one-skill/references/agentspace/private.md", names)

    def test_upgrade_from_a_package_keeps_files_outside_it(self) -> None:
        self._setup_installed_release()
        for rel in ("tests/test_x.py", ".github/workflows/t.yml", "LICENSE"):
            (self.skill / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.skill / rel).write_text("dev\n")
        d = self.ctl.draft("csv-inspector")  # make them part of the installed history
        self.ctl.apply("csv-inspector")
        pkg = self._release("1.1.0")  # a package: no tests, no CI, no LICENSE
        report = self.ctl.upgrade("csv-inspector", pkg, keep=["references/agentspace"])
        self.assertEqual(report["removed"], [])
        self.ctl.apply("csv-inspector")
        for rel in ("tests/test_x.py", ".github/workflows/t.yml", "LICENSE"):
            self.assertTrue((self.skill / rel).is_file(), rel)

    def test_default_store_location(self) -> None:
        proj = self.tmp / "proj"
        skills = proj / ".claude" / "skills"
        skills.mkdir(parents=True)
        self.assertEqual(SkillCtl(skills).store, (proj / ".tos-store").resolve())
        self.assertEqual(self.ctl.store, (self.tmp / ".tos-store").resolve())  # other layouts: next to it
        legacy = proj / ".claude" / "the-one-skill-store"
        legacy.mkdir()
        self.assertEqual(SkillCtl(skills).store, legacy.resolve())  # an existing old store keeps working

    def test_move_store_keeps_everything(self) -> None:
        proj = self.tmp / "proj"
        skills = proj / ".claude" / "skills"
        shutil.copytree(self.skill, skills / "csv-inspector")
        legacy = proj / ".claude" / "the-one-skill-store"
        ctl = SkillCtl(skills, legacy)
        d = ctl.draft("csv-inspector")
        (d / "SKILL.md").write_text(SKILL + "2. Tuned.\n")
        ctl.apply("csv-inspector")
        ctl = SkillCtl(skills)  # picks up the old store by default
        self.assertEqual(ctl.store, legacy.resolve())
        dest = ctl.move_store()
        self.assertEqual(dest, (proj / ".tos-store").resolve())
        self.assertFalse(legacy.exists())
        ctl = SkillCtl(skills)
        self.assertEqual(ctl.store, dest)
        ctl.use("csv-inspector", "original")
        self.assertEqual((skills / "csv-inspector" / "SKILL.md").read_text(), SKILL)
        with self.assertRaises(Refused):
            ctl.move_store()  # already there

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
        self.assertEqual(skillctl.main(args + ["history", "csv-inspector"]), 0)
        self.assertEqual(skillctl.main(args + ["use", "csv-inspector", "previous"]), 1)  # only one applied version
        self.assertEqual(skillctl.main(args + ["new", "fresh-skill"]), 0)
        self.assertEqual(skillctl.main(args + ["retire", "csv-inspector", "--set", "cli-set", "--note", "why"]), 0)
        self.assertEqual(skillctl.main(args + ["sets"]), 0)
        self.assertEqual(skillctl.main(args + ["guard"]), 0)
        self.assertEqual(skillctl.main(args + ["undo-set", "cli-set"]), 0)  # dry run
        self.assertFalse(self.skill.exists())
        self.assertEqual(skillctl.main(args + ["undo-set", "cli-set", "--apply"]), 0)
        self.assertTrue(self.skill.exists())
        self.assertEqual(skillctl.main(args + ["retire", "csv-inspector"]), 0)
        self.assertEqual(skillctl.main(args + ["restore", "csv-inspector"]), 0)
        self.assertEqual(folder_hash(self.skill), self.original)
        self.assertEqual(skillctl.main(args + ["use", "missing-skill", "original"]), 1)


BRAND = """## Brand rules
- Use the Arial font for every heading and body text in the document.
- Put the company logo in the top right corner of the first page only.
- Keep the primary colour navy blue and never use more than two accent colours.
- End with a contact slide that lists the account owner and their email address.
"""


def skill_md(name: str, description: str, body: str) -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n{body}"


class OverlapTest(unittest.TestCase):
    """Orthogonality: overlap in triggers and in procedure."""

    ROSTER = {
        "proposal-deck": ("Build sales proposal decks as PPTX. Use when the user asks for a proposal or pitch deck.",
                          "1. Gather the client name, the problem statement, and the proposed pricing tiers.\n"
                          "2. Write one slide per pricing tier with a comparison table and a recommendation.\n" + BRAND),
        "timeline-slides": ("Turn project milestones into a timeline slide. Use when the user wants a roadmap visual.",
                            "1. Read milestones with dates and owners, then sort them chronologically before drawing.\n"
                            "2. Draw a horizontal arrow with milestone markers spaced in proportion to the dates.\n" + BRAND),
        "board-update": ("Draft quarterly board update memos. Use when the user prepares a board meeting.",
                         "1. Collect revenue, burn, runway and hiring numbers for the quarter from the finance sheet.\n"
                         "2. Lead with the three decisions the board must take, then the metrics, then the risks.\n" + BRAND),
        "csv-inspector": ("Inspect CSV files and report columns, types and missing values. Use when the user shares a CSV file.",
                          "1. Detect the delimiter and encoding, then load the first thousand rows into memory.\n"
                          "2. Report every column with its inferred type and the count of missing values as a table.\n"),
        "csv-summary": ("Summarize CSV data files with totals and averages per column. Use when the user shares a CSV file "
                        "and wants a summary.",
                        "1. Load the whole file, group by the category column if there is one, and compute totals.\n"
                        "2. Present averages, minimums and maximums for every numeric column in one markdown table.\n"),
        "git-release": ("Cut a tagged release from main with a changelog. Use when the user says ship, release, or tag.",
                        "1. Check the working tree is clean and the tests pass before creating any tag on the branch.\n"
                        "2. Write the changelog section from merged pull requests since the previous tag was created.\n"),
        "the-one-skill": ("Manage skills. Use when the user wants to change a skill.", BRAND),
    }

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "skills"
        for name, (desc, body) in self.ROSTER.items():
            self.write(self.root / name, name, desc, body)
        self.builtin = self.tmp / "builtin"
        self.write(self.builtin / "pptx", "pptx", "Create, read and edit PowerPoint pptx decks and slides. "
                   "Use when any pptx file or slide deck is involved.", "1. Build the presentation with python-pptx.\n")
        self.ctl = SkillCtl(self.root)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    @staticmethod
    def write(folder: Path, name: str, desc: str, body: str) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "SKILL.md").write_text(skill_md(name, desc, body))

    def pair(self, r: dict, a: str, b: str) -> dict | None:
        return next((p for p in r["pairs"] if {p["a"], p["b"]} == {a, b}), None)

    def test_policy_repeated_in_three_skills_is_one_block(self) -> None:
        r = self.ctl.overlap()
        top = r["shared_blocks"][0]
        self.assertEqual(top["skills"], ["board-update", "proposal-deck", "timeline-slides"])
        self.assertEqual(top["lines"], 4)
        p = self.pair(r, "proposal-deck", "board-update")
        self.assertLess(p["triggers"], 0.30)  # different requests ...
        self.assertIn("same procedure", p["verdict"])  # ... same procedure

    def test_the_one_skill_and_unrelated_skills_are_left_out(self) -> None:
        r = self.ctl.overlap()
        names = {n for p in r["pairs"] for n in (p["a"], p["b"])} | {n for b in r["shared_blocks"] for n in b["skills"]}
        self.assertNotIn("the-one-skill", names)
        self.assertNotIn("git-release", names)

    def test_trigger_overlap_needs_a_stated_boundary(self) -> None:
        p = self.pair(self.ctl.overlap(), "csv-inspector", "csv-summary")
        self.assertGreaterEqual(p["triggers"], 0.30)
        self.assertFalse(p["boundary_stated"])
        self.assertIn("add a 'Do not use when", p["verdict"])
        desc, body = self.ROSTER["csv-inspector"]
        self.write(self.root / "csv-inspector", "csv-inspector",
                   desc + " Do not use for totals or averages (use csv-summary).", body)
        p = self.pair(self.ctl.overlap(), "csv-inspector", "csv-summary")
        self.assertTrue(p["boundary_stated"])
        self.assertIn("boundary stated", p["verdict"])

    def test_a_name_in_the_trigger_sentence_is_not_a_boundary(self) -> None:
        p = self.pair(self.ctl.overlap(also=[self.builtin]), "proposal-deck", "pptx")
        self.assertIsNotNone(p)
        self.assertFalse(p["boundary_stated"])  # "as PPTX" says what it makes, not where to go instead
        self.assertEqual(p["readonly"], ["pptx"])
        self.assertIn("never change pptx", p["verdict"])

    def test_candidate_draft_is_checked_before_it_is_proposed(self) -> None:
        d = self.ctl.new("csv-stats")
        (d / "SKILL.md").write_text(skill_md(
            "csv-stats", "Compute averages and totals per column of CSV data files. Use when the user shares a CSV file.",
            "1. Load the whole file, group by the category column if there is one, and compute totals.\n"))
        r = self.ctl.overlap(candidate="csv-stats")
        self.assertTrue(r["pairs"])
        self.assertTrue(all("csv-stats" in (p["a"], p["b"]) for p in r["pairs"]))
        self.assertIn("same job twice", self.pair(r, "csv-stats", "csv-summary")["verdict"])
        self.assertTrue(all("csv-stats" in b["skills"] for b in r["shared_blocks"]))
        with self.assertRaises(Refused):
            self.ctl.overlap(candidate="no-such-skill")

    def test_draft_of_an_installed_skill_replaces_it(self) -> None:
        d = self.ctl.draft("timeline-slides")
        desc, body = self.ROSTER["timeline-slides"]
        (d / "SKILL.md").write_text(skill_md("timeline-slides", desc, body.replace(BRAND, "Follow the brand rules.\n")))
        r = self.ctl.overlap(candidate="timeline-slides")
        self.assertFalse(r["shared_blocks"])  # the draft no longer repeats the policy
        self.assertFalse(r["shadowed"])

    def test_same_name_in_two_folders_is_reported(self) -> None:
        personal = self.tmp / "personal"
        self.write(personal / "git-release", "git-release", "Release things. Use when shipping.", "")
        r = self.ctl.overlap(also=[personal, self.builtin])
        self.assertIn("git-release", r["shadowed"])

    def test_cli_overlap(self) -> None:
        args = ["--root", str(self.root)]
        self.assertEqual(skillctl.main(args + ["overlap"]), 0)
        self.assertEqual(skillctl.main(args + ["overlap", "--json", "--also", str(self.builtin)]), 0)
        self.assertEqual(skillctl.main(args + ["overlap", "--candidate", str(self.builtin / "pptx")]), 0)
        self.assertEqual(skillctl.main(args + ["overlap", "--candidate", "missing"]), 1)
        self.assertFalse(self.ctl.store.exists())  # overlap only reads: not even the store is created


class StructureTest(unittest.TestCase):
    """`list` flags skills whose files don't fit together."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "skills"
        self.root.mkdir()
        self.ctl = SkillCtl(self.root)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def make(self, name: str, body: str, files: dict[str, str] | None = None, desc: str | None = None) -> None:
        d = self.root / name
        d.mkdir()
        (d / "SKILL.md").write_text(skill_md(name, desc or f"Does {name}. Use when asked.", body))
        for rel, text in (files or {}).items():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            (d / rel).write_text(text)

    def issues(self, name: str) -> list[str]:
        return next(r for r in self.ctl.roster() if r["name"] == name)["issues"]

    def test_well_formed_skill_with_a_helper_script_is_clean(self) -> None:
        self.make("tidy", "1. Run `python3 scripts/main.py <file>`; it prints a table.\n"
                  "2. See references/format.md for the layout.\n", {
                      "scripts/main.py": "import helper\nprint(helper.go())\n",
                      "scripts/helper.py": "def go():\n    return 1\n",
                      "references/format.md": "Columns: name, type.\n"})
        self.assertEqual(self.issues("tidy"), [])

    def test_template_left_in(self) -> None:
        d = self.ctl.new("fresh")
        shutil.copytree(d, self.root / "fresh")
        self.assertIn("template placeholders left in SKILL.md", self.issues("fresh"))

    def test_broken_orphan_unrunnable_and_absolute(self) -> None:
        self.make("messy", "1. Read references/missing.md.\n2. Then use scripts/convert.py on the file.\n"
                  "3. Output goes to /home/alice/out.csv.\n", {
                      "scripts/convert.py": "print(1)\n", "references/unused.md": "Nobody reads this.\n"},
                  desc="x " * 600 + "Use when asked.")
        got = "\n".join(self.issues("messy"))
        self.assertIn("points to `references/missing.md`, which doesn't exist", got)
        self.assertIn("`references/unused.md` is never mentioned", got)
        self.assertIn("`scripts/convert.py` has no line saying how to run it", got)
        self.assertIn("absolute path", got)
        self.assertIn("characters (> 1024)", got)

    def test_wildcards_and_agentspace_are_not_broken_links(self) -> None:
        self.make("calm", "Never edit `references/readonly-*.md`. Notes go in references/agentspace/notes.md.\n")
        self.assertEqual(self.issues("calm"), [])


class ScriptOverlapTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "skills"
        parser = "import csv\nimport sys\n\n# read rows\ndef rows(path):\n    with open(path) as f:\n" \
                 "        return list(csv.reader(f))\n\nfor r in rows(sys.argv[1]):\n    print(','.join(r))\n"
        for name, task in (("sales-report", "Write a sales report"), ("inventory-audit", "Audit warehouse stock")):
            d = self.root / name
            (d / "scripts").mkdir(parents=True)
            (d / "SKILL.md").write_text(skill_md(name, f"{task}. Use when asked.", "Run `python3 scripts/rows.py`.\n"))
            (d / "scripts" / "rows.py").write_text(parser if name == "sales-report"
                                                   else "# a copy\n" + parser.replace("    ", "  "))
        self.ctl = SkillCtl(self.root)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def test_same_script_in_two_skills(self) -> None:
        r = self.ctl.overlap()
        self.assertEqual(len(r["shared_scripts"]), 1)
        s = r["shared_scripts"][0]
        self.assertEqual({s["a"], s["b"]}, {"sales-report", "inventory-audit"})
        self.assertTrue(s["identical"])  # comments and indentation don't count
        self.assertIn("SCRIPT", skillctl._overlap.report(r))


class PublishedUpgradeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "skills"
        self.root.mkdir()
        self.pub = self.tmp / "pub" / "pdf"
        self.pub.mkdir(parents=True)
        (self.pub / "SKILL.md").write_text(skill_md("pdf", "Work with PDFs. Use when a PDF is involved.",
                                                    "1. Extract text.\n2. Keep page order.\n"))
        self.ctl = SkillCtl(self.root)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def test_adapted_skill_takes_publisher_updates_and_keeps_tweaks(self) -> None:
        with self.assertRaises(Refused):
            self.ctl.new("pdf", None, published=True)
        self.ctl.new("pdf", self.pub, published=True)
        self.ctl.apply("pdf")                                   # as published
        d = self.ctl.draft("pdf")
        (d / "SKILL.md").write_text((d / "SKILL.md").read_text() + "3. Dates as YYYY-MM-DD.\n")
        self.ctl.apply("pdf")                                   # with the user's tweak
        (self.pub / "SKILL.md").write_text((self.pub / "SKILL.md").read_text().replace(
            "1. Extract text.", "1. Extract text and tables."))  # the publisher's next release
        r = self.ctl.upgrade("pdf", self.pub)
        self.assertFalse(r["conflicts"])
        merged = (Path(r["draft"]) / "SKILL.md").read_text()
        self.assertIn("1. Extract text and tables.", merged)
        self.assertIn("3. Dates as YYYY-MM-DD.", merged)


class CaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "skills"
        d = self.root / "csv-count"
        (d / "scripts").mkdir(parents=True)
        (d / "SKILL.md").write_text(skill_md("csv-count", "Count CSV rows. Use when asked.",
                                             "Run `python3 scripts/count.py <file>`.\n"))
        (d / "scripts" / "count.py").write_text(
            "import sys\nrows = open(sys.argv[1]).read().splitlines()\nprint(f'rows: {len(rows) - 1}')\n")
        self.data = self.tmp / "data.csv"
        self.data.write_text("a,b\n1,2\n3,4\n")
        self.ctl = SkillCtl(self.root)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def test_recorded_case_catches_a_regression_in_a_draft(self) -> None:
        run = f"{sys.executable} {{skill}}/scripts/count.py data.csv"
        self.ctl.case_add("csv-count", "header-not-counted", "How many rows?", ["the header is not a row"],
                          [self.data], run, record=True)
        self.ctl.case_add("csv-count", "plain-answer", "How many rows?", ["answers with one number"])
        self.assertEqual(self.ctl.cases("csv-count")["header-not-counted"]["stdout"], "rows: 2\n")
        rows = {r["case"]: r["result"] for r in self.ctl.case_run("csv-count")}
        self.assertEqual(rows, {"header-not-counted": "pass", "plain-answer": "check by hand"})
        d = self.ctl.draft("csv-count")
        (d / "scripts" / "count.py").write_text(
            "import sys\nprint(f'rows: {len(open(sys.argv[1]).read().splitlines())}')\n")
        bad = next(r for r in self.ctl.case_run("csv-count") if r["case"] == "header-not-counted")
        self.assertEqual(bad["result"], "FAIL")
        self.assertIn("rows: 3", bad["detail"])
        ok = next(r for r in self.ctl.case_run("csv-count", installed=True) if r["case"] == "header-not-counted")
        self.assertEqual(ok["result"], "pass")
        self.assertEqual(self.ctl.status(), [("csv-count", "original (draft in progress)")])  # cases aren't a skill
        args = ["--root", str(self.root)]
        self.assertEqual(skillctl.main(args + ["case", "run", "csv-count"]), 1)
        self.assertEqual(skillctl.main(args + ["case", "list", "csv-count"]), 0)
        self.ctl.case_remove("csv-count", "plain-answer")
        self.assertEqual(list(self.ctl.cases("csv-count")), ["header-not-counted"])

    def test_case_refusals(self) -> None:
        with self.assertRaises(Refused):
            self.ctl.case_add("csv-count", "x", "p")  # no expectation, no command
        with self.assertRaises(Refused):
            self.ctl.case_add("csv-count", "x", "p", ["e"], record=True)  # record needs run
        with self.assertRaises(Refused):
            self.ctl.case_add("csv-count", "x", "p", ["e"], run=f"{sys.executable} -c 'import sys; sys.exit(3)'",
                              record=True)
        self.assertEqual(self.ctl.cases("csv-count"), {})  # nothing half-saved


class UsageTest(unittest.TestCase):
    def test_counts_skill_calls_slash_commands_and_reads(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            proj = tmp / "projects" / "p1"
            proj.mkdir(parents=True)
            lines = [
                {"timestamp": "2026-10-01T10:00:00Z", "message": {"content": [
                    {"type": "tool_use", "name": "Skill", "input": {"skill": "csv-inspector"}}]}},
                {"timestamp": "2026-11-02T10:00:00Z", "message": {"content": [
                    {"type": "tool_use", "name": "Skill", "input": {"skill": "anthropic-skills:pdf"}}]}},
                {"timestamp": "2026-11-03T10:00:00Z", "message": {"content": [
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "/x/.claude/skills/csv-inspector/SKILL.md"}}]}},
                {"timestamp": "2026-11-04T10:00:00Z", "message": {"content": "<command-name>/git-release</command-name>"}},
                "not json at all",
            ]
            (proj / "s.jsonl").write_text("\n".join(l if isinstance(l, str) else json.dumps(l) for l in lines))
            used = SkillCtl.usage(tmp / "projects")
            self.assertEqual(used["csv-inspector"], {"uses": 2, "last": "2026-11-03"})
            self.assertEqual(used["pdf"]["uses"], 1)
            self.assertEqual(used["git-release"]["last"], "2026-11-04")
            root = tmp / "skills"
            (root / "csv-inspector").mkdir(parents=True)
            (root / "csv-inspector" / "SKILL.md").write_text(SKILL)
            self.assertEqual(skillctl.main(["--root", str(root), "usage", "--transcripts", str(tmp / "projects")]), 0)
            with self.assertRaises(Refused):
                SkillCtl.usage(tmp / "nope")
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
