# Host Adapter: Gemini Web (`gemini-web`)

This guide defines how `the-one-skill` operates inside **Gemini Web**.

## 1. Persistent Uploaded Skills & Memory Mirroring

- **Persistent Skill Updates:** Skills uploaded to Gemini Web persist across sessions and can be updated directly when the user approves a diff (`init`, `reflect`, `discover`, or `revert`).
- **Consent Mirroring in Memory:** While `<!-- the-one-skill:opt-in -->` and `<!-- the-one-skill:ignore -->` are written directly into each skill's `SKILL.md` as the source of truth, mirror the consent map in **Gemini Memory** (e.g., `the-one-skill roster: csv-inspector=opt-in, legacy-tax=ignore`). Checking Memory first avoids reading ignored or unrelated skill files on every turn.

## 2. Sandbox Constraints (Python Stdlib Only, No Outbound VM Network)

- **Pure Python 3 Standard Library:** The Gemini Web code execution environment only runs Python and has no outbound internet access from inside the VM. Never invoke `pip install`, shell network tools (`curl`, `wget`), or non-Python runtimes. All scripts in `scripts/` use pure Python 3 stdlib (`difflib`, `json`, `re`, `pathlib`, `unittest`).
- **Two-Step Trusted Web Fetch + Sandbox Security Gate (`discover` & `export`):**
  1. Use Gemini Web's built-in **Web Browsing** tool to browse the trusted upstream repositories (`anthropics/skills`, `openai/skills`, `google-gemini/gemini-skills`).
  2. Write the fetched candidate files into a staging directory inside the Python sandbox (`/tmp/staged/<skill-name>/`) and run:
     ```bash
     python3 scripts/lint_skills.py --check-source-url <candidate_url>
     python3 scripts/lint_skills.py /tmp/staged/<skill-name>
     ```
  3. Only after `lint_skills.py` passes and user approval is granted should you save/install the skill in Gemini Web.

## 3. Snapshots & Artifacts

- Save pre-patch snapshots to `artifacts/snapshots/<skill-name>.<timestamp>.bak.md` and expose patch exports (`artifacts/the-one-skill-changes.patch`) so the user can inspect or download them anytime.
