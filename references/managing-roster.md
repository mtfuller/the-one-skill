# Managing the Skill Roster

The roster is every skill available on the host. All roster changes follow the same rules as improvements: propose first, show exactly what will change, wait for a yes, verify, and keep it reversible. The adapter says how each operation is done on this host.

## Review the roster
1. List every skill with its name, enabled state, source (the user's own, or protected), and whether the-one-skill manages it (`original`, `tuned`, `edited`). On strategy A, `skillctl.py list --json` reports this and flags structural problems.
2. Check for:
   - **Overlap:** two descriptions that would both trigger on the same request. Propose a merge, or sharpen each skill's "Use when / Do not use when".
   - **Vague triggers:** a description that never says when to use the skill. Propose a rewrite.
   - **Broken structure:** a missing `SKILL.md`, a frontmatter `name` that differs from the folder, an invalid name, or a `SKILL.md` over 500 lines (move detail into `references/`).
   - **Gaps:** a workflow from this or recent sessions that no skill covers.
   - **Dead weight:** skills the user says they no longer use.
3. Present a table (skill · finding · proposed action) followed by numbered options. Nothing changes until the user picks.

## Operations

| Operation | How (always with approval) |
| :--- | :--- |
| **Improve** | The Improve steps in `SKILL.md`. |
| **Create** | Check that the name is free. Show the full `SKILL.md` (and any reference files), then create it after approval. Nothing is overwritten, so no backup is needed. The skill's first later change goes through the normal draft flow. |
| **Merge A into B** | Improve B so it covers A, then retire A. Never delete. |
| **Split** | Create the new skill, then improve the old one to narrow its scope and point to the new one. |
| **Rename** | Names are identities. Create the new name with the same files, then retire the old one. |
| **Retire** | Reversible removal. A: `skillctl.py retire`. B: disable. C/D: tell the user how to do it themselves. |
| **Restore** | A: `skillctl.py restore`. B: enable. Refuse if the name is now taken by another skill. |

## Rules
- **Protected skills** (see the adapter) are never merged, renamed, retired, or edited. You can still flag their overlap with other skills and propose changes to the user's own skills instead.
- **Delete means retire.** If the user wants a skill permanently gone, retire it and tell them where the host lets them delete it. Never substitute an action without saying so.
- **One change at a time.** For multi-step operations (merge, rename), verify each step before starting the next, and stop if one fails.
