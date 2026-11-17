# Undoing Changes

Undo exactly as much as the user asked for, never more. Everything is kept, so an undo can be undone too. The same rules apply as for any change: say in plain words what will come back and what will go away, get one yes, verify, and report in one line.

## How much to undo
- **One rule or one change:** step that skill back to its previous version, or apply a new change that removes just that part. Never revert the whole skill for this: that would also undo every later change, including the-one-skill's own setup. To find the change, use `history <skill>`, and compare kept versions with `diff` if needed. Prefer, in this order:
  1. step that skill back
  2. a new change that removes just that rule
  3. revert the whole skill to its original, only if nothing else depends on it
- **One skill:** put its original back exactly as it was (`use <skill> original`). The improved versions are kept, so they can come back.
- **A multi-skill change** (a merge, rename, or install of several skills): undo its change set (below).
- **Everything:** back to vanilla (below).
- **Promise only what is kept.** Check which versions actually exist (on strategy A, `history <skill>`) before telling the user they can get one back.
- **Hand edits:** if a skill was edited outside the-one-skill, `use` refuses. Ask whether to keep those edits (draft from them and apply) or discard them.

## Change sets
A change set groups the steps of one multi-skill change so it can be undone in one step. The tool keeps the record, outside the skills. Never keep a hand-written log for this.

- **Strategy A:** give every step the same `--set <name>` (and one `--note "<why>"`), for example `apply proposal-deck --set merge-proposal-decks --note "4 PPTX skills overlapped"`, then `retire pptx-timeline-slides --set merge-proposal-decks`. `sets` lists them.
- **Undo:** `undo-set <name>` lists the reverse steps, newest first, and changes nothing. Tell the user in plain words what will come back and what will go away, then run `undo-set <name> --apply` after a yes. It refuses if any skill changed after the set or a needed version is no longer kept. In that case, explain which and propose the remaining steps one by one.
- **Other strategies:** there is no store to record in. List the exact reverse steps in your reply when the change is applied, and tell the user that this list is the only record.
- **Undoing one rule or one change:** find it with `history <skill>` (and `diff` against kept versions), then pick the smallest undo, in this order:
  1. step that skill back
  2. a new change that removes just that rule
  3. revert the whole skill to its original, only if nothing else depends on it

## Back to vanilla
Use this when the user wants every skill as it was before the-one-skill changed anything.

1. **Take an inventory:**
   - skills with a kept original that are not currently on it
   - retired skills
   - skills the-one-skill created or installed (`status` shows "created")
   - skills edited by hand
2. **Give a short table** (skill · now · after) in plain words, covering:
   - put each skill back on its original
   - restore each retired skill
   - retire each skill the-one-skill created or installed
   - **ask** about hand-edited skills, because their edits are the user's own work
   - leave untouched any skill the-one-skill never changed
3. **Revert the-one-skill last**, as its own decision. Its original has no adapter or notes, so reverting it means the next session starts from a fresh install. Offer to keep the-one-skill as it is.
4. **Apply as one change set** and verify every skill. Nothing is deleted, so every tuned version can still be switched back in.
