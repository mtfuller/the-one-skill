# Local State Export & PR Diff Workflow (`export`)

Use this workflow when the user wants to export local improvements made to `the-one-skill` (or a registry skill) and generate a clean, sanitized unified diff and pull request summary for `mtfuller/the-one-skill`.

## Step-by-Step Workflow

### 1. Stage Local State
Copy the current local/installed `the-one-skill` files into a temporary directory under `artifacts/local-export/` (excluding `.git/`, `__pycache__/`, `.DS_Store`, and `artifacts/snapshots/`).

### 2. Obtain Upstream Baseline
- **Claude Code / Codex:** Use a clean checkout of `mtfuller/the-one-skill` (`main`) or `git worktree` as `<upstream_dir>`.
- **Gemini Web:** Fetch the upstream baseline files from `https://raw.githubusercontent.com/mtfuller/the-one-skill/main/...` via web browsing and write them to `/tmp/upstream-the-one-skill/`.

### 3. Generate Unified Patch & PR Summary
Run the pure-Python stdlib diff exporter:

```bash
python3 scripts/export_diff.py <upstream_dir> <local_dir> artifacts/the-one-skill-changes.patch
```

`export_diff.py` performs three actions deterministically:
1. Compares all tracked files across `<upstream_dir>` and `<local_dir>` with normalized `\n` line endings.
2. Scans changed lines for accidental personal data leaks (emails, local home paths like `/Users/<name>`, API keys, or Memory-only state notes) and fails with a warning if any are found.
3. Writes a standard unified diff (`git diff` / `patch -p1` compatible) to `artifacts/the-one-skill-changes.patch` and prints a Markdown PR summary (added, modified, and deleted files with line deltas).

### 4. Review & Open Pull Request
Present the generated PR summary and any sanitization warnings to the user, along with the path to `artifacts/the-one-skill-changes.patch`.
