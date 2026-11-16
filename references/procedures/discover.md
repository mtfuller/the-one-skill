# Procedure: Trusted Skill Discovery (`discover`)

Use this workflow when the user's task has no matching installed skill, when a multi-step workflow repeats across sessions, or when the user asks to find or create a skill.

## 1. Check Trusted Skill Sources First

Rather than maintaining a fragile custom hash index, `the-one-skill` discovers upstream skills from **verified official organization catalogs** defined in `config/trusted-sources.json`:
- **Anthropic Official Skills:** `anthropics/skills` (`https://github.com/anthropics/skills`)
- **OpenAI Official Skills:** `openai/skills` (`https://github.com/openai/skills`)
- **Google Gemini Official Skills:** `google-gemini/gemini-skills` (`https://github.com/google-gemini/gemini-skills`)

### Lookup Steps
1. Read `config/trusted-sources.json` to get the allowed upstream repositories and URL prefixes.
2. Search or browse the trusted source catalogs for a skill matching the user's task domain:
   - **Claude Code / Codex:** Use git/GitHub CLI or web search restricted to the trusted repositories in `config/trusted-sources.json`.
   - **Gemini Web:** Use Gemini's built-in web browsing tool to inspect the trusted repository directories (`github.com/anthropics/skills`, `github.com/openai/skills`, `github.com/google-gemini/gemini-skills`).
3. Verify the candidate URL matches an allowed prefix in `config/trusted-sources.json` via:
   ```bash
   python3 scripts/lint_skills.py --check-source-url <candidate_url>
   ```

## 2. Stage & Run Security / Lint Gates

When a candidate skill is found in a trusted source:
1. **Stage Candidate Files:** Write the fetched `SKILL.md` (and any `references/` or `scripts/`) into a temporary staging directory (e.g., `/tmp/staged-skill/<skill-name>/`).
2. **Run Deterministic Lint & Security Scan:**
   ```bash
   python3 scripts/lint_skills.py <staged_dir> --security-policy config/security-policy.json
   ```
   - Blocks prompt-injection overrides (`SEC-001`), network exfiltration (`SEC-002`), credential harvesting (`SEC-003`), opaque `eval`/`exec`/`base64` payloads (`SEC-004`), and unauthorized ignore-marker tampering (`SEC-005`).
   - Checks whether the upstream skill needs tailoring to fit the **800-token ceiling** or explicit `"Use when / Do not use when"` boundaries before installation.

## 3. User Approval & Installation

1. Present a concise discovery card to the user:
   - **Skill Name & Trusted Source:** `<name>` (`<provider>: <repository>`)
   - **Security & Lint Status:** `security-policy.json: PASS` · Token count (`<= 800`)
   - **Consent Option:** Ask if the user wants to install with `<!-- the-one-skill:opt-in -->` (recommended) or vanilla.
2. Upon approval, install the skill into the host's skill location (see `vendors/<host>.md`).

## 4. Fallback: Authoring a New Skill

If no matching skill exists in the trusted catalogs, read `references/skill-creation/authoring-guide.md` to design and scaffold a tailored skill from `templates/skill-template.md`.
