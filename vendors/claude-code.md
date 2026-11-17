# Host Adapter: Claude Code (`claude-code`)

This guide defines how `the-one-skill` operates inside **Claude Code**.

## 1. Skill Roots

Run `scripts/skillctl.py` with `--root` set to the folder holding the skill:
- **Project:** `.claude/skills/` → store defaults to `.claude/the-one-skill-store/`. Ask the user whether to commit or `.gitignore` the store.
- **Personal:** `~/.claude/skills/` → store defaults to `~/.claude/the-one-skill-store/`.
- **Not managed by `the-one-skill`:** plugin skills (`/plugin` enables, disables and uninstalls them), skills synced from claude.ai (`~/.claude/skills/synced/` is overwritten by sync; turn them off on claude.ai), and enterprise-managed skills. Report these to the user instead of refining them.

Precedence for the same name: enterprise > personal > project. Keep the working copy at the original's exact path so a same-named skill elsewhere cannot shadow it. Personal skills do not load in Cowork or cloud sessions.

## 2. How Disabling Works

- `skillctl.py` disables a version by moving it out of the skills root into the store. Claude Code watches `~/.claude/skills/` and `.claude/skills/`, so swaps take effect in the current session without a restart. If the `skills` folder did not exist when the session started, run `/reload-skills`.
- Do **not** use `skillOverrides` (`.claude/settings.local.json`) for swaps: it is keyed by skill name, so it cannot tell an original from its same-named working copy. It remains the right tool if the user wants a skill hidden without `the-one-skill` managing it (`"off"` hides it from Claude and the `/` menu).
- Do **not** add `disable-model-invocation` or `user-invocable` to an original's frontmatter: that edits the original.
- Content already loaded into the conversation stays until compaction, so after a revert start a fresh task before judging the restored skill.

## 3. `CLAUDE.md` & MCP

- **`CLAUDE.md` Boundary:** Keep project-specific build/test commands in `CLAUDE.md`, and reusable multi-step workflows in `.claude/skills/`. If `CLAUDE.md` accumulates repeatable workflow instructions, `discover` can propose extracting them into a skill under **800 tokens**.
- **MCP Awareness:** If a skill relies on an MCP server tool, reference the exact MCP tool name in the skill's workflow and keep bulky tool schema examples inside `<skill>/references/`.
