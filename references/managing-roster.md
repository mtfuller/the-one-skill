# Managing the Skill Roster

The roster is every skill available on the host. All roster changes follow the same rules as improvements: say in plain language what will change, get one yes, verify, and keep it reversible. Show diffs and exact steps only when the user asks. The adapter says how each operation is done on this host. On strategy A, the `skillctl.py` commands are listed after each operation.

## Keep skills orthogonal
**Every job and every policy has exactly one owner.** Two skills overlap when they answer the same requests (triggers) *or* carry the same procedure (how the work is done: steps, rules, house style, checklists). Both kinds count. Three deck skills that each repeat the same brand rules are one policy with three copies, even though nobody would ask for them at the same moment: the copies drift apart, and a fix lands in one and not the others.

**Check with `overlap`, then read.** On strategy A, `overlap` compares every pair of skills on both dimensions and lists instruction blocks repeated across skills. Pass `--also <folder>` for each other skills folder the adapter lists (personal, plugin, built-in), which are compared but never changed. Pass `--candidate <skill>` to check a draft (from `new` or `draft`) or a downloaded folder before proposing it. Its scores are evidence, not decisions: read the skills involved before you propose anything. On other strategies, compare descriptions and bodies by reading them.

What each finding means, and what to propose:

| Finding | Meaning | Propose |
| :--- | :--- | :--- |
| **Triggers overlap**, no boundary | Both would fire on the same request | Sharpen each description. The narrower one gets "Do not use when … (use `<other>`)" |
| **Triggers overlap**, boundary stated | Already handed off | Nothing, unless the boundary is wrong |
| **Same job twice** (triggers and procedure) | Duplicate skills | Merge (below) |
| **Same procedure, different triggers** | A shared policy with several copies | Give it one owner (below) |
| **Policy repeated in 3+ skills** | The strongest signal | Always propose one owner |
| **Same name in two places** | One shadows the other | Rename or retire one; say which the host loads |
| **Overlap with a protected skill** | Someone else owns that ground | Never change the protected skill. The user's skill defers to it or says how it differs |

### Give a shared procedure one owner
Pick the smallest change that leaves one copy:
1. **Merge** when the skills are really one job with variants (the variants become sections or reference files of one skill).
2. **Extract** when the jobs are distinct but share a policy. Create one skill that owns the policy, named for it (for example `brand-style`), with a description that triggers on the policy's subject ("Use when producing any branded document, deck, or slide"). Replace each copy with one line that defers to it ("Follow brand-style for fonts, colours, and logo."), and keep only what is truly specific to each skill.
3. **Defer** when a protected or built-in skill already owns the policy: remove the copies and point to it.

Deferring only works if the host loads the owner when it's needed. Most hosts load skills by description, so the owner's description must trigger on the same work as the skills that defer to it. If the host can't do that, keep the copies and record them in the roster map as deliberate. Propose extraction as one change set: the new owner plus each slimmed skill.

## The roster map
`references/agentspace/roster.md` records who owns what, so overlap is checked against a decision instead of a guess. Create it with the first roster review or roster change, as part of that change's yes, and list it in the index ("Read when: before any roster change or review"). Keep it short:

```markdown
# Roster map
Purpose: which skill owns each job and each shared policy, and which overlaps are deliberate.
Updated: <YYYY-MM-DD>

## Skills
| Skill | Owns (job) | Hands off to | Last used |
| :--- | :--- | :--- | :--- |
| csv-inspector | Column types and missing values in a CSV | csv-summary (totals, averages) | 2026-11-03 |

## Shared policies
| Policy | Owner | Used by |
| :--- | :--- | :--- |
| Brand fonts, colours, logo | brand-style | proposal-deck, timeline-slides, board-update |

## Deliberate overlap
- <skills>: <why the user wants it kept>
```

- **Same change.** Every create, install, merge, split, rename, retire, or restore, and every improvement that changes what a skill owns, updates the map in the same change, under the same yes.
- **Respect decisions.** An overlap listed as deliberate is not proposed again unless the user asks.
- **Last used.** When you reflect on a session, set the date for each skill that did work in it. Do it in the same change as your other proposals, or as a small change of its own if nothing else changes. Where the host keeps session transcripts that you can read (on Claude Code, `usage` reads `~/.claude/projects`), use those instead. Ask the user once before reading them, and record their answer in the adapter.
- Leave the-one-skill out of the map.

## Review the roster
1. **Leave the-one-skill out.** It is the reviewer, not one of the skills under review. Don't list it in the table or propose changes to it, unless the user asks to review it or it clearly caused friction in this session (then one line at most). The same goes for its setup files.
2. List every other skill with its name, enabled state, source (the user's own, created by the-one-skill, installed from outside, or protected), and its managed state. On strategy A, `list --json` and `status` give you this, and `list` also flags structural problems. Read the roster map if there is one.
3. Check for:
   - **Overlap** in triggers or procedure, including with protected built-in skills (`overlap --also …`, then read).
   - **Vague triggers:** a description that never says when to use the skill. Propose a rewrite.
   - **Broken structure:** a missing `SKILL.md`, a frontmatter `name` that differs from the folder, an invalid name, or a `SKILL.md` over 500 lines (move detail into `references/`).
   - **Gaps:** a workflow from this or recent sessions that no skill covers. Offer to create one (below).
   - **Dead weight:** skills not used for 60 days or more (from `usage`, or the roster map's "Last used"), and skills the user says they no longer use. Never retire a skill just because it looks unused: list it and ask. Some skills are rare but important.
   - **Unpublished updates:** for skills installed from a publisher, whether a newer release exists, if the user wants that checked (see "Update a skill from its publisher").
4. Give a short table (skill · what's wrong · what you'd do), in plain words, and end with one question: do all, some, or none. Nothing changes until the user answers.

## Operations

| Operation | How (always with approval) | Strategy A |
| :--- | :--- | :--- |
| **Improve** | `references/improving.md`. | `draft` → edit → `overlap --candidate` → `apply` |
| **Create** | See below, and `references/writing-skills.md` for the files. | `new <name>` → write files → `list`, `overlap --candidate <name>`, `case run` → `apply` |
| **Find and install** | See below. | `overlap --candidate <folder>`, then `new <name> --from <folder> --published` |
| **Update from publisher** | See below. | `upgrade <name> --from <folder>` → `apply` |
| **Merge** | See below. | `new` or `draft`, then `retire` each |
| **Extract a shared policy** | See "Give a shared procedure one owner". | `new <owner>`, then `draft` each skill that defers |
| **Split** | Create the new skill, then improve the old one to narrow its scope and point to the new one. | `new`, then `draft` |
| **Rename** | Names are identities. Create the new name with the same files, then retire the old one. | `new --from`, then `retire` |
| **Retire** | Reversible removal. On strategy B, disable the skill. On C or D, tell the user how to do it. | `retire` |
| **Restore** | Bring a retired skill back. Refuse if the name is now taken by another skill. | `restore` |
| **Step back** | Undo the latest change to one skill but keep earlier ones (`references/undoing.md`). | `history`, `use previous` |
| **Back to vanilla** | `references/undoing.md`. | |

Run every operation that touches more than one skill (merge, extract, split, rename, back to vanilla, installing several skills) as one **change set** (`references/undoing.md`), so it can be undone in one step.

## Create a skill: start from the best verified work
Don't write from a blank page when Anthropic, OpenAI, or Google has already solved most of the job. A verified starting point gets the structure, edge cases, and scripts right the first time, so the user iterates less.

1. **Name the job and its boundaries.** One sentence: what the skill does, and what it does not. Check the roster map and run `overlap` against that sentence's neighbours. If an existing skill already owns the job, offer to improve it instead. If the job needs a policy another skill owns, the new skill defers to that owner.
2. **Look for a verified head start**, every time, before writing:
   - the verified-skills list (below), so you don't search for what you already found
   - skills already on the host, including protected and built-in ones. One may already cover the job, and then the answer is to use it, not to write another.
   - skills that Anthropic, OpenAI, or Google publish, from the same sources as "Find and install" (policy invariant 11).
   - if the host has a published skill-authoring skill (such as Anthropic's `skill-creator`), read it for how to structure the skill and write its description. It is protected: use its guidance, never change it.

   Read every file of the closest one to three candidates, and add what you found to the verified-skills list.
3. **Pick a start**, and say which in one line of your proposal:

   | Start | When | How |
   | :--- | :--- | :--- |
   | **Install** | A verified skill fits as is | "Find and install" below |
   | **Adapt** | A verified skill fits most of the job | Install it exactly as published, then apply the user's changes as a second version in the same change set. "Undo my tweaks" keeps the published skill, and later releases can still be merged |
   | **Borrow** | Verified skills solve parts of it | Write a new skill that takes their structure, steps, reference layout, or scripts. Keep the source's license terms, and record the source with `--note "<source> <version>"` |
   | **Scratch** | Nothing close exists | Write it, following the authoring guidance from step 2 |

4. **Draft the whole skill** following `references/writing-skills.md`. The description says what it does, "Use when …", and "Do not use when … (use `<neighbour>`)" for each neighbour from step 1. Policies another skill owns are deferred to, never copied. Fill the sections from the session that prompted the skill: the user's actual corrections are the best requirements. Put deterministic steps in scripts, tested on the session's real input.
5. **Check it** (writing-skills.md, "Before you propose"): the structure check is clean, `overlap --candidate <name>` is clean or every finding is explained in your proposal, and each correction from the session is saved as a case that passes.
6. **Propose in one message:** what the skill will do, where it started from, and what it hands off. Create it after a yes, update the roster map in the same change, and track it as created by the-one-skill, so going back to vanilla can find it. Show its files if asked.

## Find and install a skill from Anthropic, OpenAI, or Google
Use this when the user wants an existing skill rather than one written for them, when a gap is generic enough that someone has probably already solved it, or when "Create" finds a verified skill to install or adapt.

1. **Reflect first.** If the friction came from repeated corrections, name them. Say whether the fix could also be a small change to a skill the user already has. Offer both paths.
2. **Search only skills that Anthropic, OpenAI, or Google publish** (policy invariant 11):
   - their skill directories in their own products (Claude, ChatGPT, Gemini), counting only the skills the company itself publishes there
   - their official repositories, such as the `anthropics`, `openai`, `google`, and `google-gemini` organizations on GitHub

   Start from the verified-skills list (below). Search again for anything it doesn't cover, or where its entry is more than 90 days old.

   Check the publisher from where the skill actually lives (the organization or the directory's publisher field), never from what its name or description claims. No other source counts, even if the user names one or asks for more. If none of the three publishes a fitting skill, say so plainly, and offer to write one or to change a skill the user already has. If the user wants a skill from somewhere else, they can install it themselves, outside the-one-skill.
3. **Compare candidates against the user's actual corrections.** Use a table: which corrections each candidate fixes, which it doesn't, who publishes it, and when it was last updated. Be honest when nothing covers everything, and say what would close the gap (a small local addition, a hook, or a rule).
4. **Read before installing (policy invariant 11).** Read every file of the chosen skill. Summarize its instructions, scripts, network access, and anything it would run or install. Flag anything that reaches beyond its stated purpose. Run `overlap --candidate <folder>` and name any skill of the user's it would compete with or duplicate, with what you'd do about it (a boundary, or retiring the old one in the same change set).
5. **Install as a new skill** after a yes. Show the files if asked. Install through the host's own installer if it has one, or else as a created skill (strategy A: `new <name> --from <folder> --published`, then `apply <name> --note "<source> <version>"`). `--published` keeps that copy as the base for later updates from the publisher.
   - **Install it exactly as published first.** Any tweaks (the user's requests, a boundary for a neighbour, or removing something you flagged) go in afterwards as a separate change, under the same change set. Then the kept versions are "as published" and "with tweaks", so "undo my tweaks" leaves the published skill in place, and an update from the source can be compared with what was installed. One yes covers both steps.
6. **Verify.** Confirm the skill is listed and enabled. Update the roster map, and record the install in the verified-skills list. Tell the user it loads in a new session, and that retiring it undoes the install.

Never install a skill that Anthropic, OpenAI, or Google didn't publish. Never run a skill's scripts in order to evaluate it.

## The verified-skills list
`references/agentspace/verified-skills.md` remembers the skills from Anthropic, OpenAI, and Google that you have already read, so later sessions start from it instead of searching from nothing. Create it the first time you read a candidate, as part of that change's yes, and list it in the index ("Read when: before searching for, creating, or updating a skill").

```markdown
# Verified skills
Purpose: skills from Anthropic, OpenAI, or Google already read, and what was decided.
Updated: <YYYY-MM-DD>

| Skill | Publisher | Where (link and version or commit) | What it does | Checked | Decision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| pdf | Anthropic | github.com/anthropics/skills/... @ <commit> | Read, fill, merge PDFs | 2026-11-17 | installed as `pdf`, with tweaks |
```

- Decisions are: installed, adapted, borrowed from (for which skill), or rejected (with why, in a few words).
- An entry is a pointer, not a copy. Read the skill again from its source before installing, adapting, or borrowing from it.
- Re-check an entry when it's more than 90 days old, or when the user asks for updates.
- It names only skills from the three publishers. The policy's source rule still decides what counts.

## Update a skill from its publisher
For a skill installed or adapted from a publisher, a newer release can be merged in. The publisher's changes go in, and the user's tweaks stay.

1. **Find the newer release** at the source recorded in the verified-skills list. Check only when the user asks, or when a review offers it and the user says yes. Don't check on your own each session.
2. **Read every file of the new release** (policy invariant 11), and its changelog if it has one. Check it is still from the same publisher.
3. **Merge.** On strategy A: `upgrade <name> --from <folder>`. It merges three ways against the version installed with `--published`: the publisher's changes go in, the user's tweaks stay, and lines both changed become conflict markers in the draft. Resolve them in the draft only when the intent is clear, otherwise name them. Then run `list`, `overlap --candidate <name>`, and `case run <name>`, as for any change.
4. **Tell the user in a few plain lines:** what's new, which of their tweaks stay, and anything that conflicts. One yes applies it. "Undo the update" is `use <name> previous`.
5. **Update** the verified-skills list (version, date) after applying.

A skill installed before `--published` existed has no recorded base. Its first upgrade treats every difference as a conflict to resolve. Say so in your proposal, then apply as above. Later upgrades merge cleanly.

## Merge several skills
1. **Read every skill involved, including its references.** Also list protected skills that cover the same ground (for example a built-in skill for the same file type). Protected skills are never merged. The merged skill should defer to them, or say how it differs from them.
2. **Find conflicts between the skills**, such as two different fonts or two different limits. `overlap`'s shared blocks show where they agree; read the rest for where they don't. Pick a default for each conflict and name it in your one message ("Arial everywhere, replacing the timeline skill's Calibri"). The user's yes covers it, or they say otherwise.
3. **Choose the target.** Improve one existing skill if its name and scope still fit. Otherwise create a new skill with a name that covers the whole job. Bring over every reference file that is still needed.
4. **Write a description that triggers on every request the old skills did**, plus "Do not use when" lines for anything a protected skill should handle.
5. **Propose it as one change set:** the new or changed skill, plus retiring each of the others, plus the roster map update. Apply every step under the same set name, and verify it. Undoing it means restoring each retired skill and retiring the new one (or stepping the target back), in reverse order.

## Rules
- **One owner per job and per policy.** Never add a rule to a skill when another skill owns that policy: change the owner, or defer to it.
- **Protected skills** (see the adapter) are never merged, renamed, retired, or edited. You can still flag their overlap with other skills and propose changes to the user's own skills instead.
- **Delete means retire.** If the user wants a skill permanently gone, retire it and tell them where the host lets them delete it. Never substitute an action without saying so.
- **One change at a time inside a change set.** Verify each step before starting the next, and stop if one fails. Report how far the set got and how to undo that part.
