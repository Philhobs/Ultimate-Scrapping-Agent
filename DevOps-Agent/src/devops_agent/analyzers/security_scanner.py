"""Security scanner — detect hardcoded secrets, vulnerable patterns, and policy violations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    "dist", "build", ".next", "target",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf",
    ".eot", ".pdf", ".zip", ".tar", ".gz", ".exe", ".dll", ".so",
    ".pyc", ".pyo", ".o", ".a",
}


@dataclass
class SecurityFinding:
    severity: str  # "critical", "high", "medium", "low"
    category: str  # "hardcoded_secret", "vulnerable_dep", "insecure_config", etc.
    file: str
    line: int
    message: str
    context: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "context": self.context[:120],
        }


# Secret patterns (name, regex, severity)
SECRET_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("AWS Access Key", re.compile(r'AKIA[0-9A-Z]{16}'), "critical"),
    ("AWS Secret Key", re.compile(r'(?i)aws.{0,20}secret.{0,20}[\'"][0-9a-zA-Z/+]{40}[\'"]'), "critical"),
    ("GitHub Token", re.compile(r'gh[ps]_[A-Za-z0-9_]{36,}'), "critical"),
    ("Generic API Key", re.compile(r'(?i)(?:api[_-]?key|apikey)\s*[=:]\s*[\'"][a-zA-Z0-9]{20,}[\'"]'), "high"),
    ("Generic Secret", re.compile(r'(?i)(?:secret|password|passwd|pwd)\s*[=:]\s*[\'"][^\'"]{8,}[\'"]'), "high"),
    ("Private Key Header", re.compile(r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----'), "critical"),
    ("JWT Token", re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'), "high"),
    ("Slack Token", re.compile(r'xox[bpors]-[0-9]{10,}-[a-zA-Z0-9-]+'), "critical"),
    ("Database URL with password", re.compile(r'(?i)(?:postgres|mysql|mongodb)://\w+:[^@\s]{3,}@'), "critical"),
    ("Hardcoded IP", re.compile(r'\b(?:10|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b'), "low"),
]

# Insecure code patterns
INSECURE_PATTERNS: list[tuple[str, re.Pattern, str, str]] = [
    ("SQL Injection risk", re.compile(r'(?i)(?:execute|cursor\.execute)\s*\(\s*[f"\'].*%s'), "high", "Use parameterized queries"),
    ("Eval usage", re.compile(r'\beval\s*\('), "high", "Avoid eval() — use safe alternatives"),
    ("Shell injection risk", re.compile(r'(?i)(?:os\.system|subprocess\.call)\s*\(.*\+'), "high", "Use subprocess with list args"),
    ("Debug mode in production", re.compile(r'(?i)DEBUG\s*=\s*True'), "medium", "Ensure DEBUG=False in production"),
    ("CORS allow all", re.compile(r'(?i)(?:allow_origins|cors_origins)\s*=\s*\[?\s*[\'\"]\*[\'\"]'), "medium", "Restrict CORS origins"),
    ("HTTP (not HTTPS)", re.compile(r'http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)'), "low", "Use HTTPS for external URLs"),
]

# Files that should NOT be committed
SENSITIVE_FILES = {
    ".env", ".env.local", ".env.production", ".env.staging",
    "id_rsa", "id_ed25519", "id_dsa",
    "credentials.json", "service-account.json",
    "secrets.yaml", "secrets.yml",
}


def scan_security(root: str) -> list[SecurityFinding]:
    """Scan a project directory for security issues."""
    root_path = Path(root).resolve()
    findings: list[SecurityFinding] = []

    if not root_path.is_dir():
        return findings

    # Check for sensitive files that shouldn't be committed
    for path in root_path.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue

        if path.name in SENSITIVE_FILES:
            findings.append(SecurityFinding(
                severity="critical",
                category="sensitive_file",
                file=str(path.relative_to(root_path)),
                line=0,
                message=f"Sensitive file '{path.name}' found — should not be committed",
                context=f"Add '{path.name}' to .gitignore",
            ))

    # Check .gitignore for missing entries
    gitignore = root_path / ".gitignore"
    if gitignore.exists():
        gi_content = gitignore.read_text(errors="replace")
        for sf in (".env", "*.pem", "*.key"):
            if sf not in gi_content:
                findings.append(SecurityFinding(
                    severity="medium",
                    category="gitignore_missing",
                    file=".gitignore",
                    line=0,
                    message=f"'{sf}' not in .gitignore — sensitive files may be committed",
                    context=f"Add '{sf}' to .gitignore",
                ))

    # Scan source files
    for path in root_path.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in BINARY_EXTENSIONS:
            continue
        if path.stat().st_size > 500_000:  # skip files > 500KB
            continue

        try:
            content = path.read_text(errors="replace")
        except OSError:
            continue

        rel = str(path.relative_to(root_path))
        lines = content.split("\n")

        for i, line in enumerate(lines):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith(("#", "//", "/*", "*", "<!--")):
                continue

            # Secret patterns
            for name, pattern, severity in SECRET_PATTERNS:
                if pattern.search(line):
                    # Skip test files and examples
                    if any(x in rel.lower() for x in ("test", "spec", "example", "mock", "fixture")):
                        continue
                    findings.append(SecurityFinding(
                        severity=severity,
                        category="hardcoded_secret",
                        file=rel,
                        line=i + 1,
                        message=f"Possible {name} detected",
                        context=stripped,
                    ))

            # Insecure patterns
            for name, pattern, severity, fix in INSECURE_PATTERNS:
                if pattern.search(line):
                    findings.append(SecurityFinding(
                        severity=severity,
                        category="insecure_code",
                        file=rel,
                        line=i + 1,
                        message=f"{name} — {fix}",
                        context=stripped,
                    ))

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda f: severity_order.get(f.severity, 99))

    return findings
