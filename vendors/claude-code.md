# Host Adapter: Claude Code (`claude-code`)

This guide defines how `the-one-skill` operates inside **Claude Code**.

## 1. Skill Paths & Discovery Order

Claude Code loads skills from workspace and user directories:
- **Workspace Skills:** `.claude/skills/<skill-name>/SKILL.md`
- **User Global Skills:** `~/.claude/skills/<skill-name>/SKILL.md`

During `init` or Full-Roster Orthogonality Audits, scan the active workspace `.claude/skills/` directory first, and include `~/.claude/skills/` if the user requests a global roster audit.

## 2. Local Filesystem, Git & `CLAUDE.md` Integration

- **Diff-First & Snapshots:** Even when working inside a git-tracked repository, always write pre-patch snapshots to `artifacts/snapshots/<skill-name>.<timestamp>.bak.md` before applying an approved diff so `revert` works identically across git and non-git directories.
- **`CLAUDE.md` Boundary:** Keep project-specific build/test commands in `CLAUDE.md`, and reusable multi-step workflows in `.claude/skills/`. If `CLAUDE.md` accumulates repeatable workflow instructions that belong in a skill, `discover` can propose extracting them into a dedicated skill under **800 tokens**.
- **MCP Awareness:** If an installed skill relies on an MCP server tool, reference the exact MCP tool name in the skill's workflow section and keep bulky tool schema examples inside `<skill>/references/`.
