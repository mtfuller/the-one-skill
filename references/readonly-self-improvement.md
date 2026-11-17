# Self-Improvement Policy (read-only)

> **This file is read-only.** the-one-skill never creates, edits, moves, renames, or deletes it, in any version and on any host, including inside a `-tuned` twin or a draft. Only the user changes it, by hand. If an approved change would need it edited, stop and tell the user.

This file defines how the-one-skill may change itself and what its agentspace files must guarantee. Everything else in the skill can evolve. These rules cannot.

## 1. What the skill is made of, and who may change it

| Tier | Paths | Changed by | How |
| :--- | :--- | :--- | :--- |
| Read-only | `references/readonly-*.md` | The user only, by hand | Not by the-one-skill |
| Core | `SKILL.md`, other `references/*.md`, `scripts/`, `tests/` | the-one-skill, with approval | Self-change procedure (§3) |
| Agentspace | Everything under `references/agentspace/`: host adapters plus any other files the agent creates to fit the user's needs | the-one-skill, with approval | `references/building-adapters.md`, saved through §3 |

The same rule applies to any file named `readonly-*` in **any** skill: the-one-skill never modifies it.

## 2. Invariants

Every version of the-one-skill, and every agentspace file, keeps all of these. An agentspace file may add rules or narrow what the skill does. It may never loosen an invariant. A change that removes or weakens one is refused even if the user asks for it. The user may make that change by hand.

1. **Originals are kept.** The first change to any skill keeps its original. The original is never edited and can always be restored. If a host cannot do this without help (for example, the user has to download a backup), the user is told before the first change and confirms.
2. **Nothing changes without approval.** Every create, edit, enable, disable, retire, and restore is described first in plain language (what will behave differently, and why) and waits for an explicit yes. One yes may cover everything in one request. The exact change (full diff or exact action) is shown whenever the user asks for it, before or after.
3. **Conflicts are raised.** A change that overrides a skill's existing rule says so plainly in the message the user approves. It is never applied silently.
4. **No substitution.** If an action is impossible, stop and say so. Never perform a different action in its place (for example, disabling a skill when asked to delete it).
5. **Verify, don't trust.** After every change, check the real result (list, status, read back) before reporting success. A host's description of its own abilities is not evidence.
6. **Protected things stay untouched.** Skills, connectors, and plugins that an adapter marks as protected, or that someone else manages (an organization, a plugin, the platform), are never modified. Propose a new skill instead.
7. **Read-only stays read-only.** This file and every `readonly-*` file.
8. **Probes are safe.** Learning what a host can do never puts a user's real skills at risk. Write abilities are tested only on a throwaway skill, and only with the user's permission.
9. **Agentspace holds no secrets.** Its files describe abilities, rules, and preferences. They contain no tokens or passwords, and only the personal details the user explicitly asked to keep.
10. **Nothing is deleted.** Retiring a skill is reversible. Permanent deletion is left to the user in the host's own settings.
11. **Outside skills are read before they are installed.** Every file of a skill from outside the user's system (a directory, marketplace, repository, or download) is read before it is installed. The user gets a summary of what it instructs, runs, and reaches over the network. A skill is installed only from a source the user approved, and its scripts are never run in order to evaluate it.

## 3. Changing the-one-skill (self-change procedure)

Do this only when the user asks, or approves an option from a reflection. Never as a side effect of other work.

1. **State the friction and the change**, in plain language, as you would for any improvement.
2. **Classify every touched file** by tier (§1). If a read-only file is touched, stop.
3. **Check the invariants.** For each one in §2, confirm the new version still keeps it. If you are not sure, assume it does not, and say so to the user.
4. **Apply through the adapter's reversible mechanism**, exactly as for any other skill. the-one-skill gets no shortcut. Describe the change in plain language and wait for a yes. Show the diff if the user asks.
5. **Scripts:** if `scripts/` changes, run `tests/` and apply only if they pass. If this host cannot run code, do not change `scripts/`.
6. **Size:** keep `SKILL.md` under 500 lines. Move detail into `references/`.
7. **Verify and report.** Tell the user the change takes effect in a new session, and that "revert" restores the previous version. Reverting the whole skill also reverts any agentspace files saved since then. Switching the tuned version back in restores them.

## 4. Good and bad self-changes

- **Good:** clearer triggers, fewer and plainer questions, new references for situations that keep coming up, sharper roster checks, adapter fixes when a host behaves differently from what was recorded, and new agentspace files that capture how this user works.
- **Never:** removing or loosening an approval step, widening what the skill may touch without the user, applying changes automatically, deleting user skills, or editing this file.
