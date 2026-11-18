#!/usr/bin/env python3
"""Run one headless Claude Code turn in a fixture and summarize it.

Usage: run.py <fixture_dir> <name> <prompt> [--continue]

Writes <name>.jsonl (full stream) and <name>.txt (tool calls + final reply) next to the
fixture folder, and prints the summary. `--continue` resumes the fixture's last session.
Permissions stay on: writes under .claude/ are denied headless, so scenarios that apply
changes must be run interactively (see README.md).
"""
import json
import pathlib
import subprocess
import sys

ALLOWED = ("Read,Write,Edit,Glob,Grep,Skill,WebSearch,WebFetch,Bash(python3:*),Bash(ls:*),Bash(cat:*),Bash(diff:*),"
           "Bash(mkdir:*),Bash(cp:*),Bash(find:*),Bash(date:*),Bash(git status:*),Bash(git diff:*)")


def main() -> int:
    d, name, prompt = sys.argv[1], sys.argv[2], sys.argv[3]
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--permission-mode", "acceptEdits", "--allowedTools", ALLOWED]
    if "--continue" in sys.argv[4:]:
        cmd.append("--continue")
    mcp = pathlib.Path(d) / ".eval-mcp.json"  # a fixture's fake connectors (see make_fixture.sh)
    if mcp.is_file():
        servers = json.loads(mcp.read_text())["mcpServers"]
        cmd[cmd.index("--allowedTools") + 1] += "," + ",".join(f"mcp__{s}" for s in servers)
        cmd += ["--mcp-config", str(mcp)]
    r = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=900)
    out_dir = pathlib.Path(d).resolve().parent
    (out_dir / f"{name}.jsonl").write_text(r.stdout)
    tools, final, denied = [], "", []
    for line in r.stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            for c in ev["message"].get("content", []):
                if c.get("type") == "tool_use":
                    i = c["input"]
                    s = i.get("command") or i.get("file_path") or i.get("skill") or i.get("pattern") or ""
                    tools.append(f'{c["name"]}: {str(s)[:150]}')
        elif ev.get("type") == "result":
            final = ev.get("result", "")
            denied = [x.get("tool_name") for x in ev.get("permission_denials", [])]
    lines = [f"=== {name} ===", "TOOLS:"] + [f"  {t}" for t in tools]
    if denied:
        lines.append(f"DENIED: {denied}")
    lines += ["FINAL:", final]
    if r.returncode:
        lines.append(f"EXIT {r.returncode}: {r.stderr[-500:]}")
    txt = "\n".join(lines)
    (out_dir / f"{name}.txt").write_text(txt)
    print(txt)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
