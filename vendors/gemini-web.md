# Host Adapter: Gemini Web (`gemini-web`)

This guide defines how `the-one-skill` operates inside **Gemini Web**.

## 1. Persistent Uploaded Skills & Memory Mirroring

- **Persistent Skill Updates:** Skills uploaded to Gemini Web persist across sessions and can be updated directly when the user approves a diff (`init`, `reflect`, `discover`, or `revert`).
- **Consent Mirroring in Memory:** While `<!-- the-one-skill:opt-in -->` and `<!-- the-one-skill:ignore -->` are written directly into each skill's `SKILL.md` as the source of truth, mirror the consent map in **Gemini Memory** (e.g., `the-one-skill roster: csv-inspector=opt-in, legacy-tax=ignore`). Checking Memory first avoids reading ignored or unrelated skill files on every turn.

## 2. Sandbox Constraints (Python Stdlib Only, No Outbound VM Network)

- **Pure Python 3 Standard Library:** The Gemini Web code execution environment only runs Python and has no outbound internet access from inside the VM. Never invoke `pip install`, shell network tools (`curl`, `wget`), or non-Python runtimes. All scripts in `scripts/` use pure Python 3 stdlib (`hashlib`, `difflib`, `json`, `re`, `pathlib`, `unittest`).
- **Two-Step Web Fetch + Sandbox Verification (`discover` & `export`):**
  1. Use Gemini Web's built-in **Web Browsing** tool to read `registry.json` and the candidate skill's commit-pinned raw files (`https://raw.githubusercontent.com/<owner>/<repo>/<commit_sha>/<path>`).
  2. Write those fetched file contents into a staging directory inside the Python sandbox (`/tmp/staged/<skill-name>/`) and run:
     ```bash
     python3 scripts/verify_hash.py /tmp/staged/<skill-name> <expected_sha256>
     python3 scripts/lint_skills.py /tmp/staged/<skill-name> --security-policy config/security-policy.json
     ```
  3. Only after `verify_hash.py` prints `PASS` and user approval is granted should you save/install the skill in Gemini Web.

## 3. Snapshots & Artifacts

- Save pre-patch snapshots to `artifacts/snapshots/<skill-name>.<timestamp>.bak.md` and expose patch exports (`artifacts/the-one-skill-changes.patch`) so the user can inspect or download them anytime.
