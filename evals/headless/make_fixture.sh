#!/bin/bash
# Usage: make_fixture.sh <dir>
# Builds a throwaway project: the committed the-one-skill (HEAD) plus three test skills
# (csv-inspector, csv-analyzer that overlaps it, and a vague helper) under <dir>/.claude/skills.
set -euo pipefail
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
D=$1
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
cd "$D" && git init -q && git add -A && git -c user.name=eval -c user.email=eval@example.invalid commit -qm fixture
