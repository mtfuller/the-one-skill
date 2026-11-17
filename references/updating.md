# Updating the-one-skill

Use this when the user gives you a new release of the-one-skill and asks you to update yourself: an unpacked folder, a zip, or a `the-one-skill.bundle.md` file. The update merges the release into the installed skill. Your agentspace and the user's local improvements stay. Only you change the core files.

## Steps
1. **Get the release as files.**
   - Folder: use it.
   - Zip: unpack it if you can run code; otherwise ask for the bundle file instead.
   - Bundle: run `python3 scripts/bundle.py unpack <bundle> <folder>` if you can run code. Otherwise read the files from the bundle directly: each one sits between `=== FILE: <path> ===` and `=== END FILE: <path> ===`.
2. **Check it.** Its `SKILL.md` must have `name: the-one-skill`. Its `VERSION.md` must be newer than yours, unless the user asks for an older one. Read every file, as for any outside skill (policy invariant 11), and read its `CHANGELOG.md`.
3. **Merge three ways:**
   - **Base:** the release installed last. On strategy A the store tracks it. On other hosts it is the original you kept, unless the adapter records a later release.
   - **Yours:** the installed copy.
   - **Theirs:** the new release.

   How each file is merged:
   - **The release's changes go in.**
   - **The user's local changes stay** (anything that differs from the base).
   - **`references/agentspace/` is kept exactly as installed**, including `index.md`.
   - **Read-only files:** taken exactly as published, or kept if the release didn't change them. If the user hand-edited one and the release changed it too, stop: that is theirs to reconcile, by hand.
   - **Both changed the same lines:** resolve it yourself only when the intent is clear (for example, the release reworded a line that the user tweaked for the same reason). Otherwise, name it in your message.

   A release is a **package**: `SKILL.md`, `README.md`, `CHANGELOG.md`, `VERSION.md`, `LICENSE.md`, `references/`, and `scripts/*.py`. Files outside it (tests, evals, CI, your notes) aren't in a release, so leave them as installed and never treat them as removed.

   On strategy A, run `skillctl.py upgrade the-one-skill --from <folder> --keep references/agentspace`. It does this merge into a draft and lists what came from where. Conflicts appear in the draft as `<<<<<<< yours (installed)` / `>>>>>>> new release` blocks. Edit the draft to resolve them, never the installed files.
4. **Tell the user in a few plain lines:** the version change, what's new (from the changelog, in plain words), which of their own improvements stay, anything you couldn't merge, and any change to the read-only policy, called out on its own line. End with one yes. Show the full diff if they ask.
5. **Apply after the yes**, through the adapter's mechanism, as one reversible change. The previous version stays kept, so "undo the update" works (`use the-one-skill previous` on strategy A).
6. **Check:** every agentspace file is still there. If `scripts/` changed and you can run code, run the release's tests now. If they fail, undo the update at once and say so.
7. **Adapters:** if the release changed the adapter template or framework (`references/building-adapters.md`), offer to refresh your adapter in the same message as the update, or right after it.

## Host notes
- **Twin hosts (for example Gemini):** update `the-one-skill-tuned` with the **whole merged folder** in one call, never `SKILL.md` content alone, which drops the other files. Then list the skill's files to confirm that agentspace survived. Record the installed release version in the adapter, so the next update knows its base.
- **Hosts that only accept uploads by the user:** give the user the merged files (or a bundle made with `bundle.py pack`) and tell them where to upload them. Remind them that the bundle never includes agentspace, so the merged folder you hand over must keep the agentspace files.
