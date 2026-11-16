#!/usr/bin/env python3
"""Deterministic token cap, frontmatter, trigger-overlap, trusted-source, and security linter.

Pure Python 3 standard library. Enforces:
  1. 800-token ceiling on SKILL.md using a deterministic stdlib estimator
  2. Valid YAML frontmatter ('name' and 'description' containing explicit
     'Use when' and 'Do not use when' routing guidance)
  3. Explicit '## Use when' and '## Do not use when' body sections
  4. Consent marker consistency ('opt-in' vs 'ignore')
  5. Trigger keyword overlap detection across skill rosters
  6. Security policy pattern scanning against config/security-policy.json
  7. Trusted upstream source URL validation against config/trusted-sources.json

Usage:
    python3 scripts/lint_skills.py [target_path ...] [--security-policy path]
    python3 scripts/lint_skills.py --check-source-url <candidate_url>
    python3 scripts/lint_skills.py --verify-repo
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT_PATH = REPO_ROOT / "config" / "contract.json"
DEFAULT_SECURITY_POLICY_PATH = REPO_ROOT / "config" / "security-policy.json"
DEFAULT_TRUSTED_SOURCES_PATH = REPO_ROOT / "config" / "trusted-sources.json"

MAX_SKILL_TOKENS = 800
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
OPT_IN_LINE_RE = re.compile(r"^\s*<!--\s*the-one-skill:opt-in\s*-->\s*$", re.MULTILINE)
IGNORE_LINE_RE = re.compile(r"^\s*<!--\s*the-one-skill:ignore\s*-->\s*$", re.MULTILINE)
START_LINE_RE = re.compile(r"^\s*<!--\s*the-one-skill:start\s*-->\s*$", re.MULTILINE)
END_LINE_RE = re.compile(r"^\s*<!--\s*the-one-skill:end\s*-->\s*$", re.MULTILINE)

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
    "validating", "checking", "profiling", "auditing", "inspecting", " Pure",
    "pure", "python", "stdlib",
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
    """Deterministic pure-stdlib token estimator agreed in contract.json.

    Uses the conservative maximum of:
      - Character heuristic: len(text) // 4 (~4 chars per token)
      - Whitespace word heuristic: int(len(text.split()) * 1.35) (~0.75 words per token)
    """
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
    # Strip any "Do not use when..." clause from the description so negative exclusions
    # naming other skills do not count as positive trigger collisions!
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


def load_security_policy(policy_path: Path | None = None) -> dict:
    target = policy_path or DEFAULT_SECURITY_POLICY_PATH
    if not target.exists():
        return {"banned_patterns": []}
    return json.loads(target.read_text(encoding="utf-8"))


def load_trusted_sources(sources_path: Path | None = None) -> dict:
    target = sources_path or DEFAULT_TRUSTED_SOURCES_PATH
    if not target.exists():
        return {"trusted_sources": []}
    return json.loads(target.read_text(encoding="utf-8"))


def verify_trusted_source_url(
    url: str, sources_path: Path | None = None
) -> tuple[bool, str]:
    """Verify whether a candidate URL belongs to an approved source in trusted-sources.json."""
    cleaned = url.strip()
    data = load_trusted_sources(sources_path)
    for src in data.get("trusted_sources", []):
        provider = src.get("provider", src.get("id", "unknown"))
        repo = src.get("repository", "")
        for prefix in src.get("allowed_url_prefixes", []):
            if cleaned.startswith(prefix) or cleaned == prefix.rstrip("/"):
                return True, f"PASS: Trusted source ({provider} — {repo})"
    return (
        False,
        f"FAIL: Untrusted skill source URL {cleaned!r} is not in config/trusted-sources.json",
    )


def scan_security_patterns(text: str, rel_label: str, policy: dict) -> list[str]:
    findings: list[str] = []
    for rule in policy.get("banned_patterns", []):
        rule_id = rule.get("id", "SEC-UNK")
        category = rule.get("category", "unknown")
        regex = rule.get("regex", "")
        if not regex:
            continue
        match = re.search(regex, text)
        if match:
            snippet = match.group(0).strip().replace("\n", " ")[:60]
            findings.append(
                f"[{rule_id}:{category}] in {rel_label}: matched banned pattern {snippet!r}"
            )
    return findings


def lint_skill_file(
    skill_md_path: Path,
    security_policy: dict | None = None,
    max_tokens: int = MAX_SKILL_TOKENS,
) -> SkillLintResult:
    policy = security_policy if security_policy is not None else load_security_policy()
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
        try:
            file_text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel_label = (
            file_path.relative_to(skill_dir).as_posix()
            if file_path != skill_md_path
            else skill_md_path.name
        )
        security_findings.extend(scan_security_patterns(file_text, rel_label, policy))

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


def verify_repository(policy_path: Path | None = None) -> int:
    """Run full deterministic repository check: valid skills pass, trap fixtures fail."""
    policy = load_security_policy(policy_path)
    failures: list[str] = []

    valid_targets = [
        REPO_ROOT / "SKILL.md",
        REPO_ROOT / "templates" / "skill-template.md",
    ]
    verified_fixtures_dir = REPO_ROOT / "evals" / "fixtures" / "verified-skills"
    if verified_fixtures_dir.is_dir():
        valid_targets.extend(sorted(verified_fixtures_dir.rglob("SKILL.md")))

    print("=== Checking Valid Skills & Verified Sample Fixtures ===")
    valid_results: list[SkillLintResult] = []
    for path in valid_targets:
        res = lint_skill_file(path, security_policy=policy)
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
            res = lint_skill_file(trap_md, security_policy=policy)
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
        pair_results = [lint_skills_file_result := lint_skill_file(f, security_policy=policy) for f in pair_files]
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic token cap, frontmatter, overlap, trusted-source, and security linter."
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Skill files or directories to lint (defaults to --verify-repo if omitted).",
    )
    parser.add_argument(
        "--security-policy",
        type=Path,
        default=None,
        help="Path to security-policy.json (defaults to config/security-policy.json).",
    )
    parser.add_argument(
        "--check-source-url",
        type=str,
        default=None,
        help="Verify whether a candidate upstream skill URL belongs to config/trusted-sources.json.",
    )
    parser.add_argument(
        "--verify-repo",
        action="store_true",
        help="Run full repository lint check including verified and trap fixtures.",
    )
    args = parser.parse_args(argv)

    if args.check_source_url is not None:
        passed, msg = verify_trusted_source_url(args.check_source_url)
        print(msg)
        return 0 if passed else 1

    if args.verify_repo or not args.targets:
        return verify_repository(args.security_policy)

    policy = load_security_policy(args.security_policy)
    skill_files = discover_skill_files(args.targets)
    if not skill_files:
        print(f"ERROR: No SKILL.md files found in targets: {args.targets}", file=sys.stderr)
        return 2

    results: list[SkillLintResult] = []
    any_failed = False

    for sf in skill_files:
        res = lint_skill_file(sf, security_policy=policy)
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
