# Host Adapter: OpenAI Codex (`codex`)

This guide defines how `the-one-skill` operates inside **OpenAI Codex** (CLI and app).

## 1. Skill Roots

Codex discovers skills in:
- **Repository:** `.agents/skills/` in each directory from the working directory up to the repository root.
- **User:** `~/.agents/skills/`, plus the legacy `~/.codex/skills/` (or `$CODEX_HOME/skills`), still read for backward compatibility.
- **Admin:** `/etc/codex/skills/`, plus bundled system skills. Do not manage these; report them to the user.

Run `scripts/skillctl.py` with `--root` set to the folder holding the skill. The store defaults to a sibling, e.g. `~/.agents/the-one-skill-store/`. How Codex resolves two skills with the same name across roots is not clearly documented, so keep the working copy at the original's exact path and never leave two same-named skills installed.

Check `AGENTS.md` for instructions that overlap a skill's triggers during `status` or roster audits.

## 2. How Disabling Works

- `skillctl.py` disables a version by moving it out of the skills root into the store.
- Codex also supports per-path toggles in `~/.codex/config.toml` (`[[skills.config]]` with `path = "<abs path to SKILL.md>"` and `enabled = false`). `the-one-skill` does not use them for swaps, but if the user has one pointing at a managed skill's path, it applies to whichever version is installed there.
- **Restart Codex** after every `commit`, `undo`, `revert`, `reapply`, `install`, `retire`, or `unretire`. Tell the user each time.

## 3. Sandbox & Verification

- Run `python3 scripts/skillctl.py`, `python3 scripts/lint_skills.py`, and `python3 scripts/export_diff.py` directly in the Codex terminal. Swaps write outside the workspace when the root is `~/.agents/skills`, which may need the user's approval in Codex's sandbox.
- **Trusted Skill Sources:** When discovering skills (`references/discover.md`), verify candidate URLs (`python3 scripts/lint_skills.py --check-source-url <url>`) and lint the staged folder before installing.
