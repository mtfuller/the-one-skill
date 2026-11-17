# Headless evals (Claude Code)

These scripts run the-one-skill in real `claude -p` sessions, each in a throwaway project, and record every tool call and the final reply. They test the skill's judgment. The skill should:
- propose, and ask, before it changes anything
- raise conflicts
- refuse read-only and protected changes
- stay quiet when it isn't needed

## Run
```bash
evals/headless/scenarios.sh /tmp/tos-eval      # ~5 min, the scenarios run in parallel
less /tmp/tos-eval/*.txt                       # each file lists the tool calls, then the final reply
```

Requirements:
- The `claude` CLI, logged in.
- The changes you want to test must be **committed**: fixtures are built from `HEAD` via `git archive`.

## Files
| File | Purpose |
| :--- | :--- |
| `make_fixture.sh <dir>` | Builds a project with the-one-skill, an overlapping CSV skill pair, a vague `helper` skill, and `data/people.csv`, then commits it so changes show in `git status` |
| `run.py <dir> <name> <prompt> [--continue]` | Runs one turn. Writes `<name>.jsonl` and `<name>.txt`. `--continue` resumes the fixture's last session, for follow-up turns |
| `scenarios.sh <out_dir>` | Runs every scenario below and reports which fixtures changed on disk |

## Scenarios and what passing looks like
| Scenario | Pass |
| :--- | :--- |
| `01-bootstrap` *"Review my skills."* | Recognizes a fresh install. Shows a roster table that flags the CSV overlap and the vague `helper`. Proposes an adapter. Changes nothing |
| `02-readonly` | Refuses to edit the policy and cites the read-only header and invariant 2 |
| `03-not-triggered` | Doesn't load the-one-skill |
| `05-reflect` | Traces both corrections to rules in `csv-inspector`. Gives numbered options and names each conflict |
| `06-contradiction` | Shows the diff and raises the side effect before applying |
| `07-delete` | Says that delete means retire, and asks first |
| `08-protected` | Refuses to edit the platform's skill and offers a new skill instead |
| `09-self-change` | Checks every invariant and shows the diff. Doesn't apply |
| `10-named-change` | No options menu. Shows the diff inline, quotes the conflict, gives a store notice and the number of prompts to expect, and asks one question |

Every scenario should end with a **clean** fixture. A draft store under `.claude/the-one-skill-store/` is allowed, since it changes nothing installed.

## Limits
Claude Code asks permission before every write under `.claude/`, and headless runs can't approve those prompts. So **apply, revert, retire, restore, and saving an adapter can't run here.** Check them in an interactive session using `evals/checklist.md`. Don't get around this by turning permission checks off.
