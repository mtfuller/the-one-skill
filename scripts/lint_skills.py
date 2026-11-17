#!/usr/bin/env python3
"""Self-contained deterministic token cap, frontmatter, overlap, trusted-source, and security linter.

Pure Python 3 standard library. Enforces:
  1. 800-token ceiling on SKILL.md using a deterministic stdlib estimator
  2. Valid YAML frontmatter ('name' and 'description' containing explicit
     'Use when' and 'Do not use when' routing guidance)
  3. Explicit '## Use when' and '## Do not use when' body sections
  4. Consent marker consistency ('opt-in' vs 'ignore')
  5. Trigger keyword overlap detection across skill rosters
  6. Built-in security pattern scanning (SEC-001 through SEC-005)
  7. Built-in trusted upstream source URL validation (Anthropic, OpenAI, Google Gemini)

Usage:
    python3 scripts/lint_skills.py [target_path ...]
    python3 scripts/lint_skills.py --check-source-url <candidate_url>
    python3 scripts/lint_skills.py --verify-repo
    python3 scripts/lint_skills.py --self-check
"""

from __future__ import annotations

import argparse
import dataclasses
import re
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent

MAX_SKILL_TOKENS = 800
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
OPT_IN_LINE_RE = re.compile(r"^\s*<!--\s*the-one-skill:opt-in\s*-->\s*$", re.MULTILINE)
IGNORE_LINE_RE = re.compile(r"^\s*<!--\s*the-one-skill:ignore\s*-->\s*$", re.MULTILINE)
START_LINE_RE = re.compile(r"^\s*<!--\s*the-one-skill:start\s*-->\s*$", re.MULTILINE)
END_LINE_RE = re.compile(r"^\s*<!--\s*the-one-skill:end\s*-->\s*$", re.MULTILINE)

TRUSTED_SOURCES: tuple[dict[str, object], ...] = (
    {
        "id": "anthropic-official",
        "provider": "Anthropic",
        "repository": "anthropics/skills",
        "allowed_url_prefixes": (
            "https://github.com/anthropics/skills/",
            "https://raw.githubusercontent.com/anthropics/skills/",
        ),
    },
    {
        "id": "openai-official",
        "provider": "OpenAI",
        "repository": "openai/skills",
        "allowed_url_prefixes": (
            "https://github.com/openai/skills/",
            "https://raw.githubusercontent.com/openai/skills/",
        ),
    },
    {
        "id": "google-gemini-official",
        "provider": "Google Gemini",
        "repository": "google-gemini/gemini-skills",
        "allowed_url_prefixes": (
            "https://github.com/google-gemini/gemini-skills/",
            "https://raw.githubusercontent.com/google-gemini/gemini-skills/",
        ),
    },
)

BANNED_SECURITY_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "SEC-001",
        "prompt_injection_override",
        re.compile(
            r"(?i)(ignore\s+(all\s+)?(previous|prior|system)\s+instructions|disregard\s+safety|bypass\s+security\s+policy|skip\s+diff\s+approval)"
        ),
    ),
    (
        "SEC-002",
        "network_exfiltration",
        re.compile(
            r"(?i)(curl\s+-[a-zA-Z]*d|wget\s+--post|urllib\.request\.urlopen|requests\.(post|put)|webhook\.site|ngrok-free\.app|pipedream\.net|burpcollaborator)"
        ),
    ),
    (
        "SEC-003",
        "credential_harvesting",
        re.compile(
            r"(?i)(~/.ssh/id_|~/.aws/credentials|~/.config/gcloud|OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|GITHUB_TOKEN|os\.environ)"
        ),
    ),
    (
        "SEC-004",
        "opaque_execution",
        re.compile(
            r"(?i)(base64\.b64decode\s*\(|exec\s*\(\s*compile|eval\s*\(\s*__import__|subprocess\.(Popen|run|call)\s*\(.*shell\s*=\s*True)"
        ),
    ),
    (
        "SEC-005",
        "unauthorized_mutation",
        re.compile(
            r"(?i)(remove\s+the-one-skill:ignore|strip\s+ignore\s+marker\s+silently)"
        ),
    ),
)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "before", "by", "can", "do",
    "does", "for", "from", "has", "have", "how", "if", "in", "into", "is",
    "it", "its", "may", "need", "needs", "no", "not", "of", "on", "one",
    "only", "or", "other", "out", "over", "run", "running", "should", "skill",
    "skills", "so", "some", "such", "task", "tasks", "than", "that", "the",
    "their", "them", "then", "there", "these", "they", "this", "to", "under",
    "up", "use", "used", "user", "using", "via", "wants", "when", "where",
    "which", "while", "with", "without", "workflow", "workflows", "you", "your",
    "asks", "ask", "perform", "specific", "input", "involves", "needed",
    "request", "general", "question", "outside", "handled", "audit", "validate",
    "check", "inspect", "missing", "file", "files", "keys", "definitions",
    "validating", "checking", "profiling", "auditing", "inspecting", "pure",
    "python", "stdlib",
}


@dataclasses.dataclass
class SkillLintResult:
    skill_path: Path
    name: str
    description: str
    token_count: int
    consent_state: str  # "opt-in", "ignore", "unmanaged", "conflict"
    trigger_keywords: set[str]
    errors: list[str]
    warnings: list[str]
    security_findings: list[str]

    @property
    def passed(self) -> bool:
        return not self.errors and not self.security_findings


def estimate_tokens(text: str) -> int:
    """Deterministic pure-stdlib token estimator: max(chars // 4, int(words * 1.35))."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    char_estimate = len(normalized) // 4
    word_estimate = int(len(normalized.split()) * 1.35)
    return max(char_estimate, word_estimate)


def parse_frontmatter(content: str) -> dict[str, str]:
    """Parse simple key: value YAML frontmatter without third-party PyYAML."""
    match = FRONTMATTER_RE.match(content)
    if not match:
        return {}
    block = match.group(1)
    result: dict[str, str] = {}
    current_key: str | None = None
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in raw_line and not raw_line.startswith((" ", "\t")):
            key, val = raw_line.split(":", 1)
            current_key = key.strip()
            cleaned_val = val.strip().strip("'\"")
            result[current_key] = cleaned_val
        elif current_key and raw_line.startswith((" ", "\t")):
            result[current_key] = (result[current_key] + " " + line).strip()
    return result


def extract_section(content: str, heading_name: str) -> str:
    """Extract markdown text beneath a `## <heading_name>` section until the next heading."""
    pattern = re.compile(
        rf"^##+\s+{re.escape(heading_name)}\b[^\n]*\n(.*?)(?=^##+\s+|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    return match.group(1).strip() if match else ""


def extract_trigger_keywords(description: str, use_when_section: str) -> set[str]:
    """Extract normalized positive trigger keywords from description and 'Use when' bullets."""
    positive_desc = re.split(r"(?i)\bdo\s+not\s+use\s+when\b", description)[0]
    combined = f"{positive_desc}\n{use_when_section}".lower()
    combined = re.sub(r"<!--.*?-->", " ", combined, flags=re.DOTALL)
    words = re.findall(r"[a-z0-9][a-z0-9_-]{2,}", combined)
    return {w.strip("_-") for w in words if w.strip("_-") not in STOPWORDS and len(w) >= 3}


def detect_consent_state(content: str) -> str:
    has_opt_in = bool(OPT_IN_LINE_RE.search(content))
    has_ignore = bool(IGNORE_LINE_RE.search(content))
    if has_opt_in and has_ignore:
        return "conflict"
    if has_ignore:
        return "ignore"
    if has_opt_in:
        return "opt-in"
    return "unmanaged"


def verify_trusted_source_url(url: str) -> tuple[bool, str]:
    """Verify whether a candidate URL belongs to an approved upstream skill repository."""
    cleaned = url.strip()
    for src in TRUSTED_SOURCES:
        provider = str(src["provider"])
        repo = str(src["repository"])
        prefixes = src["allowed_url_prefixes"]
        assert isinstance(prefixes, tuple)
        for prefix in prefixes:
            if cleaned.startswith(prefix) or cleaned == prefix.rstrip("/"):
                return True, f"PASS: Trusted source ({provider} — {repo})"
    return (
        False,
        f"FAIL: Untrusted skill source URL {cleaned!r} is not in TRUSTED_SOURCES",
    )


def scan_security_patterns(text: str, rel_label: str) -> list[str]:
    findings: list[str] = []
    for rule_id, category, pattern in BANNED_SECURITY_PATTERNS:
        match = pattern.search(text)
        if match:
            snippet = match.group(0).strip().replace("\n", " ")[:60]
            findings.append(
                f"[{rule_id}:{category}] in {rel_label}: matched banned pattern {snippet!r}"
            )
    return findings


def lint_skill_file(
    skill_md_path: Path,
    max_tokens: int = MAX_SKILL_TOKENS,
) -> SkillLintResult:
    content = skill_md_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    tokens = estimate_tokens(content)
    fm = parse_frontmatter(content)
    name = fm.get("name", "")
    description = fm.get("description", "")
    consent = detect_consent_state(content)

    errors: list[str] = []
    warnings: list[str] = []

    if not fm:
        errors.append("Missing YAML frontmatter block (`--- ... ---`).")
    else:
        if not name:
            errors.append("Missing required frontmatter key: `name`.")
        if not description:
            errors.append("Missing required frontmatter key: `description`.")
        else:
            if not re.search(r"\buse\s+when\b", description, re.IGNORECASE):
                errors.append(
                    "Frontmatter `description` must explicitly state when to use the skill (`Use when ...`)."
                )
            if not re.search(r"\bdo\s+not\s+use\s+when\b", description, re.IGNORECASE):
                errors.append(
                    "Frontmatter `description` must explicitly state when not to use the skill (`Do not use when ...`)."
                )

    if tokens > max_tokens:
        errors.append(
            f"Token ceiling exceeded: {tokens} tokens (max allowed is {max_tokens}). "
            "Move detailed material to references/."
        )

    use_when = extract_section(content, "Use when")
    do_not_use_when = extract_section(content, "Do not use when")

    if not use_when:
        errors.append("Missing required `## Use when` section.")
    if not do_not_use_when:
        errors.append("Missing required `## Do not use when` section.")

    if consent == "conflict":
        errors.append(
            "Conflicting consent markers: both `the-one-skill:opt-in` and `the-one-skill:ignore` are present."
        )

    has_start = bool(START_LINE_RE.search(content))
    has_end = bool(END_LINE_RE.search(content))
    if has_start != has_end:
        errors.append("Unbalanced `the-one-skill:start` / `the-one-skill:end` delimiter markers.")

    security_findings: list[str] = []
    skill_dir = skill_md_path.parent
    files_to_scan = [skill_md_path]
    for sub in ("scripts", "references"):
        subdir = skill_dir / sub
        if subdir.is_dir():
            files_to_scan.extend(sorted(p for p in subdir.rglob("*") if p.is_file()))

    for file_path in files_to_scan:
        if file_path.resolve() == Path(__file__).resolve():
            continue
        try:
            file_text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel_label = (
            file_path.relative_to(skill_dir).as_posix()
            if file_path != skill_md_path
            else skill_md_path.name
        )
        security_findings.extend(scan_security_patterns(file_text, rel_label))

    keywords = extract_trigger_keywords(description, use_when)

    return SkillLintResult(
        skill_path=skill_md_path,
        name=name or skill_md_path.parent.name,
        description=description,
        token_count=tokens,
        consent_state=consent,
        trigger_keywords=keywords,
        errors=errors,
        warnings=warnings,
        security_findings=security_findings,
    )


def detect_roster_overlaps(
    results: Sequence[SkillLintResult],
    jaccard_threshold: float = 0.35,
    min_shared_keywords: int = 4,
) -> list[str]:
    """Return overlap warnings across non-ignored skills in a roster."""
    overlaps: list[str] = []
    active = [r for r in results if r.consent_state != "ignore" and r.trigger_keywords]
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            a, b = active[i], active[j]
            shared = sorted(a.trigger_keywords & b.trigger_keywords)
            union = a.trigger_keywords | b.trigger_keywords
            if not union:
                continue
            jaccard = len(shared) / len(union)
            if jaccard >= jaccard_threshold or (
                len(shared) >= min_shared_keywords and jaccard >= 0.20
            ):
                overlaps.append(
                    f"Trigger overlap between `{a.name}` and `{b.name}`: "
                    f"Jaccard={jaccard:.2f}, shared_keywords={shared}"
                )
    return overlaps


def discover_skill_files(targets: Sequence[str | Path]) -> list[Path]:
    found: list[Path] = []
    for raw in targets:
        p = Path(raw).resolve()
        if p.is_file():
            found.append(p)
        elif p.is_dir():
            direct = p / "SKILL.md"
            if direct.is_file():
                found.append(direct)
            else:
                found.extend(sorted(p.rglob("SKILL.md")))
    return found


def verify_repository() -> int:
    """Run full deterministic repository check: valid skills pass, trap fixtures fail."""
    failures: list[str] = []

    valid_targets = [
        REPO_ROOT / "SKILL.md",
    ]
    verified_fixtures_dir = REPO_ROOT / "evals" / "fixtures" / "verified-skills"
    if verified_fixtures_dir.is_dir():
        valid_targets.extend(sorted(verified_fixtures_dir.rglob("SKILL.md")))

    print("=== Checking Valid Skills & Verified Sample Fixtures ===")
    valid_results: list[SkillLintResult] = []
    for path in valid_targets:
        res = lint_skill_file(path)
        valid_results.append(res)
        rel = path.relative_to(REPO_ROOT).as_posix()
        status = "PASS" if res.passed else "FAIL"
        print(
            f"  [{status}] {rel} (name={res.name}, tokens={res.token_count}/{MAX_SKILL_TOKENS}, consent={res.consent_state})"
        )
        if not res.passed:
            for err in res.errors + res.security_findings:
                print(f"         -> {err}")
                failures.append(f"{rel}: {err}")

    verified_only = [
        r for r in valid_results if "verified-skills" in r.skill_path.as_posix()
    ]
    verified_overlaps = detect_roster_overlaps(verified_only)
    if verified_overlaps:
        for ov in verified_overlaps:
            print(f"  [FAIL] Verified fixture overlap: {ov}")
            failures.append(ov)

    traps_dir = REPO_ROOT / "evals" / "fixtures" / "traps"
    if traps_dir.is_dir():
        print("\n=== Verifying Negative Trap Fixtures (Must Be Blocked) ===")
        for trap_md in sorted(traps_dir.rglob("SKILL.md")):
            res = lint_skill_file(trap_md)
            rel = trap_md.relative_to(REPO_ROOT).as_posix()
            if res.passed:
                msg = f"Trap fixture unexpectedly passed lint/security: {rel}"
                print(f"  [FAIL] {msg}")
                failures.append(msg)
            else:
                reasons = "; ".join(res.errors + res.security_findings)
                print(f"  [PASS: Caught Trap] {rel} -> {reasons}")

    overlap_dir = REPO_ROOT / "evals" / "fixtures" / "overlap-pair"
    if overlap_dir.is_dir():
        print("\n=== Verifying Overlap-Pair Fixture (Must Flag Trigger Collision) ===")
        pair_files = sorted(overlap_dir.rglob("SKILL.md"))
        pair_results = [lint_skill_file(f) for f in pair_files]
        overlaps = detect_roster_overlaps(pair_results)
        if not overlaps:
            msg = "Overlap-pair fixture did not trigger detect_roster_overlaps()"
            print(f"  [FAIL] {msg}")
            failures.append(msg)
        else:
            for ov in overlaps:
                print(f"  [PASS: Caught Overlap] {ov}")

    if failures:
        print(f"\nRepository lint verification FAILED with {len(failures)} error(s).", file=sys.stderr)
        return 1

    print("\nPASS: All repository skills and negative fixtures verified deterministically.")
    return 0


def self_check() -> int:
    """Print what the-one-skill can run here. Exit 0 only if every script is present."""
    scripts = ("lint_skills.py", "skillctl.py", "export_diff.py")
    missing = [name for name in scripts if not (REPO_ROOT / "scripts" / name).is_file()]
    print(f"python {sys.version.split()[0]}; the-one-skill at {REPO_ROOT}")
    if missing:
        print(f"SELF-CHECK FAIL: missing scripts: {', '.join(missing)}")
        return 1
    print("SELF-CHECK OK: code execution and the-one-skill scripts are available.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Self-contained deterministic token cap, frontmatter, overlap, trusted-source, and security linter."
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Skill files or directories to lint (defaults to --verify-repo if omitted).",
    )
    parser.add_argument(
        "--check-source-url",
        type=str,
        default=None,
        help="Verify whether a candidate upstream skill URL belongs to an approved trusted source.",
    )
    parser.add_argument(
        "--verify-repo",
        action="store_true",
        help="Run full repository lint check including verified and trap fixtures.",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Confirm that code execution works and the-one-skill's scripts are reachable.",
    )
    args = parser.parse_args(argv)

    if args.self_check:
        return self_check()

    if args.check_source_url is not None:
        passed, msg = verify_trusted_source_url(args.check_source_url)
        print(msg)
        return 0 if passed else 1

    if args.verify_repo or not args.targets:
        return verify_repository()

    skill_files = discover_skill_files(args.targets)
    if not skill_files:
        print(f"ERROR: No SKILL.md files found in targets: {args.targets}", file=sys.stderr)
        return 2

    results: list[SkillLintResult] = []
    any_failed = False

    for sf in skill_files:
        res = lint_skill_file(sf)
        results.append(res)
        status = "PASS" if res.passed else "FAIL"
        print(
            f"[{status}] {sf} (name={res.name}, tokens={res.token_count}/{MAX_SKILL_TOKENS}, consent={res.consent_state})"
        )
        for err in res.errors:
            print(f"  ERROR: {err}")
        for sec in res.security_findings:
            print(f"  SECURITY: {sec}")
        if not res.passed:
            any_failed = True

    overlaps = detect_roster_overlaps(results)
    for ov in overlaps:
        print(f"OVERLAP WARNING: {ov}")

    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
