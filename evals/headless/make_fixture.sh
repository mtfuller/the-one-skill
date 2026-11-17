#!/bin/bash
# Usage: make_fixture.sh <dir> [profile]
# Builds a throwaway project: the committed the-one-skill (HEAD) plus three test skills
# (csv-inspector, csv-analyzer that overlaps it, and a vague helper) under <dir>/.claude/skills.
# Profiles stage a history with skillctl (the same steps an approved session would take):
#   fresh    (default) nothing else
#   adapter  a Claude Code adapter applied to the-one-skill (original kept)
#   pptx     adapter + four overlapping PPTX proposal skills with conflicting rules
#   used     adapter + csv-inspector tuned, helper retired, weekly-status-report created
#   rule     adapter, then a second change adding a heavy rule to the adapter
set -euo pipefail
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
D=$1
PROFILE=${2:-fresh}
rm -rf "$D"; mkdir -p "$D/.claude/skills"
git -C "$REPO" archive HEAD | tar -x -C "$D/.claude/skills" --one-top-level=the-one-skill
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
printf ".claude/the-one-skill-store/\n" > "$D/.gitignore"
commit() { (cd "$D" && git add -A && git -c user.name=eval -c user.email=eval@example.invalid commit -qm "$1" --allow-empty); }
cd "$D" && git init -q && commit fixture

[ "$PROFILE" = fresh ] && exit 0
C="python3 $K/the-one-skill/scripts/skillctl.py --root $K"
draft() { $C draft "$1" | sed -n 's/^Draft ready: //p'; }

DR=$(draft the-one-skill)
cat > "$DR/references/agentspace/claude-code.md" <<'A'
# Agentspace: Claude Code (project skills)
Slug: claude-code
Detect: Bash/Read/Edit/Skill tools; skills in <project>/.claude/skills
Verified: 2026-11-10
Strategy: A: originals kept in .claude/the-one-skill-store/ via scripts/skillctl.py

## Where skills live
- Project: .claude/skills/ ; store: .claude/the-one-skill-store/

## Operations
SKILLCTL = python3 .claude/skills/the-one-skill/scripts/skillctl.py --root .claude/skills
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
  sed -i 's/Present the summary as prose paragraphs./Present the summary as a Markdown table./' "$DR/SKILL.md"
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
*) echo "unknown profile: $PROFILE" >&2; exit 1 ;;
esac
commit "staged: $PROFILE"
