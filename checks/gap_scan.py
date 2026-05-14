"""
Design–Implementation gap scanner.
Zero external dependencies. Run from repo root:
  python checks/gap_scan.py [--doc <path>] [--code <dir>] [--json]

Reads design documents, extracts verifiable claims, searches code for
implementation evidence, and writes .deepship/gap_report.md.

Layers:
  L1 structural  — verify.py (already exists)
  L2 contractual — conformance tests (already exists)
  L3 design–impl — THIS SCRIPT
  L4 flow–reality — part of L3 (state machine claims → transition code)
"""

import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent

# ── Claim extraction patterns ──────────────────────────────

CLAIM_PATTERNS: list[tuple[str, str]] = [
    # Chinese behavioral claims
    (r"(.{0,80}(?:负责|拦截|检查|验证|确保|阻止|放行|拒绝|允许|禁止|强制).{0,80})", "behavior"),
    # Chinese passive voice
    (r"(.{0,80}(?:被(?:拦截|拒绝|阻止|放行|允许|禁止|强制|跳过|绕过)).{0,80})", "behavior"),
    # English RFC-style policy claims
    (r"(.{0,120}\bMUST(?:\s+NOT)?\b.{0,120})", "policy"),
    (r"(.{0,120}\bSHALL(?:\s+NOT)?\b.{0,120})", "policy"),
    (r"(.{0,120}\bMAY\b.{0,120})", "policy"),
    (r"(.{0,120}\bMUST NOT\b.{0,120})", "policy"),
    (r"(.{0,120}\bSHALL NOT\b.{0,120})", "policy"),
    # English ALLOW/BLOCK/DENY claims (capitalized — gate labels)
    (r"(.{0,80}(?:\bALLOW\b|\bBLOCK\b|\bDENY\b).{0,80})", "policy"),
    # English behavioral verbs
    (r"(.{0,80}(?:is responsible for|intercepts|validates|verifies|enforces|checks|guards|prevents|ensures).{0,80})", "behavior"),
    # Transitions
    (r"(.{0,80}(?:→|→).{0,80})", "transition"),
    # Backtick-quoted file/function with action
    (r"(`[a-zA-Z_][a-zA-Z0-9_./]*\.[a-z]+(?:::\w+)?`\s*(?:负责|拦截|检查|实现|处理|调用|写入|读取).{0,60})", "function-claim"),
    (r"(`[a-zA-Z_][a-zA-Z0-9_./]*\.(?:py|js|md|json)`\s*(?:.{0,40}(?:负责|定义|包含|实现|处理)))", "file-claim"),
    # Chinese wildcard claims
    (r"(.{0,60}(?:所有.+?(?:放行|允许|不拦截|跳过)).{0,60})", "wildcard"),
]

SKIP_PATTERNS = [
    r"^\s*#+\s",
    r"^\s*\|",
    r"^\s*```",
    r"^\s*[-*]\s*\[.\]\s*$",
    r"^\s*$",
]


def extract_claims(doc_path: Path) -> list[dict]:
    claims = []
    text = doc_path.read_text(encoding="utf-8")
    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if any(re.match(p, stripped) for p in SKIP_PATTERNS):
            continue
        for pattern, category in CLAIM_PATTERNS:
            matches = re.findall(pattern, stripped, re.IGNORECASE)
            for m in matches:
                claim_text = m if isinstance(m, str) else m[0]
                claim_text = claim_text.strip()
                if len(claim_text) < 10:
                    continue
                claims.append({
                    "text": claim_text,
                    "category": category,
                    "line": i,
                    "source_file": str(doc_path.relative_to(ROOT)),
                })
                break
    return claims


def extract_keywords(claim_text: str) -> list[str]:
    keywords = []
    backticked = re.findall(r"`([^`]+)`", claim_text)
    for bt in backticked:
        parts = bt.replace("\\", "/").split("/")
        keywords.append(parts[-1])
    keywords.extend(backticked)
    camel = re.findall(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", claim_text)
    keywords.extend(camel)
    snake = re.findall(r"\b([a-z]+(?:_[a-z]+){1,})\b", claim_text)
    keywords.extend(snake)
    cn_verbs = re.findall(r"(负责|拦截|检查|验证|确保|阻止|放行|拒绝|允许|禁止|强制|跳过|绕过|读取|写入|调用|实现|处理)", claim_text)
    keywords.extend(cn_verbs)
    en_verbs = re.findall(r"\b(ALLOW|BLOCK|DENY|MUST NOT|MUST|SHALL NOT|SHALL|intercept|validate|verify|enforce|check|guard)\b", claim_text, re.IGNORECASE)
    keywords.extend([v.upper() for v in en_verbs])
    seen = set()
    unique = []
    for kw in keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            unique.append(kw)
    return unique[:8]


@dataclass
class Evidence:
    claim_idx: int
    claim_text: str
    category: str
    source_file: str
    source_line: int
    keywords: list[str]
    matches: list = field(default_factory=list)
    score: str = "no_match"
    confidence: float = 0.0


def search_codebase(keywords: list[str], code_dirs: list[Path]) -> list[dict]:
    matches = []
    exts = {".py", ".js", ".ts", ".md"}
    for code_dir in code_dirs:
        if not code_dir.exists():
            continue
        for fp in code_dir.rglob("*"):
            if fp.is_dir() or fp.suffix not in exts:
                continue
            if any(skip in str(fp) for skip in ["__pycache__", "node_modules", ".git"]):
                continue
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for kw in keywords:
                if len(kw) < 3:
                    continue
                if kw.lower() in content.lower():
                    for li, line in enumerate(content.split("\n"), 1):
                        if kw.lower() in line.lower():
                            matches.append({
                                "file": str(fp.relative_to(ROOT)),
                                "line": li,
                                "content": line.strip()[:120],
                                "keyword": kw,
                            })
                            if len(matches) >= 50:
                                return matches
    return matches


def score_evidence(claim: dict, matches: list[dict]) -> tuple[str, float]:
    if not matches:
        return "no_match", 0.0
    unique_files = {m["file"] for m in matches}
    unique_keywords = {m["keyword"].lower() for m in matches}
    code_files = {f for f in unique_files if f.endswith((".py", ".js", ".ts"))}
    claimed_ids = set(re.findall(r"`([^`]+)`", claim["text"]))
    has_direct = any(
        any(cid.lower() in m["content"].lower() for cid in claimed_ids)
        for m in matches
    ) if claimed_ids else False
    n_code = len(code_files)
    n_kw = len(unique_keywords)
    if n_code >= 1 and n_kw >= 2 and has_direct:
        return "direct_match", min(0.95, 0.5 + 0.15 * n_code + 0.1 * n_kw)
    elif n_code >= 1 and n_kw >= 2:
        return "partial_match", min(0.85, 0.3 + 0.15 * n_code + 0.1 * n_kw)
    elif len(matches) >= 2:
        return "partial_match", min(0.7, 0.2 + 0.1 * len(unique_files) + 0.1 * n_kw)
    elif len(matches) == 1:
        return "partial_match", 0.2
    return "no_match", 0.0


def generate_report(evidences, doc_path, code_dirs, output_path, json_output=False):
    n_total = len(evidences)
    n_direct = sum(1 for e in evidences if e.score == "direct_match")
    n_partial = sum(1 for e in evidences if e.score == "partial_match")
    n_gap = sum(1 for e in evidences if e.score == "no_match")
    coverage = (n_direct + n_partial * 0.5) / max(n_total, 1) * 100
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = []
    lines.append("# Gap Scan Report")
    lines.append("")
    lines.append(f"> Generated: {now} | Doc: `{doc_path.name}` | Code: {', '.join(f'`{d}`' for d in code_dirs)}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total claims | {n_total} |")
    lines.append(f"| Direct evidence | {n_direct} |")
    lines.append(f"| Partial evidence | {n_partial} |")
    lines.append(f"| **Gaps (no evidence)** | **{n_gap}** |")
    lines.append(f"| Evidence coverage | {coverage:.0f}% |")
    lines.append("")

    gaps = [e for e in evidences if e.score == "no_match"]
    if gaps:
        lines.append("## Gaps — No Implementation Evidence")
        lines.append("")
        for e in gaps:
            lines.append(f"### {e.category.upper()}: {e.claim_text[:80]}...")
            lines.append(f"- **Source**: `{e.source_file}:{e.source_line}`")
            lines.append(f"- **Keywords**: {', '.join(e.keywords[:5])}")
            lines.append(f"- **Action**: Implement or update doc")
            lines.append("")

    partials = [e for e in evidences if e.score == "partial_match"]
    if partials:
        lines.append("## Partial Matches")
        lines.append("")
        for e in partials:
            lines.append(f"### {e.category.upper()}: {e.claim_text[:80]}...")
            lines.append(f"- **Source**: `{e.source_file}:{e.source_line}` | Confidence: {e.confidence:.0%}")
            for m in e.matches[:5]:
                lines.append(f"  - `{m['file']}:{m['line']}` — `{m['content'][:80]}`")
            lines.append("")

    directs = [e for e in evidences if e.score == "direct_match"]
    if directs:
        lines.append("## Direct Matches")
        lines.append("")
        for e in directs:
            first = e.matches[0] if e.matches else None
            ref = f" → `{first['file']}:{first['line']}`" if first else ""
            lines.append(f"- **{e.category.upper()}**: {e.claim_text[:100]}{ref}")

    by_cat = defaultdict(lambda: {"total": 0, "direct": 0, "partial": 0, "gap": 0})
    for e in evidences:
        by_cat[e.category]["total"] += 1
        if e.score == "direct_match":
            by_cat[e.category]["direct"] += 1
        elif e.score == "partial_match":
            by_cat[e.category]["partial"] += 1
        else:
            by_cat[e.category]["gap"] += 1

    lines.append("")
    lines.append("## Category Breakdown")
    lines.append("")
    lines.append("| Category | Total | Direct | Partial | Gap |")
    lines.append("|----------|-------|--------|---------|-----|")
    for cat in sorted(by_cat):
        d = by_cat[cat]
        lines.append(f"| {cat} | {d['total']} | {d['direct']} | {d['partial']} | {d['gap']} |")

    report = "\n".join(lines) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"Report: {output_path} ({n_gap} gaps, {n_partial} partial, {n_direct} direct)")

    if json_output:
        json_path = output_path.with_suffix(".json")
        json_data = {
            "generated": now, "doc": str(doc_path),
            "summary": {"total": n_total, "direct": n_direct, "partial": n_partial, "gaps": n_gap, "coverage_pct": round(coverage, 1)},
            "gaps": [{"text": e.claim_text, "source": f"{e.source_file}:{e.source_line}", "category": e.category} for e in evidences if e.score == "no_match"],
        }
        json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"JSON: {json_path}")
    return report


def scan(doc_path, code_dirs, output_path=None, json_output=False):
    doc_path = doc_path.resolve()
    if output_path is None:
        output_path = ROOT / ".deepship" / "gap_report.md"
    print(f"Doc: {doc_path}")
    print(f"Code: {[str(d) for d in code_dirs]}")
    claims = extract_claims(doc_path)
    print(f"Claims: {len(claims)}")
    evidences = []
    for i, claim in enumerate(claims):
        keywords = extract_keywords(claim["text"])
        if not keywords:
            continue
        matches = search_codebase(keywords, code_dirs)
        score, confidence = score_evidence(claim, matches)
        ev = Evidence(claim_idx=i, claim_text=claim["text"], category=claim["category"],
                      source_file=claim["source_file"], source_line=claim["line"],
                      keywords=keywords, matches=matches, score=score, confidence=confidence)
        evidences.append(ev)
    generate_report(evidences, doc_path, code_dirs, output_path, json_output)
    return evidences


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DEEPSHIP Gap Scanner — design-implementation consistency")
    parser.add_argument("--doc", type=str, help="Design document to scan")
    parser.add_argument("--code", type=str, nargs="+", default=["adapters/", "rules/", "protocol/"], help="Code dirs")
    parser.add_argument("--output", "-o", type=str, help="Output path")
    parser.add_argument("--json", action="store_true", help="Also output JSON")
    parser.add_argument("--all", action="store_true", help="Scan all protocol/ docs")
    args = parser.parse_args()

    if args.all:
        protocol_dir = ROOT / "protocol"
        code_dirs = [ROOT / d for d in args.code if (ROOT / d).exists()]
        all_ev = []
        for dp in sorted(protocol_dir.glob("*.md")):
            ev = scan(dp, code_dirs, ROOT / ".deepship" / f"gap_report_{dp.stem}.md", args.json)
            all_ev.extend(ev)
        n_gaps = sum(1 for e in all_ev if e.score == "no_match")
        print(f"\n=== ALL: {len(all_ev)} claims, {n_gaps} gaps ===")
    elif args.doc:
        doc_path = Path(args.doc)
        if not doc_path.exists():
            doc_path = ROOT / args.doc
        if not doc_path.exists():
            print(f"Not found: {args.doc}", file=sys.stderr)
            sys.exit(1)
        code_dirs = [ROOT / d for d in args.code if (ROOT / d).exists()]
        output_path = Path(args.output) if args.output else None
        ev = scan(doc_path, code_dirs, output_path, args.json)
        print(f"\nDone: {len(ev)} claims, {sum(1 for e in ev if e.score == 'no_match')} gaps")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
