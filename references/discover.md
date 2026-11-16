# Verified Skill Discovery & Authoring (`discover`)

Use this workflow when the user's task has no matching installed skill, when a multi-step workflow repeats across sessions, or when the user asks to find/create a skill.

## 1. Registry-First Lookup

Always check `registry.json` before drafting a new skill from scratch:
1. Read `registry.json` (locally or via web browsing on Gemini Web from `raw.githubusercontent.com/mtfuller/the-one-skill/main/registry.json`).
2. Match the user's task domain and keywords against each entry's `name`, `description`, and `tags`.
3. Verify the candidate entry specifies an **immutable commit SHA or release tag** (`commit_sha`) and a 64-character `sha256` digest. Reject any entry pointing to a floating branch (`main`, `master`, `HEAD`, `latest`).

## 2. Stage & Deterministically Verify (`verify_hash.py` Gate)

When a candidate matches in `registry.json`:
1. **Fetch Raw Files:**
   - **Claude Code / Codex:** Fetch the pinned commit archive or raw files listed in the registry entry's `files` manifest at `commit_sha`.
   - **Gemini Web:** Because the Python VM has no outbound internet, use Gemini's built-in web browsing capability to read the pinned raw URLs (`https://raw.githubusercontent.com/<repo>/<commit_sha>/<path>`) and write them into a temporary staging folder inside the sandbox (e.g., `/tmp/staged-skill/<skill-name>/`).
2. **Run Deterministic SHA-256 Verification:**
   ```bash
   python3 scripts/verify_hash.py <staged_dir> <expected_sha256>
   ```
   - **Hard Gate:** `verify_hash.py` **must** print `PASS: <sha256>` and exit with code `0`. If it prints `FAIL`, abort installation immediately, delete the staging directory, and alert the user of a hash mismatch.
3. **Run Security & Lint Gate:**
   ```bash
   python3 scripts/lint_skills.py <staged_dir> --security-policy config/security-policy.json
   ```
   - Blocks prompt-injection overrides (`SEC-001`), network exfiltration (`SEC-002`), credential harvesting (`SEC-003`), opaque `eval`/`exec`/`base64` payloads (`SEC-004`), and unauthorized ignore-marker tampering (`SEC-005`).

## 3. User Approval & Installation

1. Present a concise discovery card to the user:
   - **Skill Name & Source:** `<name>` (`<repo>@<commit_sha>`)
   - **Integrity & Security:** `verify_hash.py: PASS` · `security-policy.json: PASS` · Token count (`<= 800`)
   - **Consent Option:** Ask if the user wants to install with `<!-- the-one-skill:opt-in -->` (recommended) or vanilla.
2. Upon approval, install the skill into the host's skill location (see `vendors/<host>.md`).

## 4. Fallback: Authoring a New Skill from Template

If no suitable skill exists in `registry.json`:
1. Copy `templates/skill-template.md` as the starting scaffold.
2. Fill in YAML frontmatter (`name`, `description`), crisp `"Use when"` / `"Do not use when"` boundaries (orthogonal to existing installed skills), and a concise workflow under **800 tokens**.
3. Place any detailed domain tables in `references/` and pure Python 3 stdlib helpers in `scripts/`.
4. Run `python3 scripts/lint_skills.py` on the staged draft, present the full preview to the user for approval, and install.
