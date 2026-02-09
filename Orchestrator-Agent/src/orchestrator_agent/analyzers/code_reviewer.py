"""Static code-review analyzer.

Performs rule-based checks for code quality, security, and best practices.
Returns structured findings the agent can present or act on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReviewFinding:
    """A single code-review finding."""
    file: str
    line: int
    severity: str          # "critical" | "warning" | "info"
    category: str          # "security" | "quality" | "style" | "performance"
    message: str
    suggestion: str = ""


# ---------------------------------------------------------------------------
# Rule sets
# ---------------------------------------------------------------------------

SECURITY_PATTERNS: list[dict] = [
    {"pattern": r"eval\s*\(", "msg": "Use of eval() — potential code injection", "sev": "critical"},
    {"pattern": r"exec\s*\(", "msg": "Use of exec() — potential code injection", "sev": "critical"},
    {"pattern": r"subprocess\.call\(.+shell\s*=\s*True", "msg": "Shell=True in subprocess — command injection risk", "sev": "critical"},
    {"pattern": r"os\.system\s*\(", "msg": "os.system() — prefer subprocess with shell=False", "sev": "warning"},
    {"pattern": r"(password|secret|api_key|token)\s*=\s*[\"'][^\"']+[\"']", "msg": "Hardcoded secret detected", "sev": "critical"},
    {"pattern": r"pickle\.loads?\s*\(", "msg": "Insecure deserialization with pickle", "sev": "critical"},
    {"pattern": r"yaml\.load\s*\([^)]*\)(?!.*Loader)", "msg": "yaml.load without safe Loader", "sev": "warning"},
    {"pattern": r"__import__\s*\(", "msg": "Dynamic import with __import__", "sev": "warning"},
    {"pattern": r"chmod\s*\(\s*0o?777", "msg": "World-writable file permissions", "sev": "critical"},
    {"pattern": r"verify\s*=\s*False", "msg": "SSL verification disabled", "sev": "critical"},
]

QUALITY_PATTERNS: list[dict] = [
    {"pattern": r"except\s*:", "msg": "Bare except clause — catches all exceptions", "sev": "warning"},
    {"pattern": r"# ?TODO", "msg": "TODO comment found", "sev": "info"},
    {"pattern": r"# ?FIXME", "msg": "FIXME comment found", "sev": "warning"},
    {"pattern": r"# ?HACK", "msg": "HACK comment found", "sev": "warning"},
    {"pattern": r"print\s*\(", "msg": "print() call — consider using logging", "sev": "info"},
    {"pattern": r"import \*", "msg": "Wildcard import — pollutes namespace", "sev": "warning"},
    {"pattern": r"global\s+\w+", "msg": "Global variable usage", "sev": "warning"},
    {"pattern": r"time\.sleep\s*\(", "msg": "time.sleep() found — may block", "sev": "info"},
]

JS_SECURITY_PATTERNS: list[dict] = [
    {"pattern": r"innerHTML\s*=", "msg": "innerHTML assignment — XSS risk", "sev": "critical"},
    {"pattern": r"document\.write\s*\(", "msg": "document.write() — XSS risk", "sev": "critical"},
    {"pattern": r"eval\s*\(", "msg": "eval() — code injection risk", "sev": "critical"},
    {"pattern": r"dangerouslySetInnerHTML", "msg": "dangerouslySetInnerHTML — XSS risk", "sev": "warning"},
    {"pattern": r"(password|secret|api_key|token)\s*[:=]\s*[\"'][^\"']+[\"']", "msg": "Hardcoded secret detected", "sev": "critical"},
    {"pattern": r"child_process\.exec\s*\(", "msg": "child_process.exec — command injection risk", "sev": "critical"},
]


def _detect_language(filepath: str) -> str:
    """Detect language from file extension."""
    ext = Path(filepath).suffix.lower()
    lang_map = {
        ".py": "python",
        ".js": "javascript", ".jsx": "javascript",
        ".ts": "typescript", ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
    }
    return lang_map.get(ext, "unknown")


def _check_patterns(
    lines: list[str],
    patterns: list[dict],
    filepath: str,
    category: str,
) -> list[ReviewFinding]:
    """Run regex patterns over lines and collect findings."""
    findings: list[ReviewFinding] = []
    for i, line in enumerate(lines, start=1):
        for rule in patterns:
            if re.search(rule["pattern"], line, re.IGNORECASE):
                findings.append(ReviewFinding(
                    file=filepath,
                    line=i,
                    severity=rule["sev"],
                    category=category,
                    message=rule["msg"],
                ))
    return findings


# ---------------------------------------------------------------------------
# Structural checks
# ---------------------------------------------------------------------------

def _check_function_length(
    lines: list[str],
    filepath: str,
    max_lines: int = 30,
) -> list[ReviewFinding]:
    """Flag functions that exceed max_lines."""
    findings: list[ReviewFinding] = []
    func_start: int | None = None
    func_name = ""
    indent_level = 0

    for i, line in enumerate(lines, start=1):
        stripped = line.rstrip()
        m = re.match(r"^(\s*)(async\s+)?def\s+(\w+)", stripped)
        if m:
            # Close previous function
            if func_start is not None:
                length = i - func_start
                if length > max_lines:
                    findings.append(ReviewFinding(
                        file=filepath,
                        line=func_start,
                        severity="warning",
                        category="quality",
                        message=f"Function '{func_name}' is {length} lines (max {max_lines})",
                        suggestion="Break into smaller functions",
                    ))
            func_start = i
            func_name = m.group(3)
            indent_level = len(m.group(1))

    # Check last function
    if func_start is not None:
        length = len(lines) - func_start + 1
        if length > max_lines:
            findings.append(ReviewFinding(
                file=filepath,
                line=func_start,
                severity="warning",
                category="quality",
                message=f"Function '{func_name}' is {length} lines (max {max_lines})",
                suggestion="Break into smaller functions",
            ))
    return findings


def _check_file_length(
    lines: list[str],
    filepath: str,
    max_lines: int = 500,
) -> list[ReviewFinding]:
    """Flag files over max_lines."""
    if len(lines) > max_lines:
        return [ReviewFinding(
            file=filepath,
            line=1,
            severity="info",
            category="quality",
            message=f"File has {len(lines)} lines (recommended max {max_lines})",
            suggestion="Consider splitting into multiple modules",
        )]
    return []


def _check_complexity_hints(
    lines: list[str],
    filepath: str,
) -> list[ReviewFinding]:
    """Flag deeply nested code (simple indentation heuristic)."""
    findings: list[ReviewFinding] = []
    for i, line in enumerate(lines, start=1):
        stripped = line.rstrip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        # 5 levels of 4-space indentation = 20 spaces
        if indent >= 20 and stripped and not stripped.startswith("#"):
            findings.append(ReviewFinding(
                file=filepath,
                line=i,
                severity="warning",
                category="quality",
                message="Deeply nested code (5+ levels)",
                suggestion="Extract into helper function or use early returns",
            ))
    return findings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def review_file(filepath: str, content: str) -> list[dict]:
    """Review a single file and return findings as dicts."""
    lines = content.splitlines()
    lang = _detect_language(filepath)
    findings: list[ReviewFinding] = []

    # Security patterns
    if lang in ("python",):
        findings.extend(_check_patterns(lines, SECURITY_PATTERNS, filepath, "security"))
        findings.extend(_check_patterns(lines, QUALITY_PATTERNS, filepath, "quality"))
    elif lang in ("javascript", "typescript"):
        findings.extend(_check_patterns(lines, JS_SECURITY_PATTERNS, filepath, "security"))

    # Structural checks (Python)
    if lang == "python":
        findings.extend(_check_function_length(lines, filepath))
        findings.extend(_check_file_length(lines, filepath))
        findings.extend(_check_complexity_hints(lines, filepath))

    return [
        {
            "file": f.file,
            "line": f.line,
            "severity": f.severity,
            "category": f.category,
            "message": f.message,
            "suggestion": f.suggestion,
        }
        for f in findings
    ]


def review_project(files: dict[str, str]) -> dict:
    """Review all files and return a summary."""
    all_findings: list[dict] = []
    for fpath, content in files.items():
        all_findings.extend(review_file(fpath, content))

    critical = sum(1 for f in all_findings if f["severity"] == "critical")
    warnings = sum(1 for f in all_findings if f["severity"] == "warning")
    info = sum(1 for f in all_findings if f["severity"] == "info")

    return {
        "total_files_reviewed": len(files),
        "total_findings": len(all_findings),
        "critical": critical,
        "warnings": warnings,
        "info": info,
        "findings": all_findings,
        "passed": critical == 0,
    }
