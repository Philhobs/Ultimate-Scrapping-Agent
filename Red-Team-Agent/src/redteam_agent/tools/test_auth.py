"""test_auth MCP tool — analyze authentication and authorization code for weaknesses."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from redteam_agent.state import get_target, add_payload_result

SKIP_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build", "vendor"}


@tool(
    "test_auth",
    "Analyze authentication and authorization code for weaknesses: session management, "
    "token handling, password policies, privilege escalation paths, CORS configuration, "
    "and CSRF protection. Uses scanned target or provide 'path'.",
    {"path": str},
)
async def test_auth(args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path")
    if not path:
        try:
            target = get_target()
            path = target["root"]
        except RuntimeError:
            return {
                "content": [{"type": "text", "text": "Error: Provide 'path' or run scan_target first."}],
                "is_error": True,
            }

    root = Path(path).resolve()
    findings: list[dict] = []

    for file_path in root.rglob("*"):
        if any(skip in file_path.parts for skip in SKIP_DIRS):
            continue
        if not file_path.is_file():
            continue
        if file_path.suffix not in (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rb", ".java", ".php"):
            continue

        try:
            content = file_path.read_text(errors="replace")
        except OSError:
            continue

        rel = str(file_path.relative_to(root))
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            for check in AUTH_CHECKS:
                if check["pattern"].search(line):
                    findings.append({
                        "category": check["category"],
                        "severity": check["severity"],
                        "issue": check["issue"],
                        "file": rel,
                        "line": i,
                        "code": line.strip()[:150],
                        "remediation": check["remediation"],
                    })

    # Check for missing auth patterns
    all_content = ""
    for file_path in root.rglob("*.py"):
        if any(skip in file_path.parts for skip in SKIP_DIRS):
            continue
        try:
            all_content += file_path.read_text(errors="replace") + "\n"
        except OSError:
            continue

    missing_checks = _check_missing_auth(all_content, root)
    findings.extend(missing_checks)

    add_payload_result({
        "tool": "test_auth",
        "findings": len(findings),
    })

    # Group by category
    by_category: dict[str, list[dict]] = {}
    for f in findings:
        by_category.setdefault(f["category"], []).append(f)

    # Score
    critical = sum(1 for f in findings if f["severity"] == "critical")
    high = sum(1 for f in findings if f["severity"] == "high")
    medium = sum(1 for f in findings if f["severity"] == "medium")

    result = {
        "total_findings": len(findings),
        "critical": critical,
        "high": high,
        "medium": medium,
        "by_category": {k: len(v) for k, v in by_category.items()},
        "findings": findings[:40],
        "auth_score": _auth_score(critical, high, medium),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


AUTH_CHECKS = [
    # Password handling
    {
        "pattern": re.compile(r"""(?:password|passwd)\s*==\s*""", re.IGNORECASE),
        "category": "password",
        "severity": "critical",
        "issue": "Plain text password comparison — no hashing.",
        "remediation": "Use bcrypt.checkpw() or argon2.verify() for password comparison.",
    },
    {
        "pattern": re.compile(r"""(?:md5|sha1)\s*\(.*(?:password|passwd)""", re.IGNORECASE),
        "category": "password",
        "severity": "high",
        "issue": "Weak hash for password (MD5/SHA1).",
        "remediation": "Use bcrypt, argon2, or scrypt for password hashing.",
    },
    # JWT issues
    {
        "pattern": re.compile(r"""(?:verify\s*=\s*False|algorithms\s*=\s*\[)"""),
        "category": "jwt",
        "severity": "critical",
        "issue": "JWT verification may be disabled or algorithm not restricted.",
        "remediation": "Always verify JWTs. Restrict to expected algorithms: algorithms=['HS256']",
    },
    {
        "pattern": re.compile(r"""jwt\.(?:encode|decode).*(?:secret|key)\s*=\s*['""][^'""]{1,20}['""]"""),
        "category": "jwt",
        "severity": "high",
        "issue": "Short or hardcoded JWT secret.",
        "remediation": "Use a strong, randomly generated secret (256+ bits) from env vars.",
    },
    # Session management
    {
        "pattern": re.compile(r"""(?:session|cookie).*(?:httponly|secure|samesite)\s*=\s*False""", re.IGNORECASE),
        "category": "session",
        "severity": "high",
        "issue": "Session cookie missing security flags (HttpOnly/Secure/SameSite).",
        "remediation": "Set HttpOnly=True, Secure=True, SameSite='Strict' on session cookies.",
    },
    {
        "pattern": re.compile(r"""session\.permanent\s*=\s*True"""),
        "category": "session",
        "severity": "medium",
        "issue": "Permanent sessions enabled — long-lived sessions increase risk.",
        "remediation": "Use short session timeouts. Set PERMANENT_SESSION_LIFETIME appropriately.",
    },
    # CORS
    {
        "pattern": re.compile(r"""(?:Access-Control-Allow-Origin|CORS_ORIGINS?).*['""]?\*['""]?"""),
        "category": "cors",
        "severity": "high",
        "issue": "CORS allows all origins (*) — any site can make authenticated requests.",
        "remediation": "Restrict CORS to specific trusted origins. Never use * with credentials.",
    },
    {
        "pattern": re.compile(r"""(?:allow_credentials|supports_credentials)\s*=\s*True""", re.IGNORECASE),
        "category": "cors",
        "severity": "medium",
        "issue": "CORS credentials enabled — verify origin is restricted.",
        "remediation": "When using credentials, ensure origins are explicitly whitelisted (not *).",
    },
    # Rate limiting
    {
        "pattern": re.compile(r"""(?:login|authenticate|sign_in|signin)""", re.IGNORECASE),
        "category": "rate_limiting",
        "severity": "medium",
        "issue": "Auth endpoint — verify rate limiting is in place.",
        "remediation": "Implement rate limiting on login endpoints (e.g., Flask-Limiter, express-rate-limit).",
    },
    # Hardcoded credentials
    {
        "pattern": re.compile(r"""(?:admin|root)\s*[:=]\s*['""](?:admin|root|password|123456)['""]""", re.IGNORECASE),
        "category": "default_credentials",
        "severity": "critical",
        "issue": "Default/hardcoded admin credentials.",
        "remediation": "Remove default credentials. Force password change on first login.",
    },
    # SQL in auth
    {
        "pattern": re.compile(r"""(?:SELECT|WHERE).*(?:password|user).*(?:f['""]|%s|\.format)""", re.IGNORECASE),
        "category": "sql_auth",
        "severity": "critical",
        "issue": "SQL query with user/password using string formatting — auth bypass risk.",
        "remediation": "Use parameterized queries for all authentication SQL.",
    },
    # Insecure redirect
    {
        "pattern": re.compile(r"""redirect\s*\(.*(?:request|args|params|query)"""),
        "category": "open_redirect",
        "severity": "medium",
        "issue": "Redirect using user-controlled input — open redirect vulnerability.",
        "remediation": "Validate redirect URLs against an allowlist. Use relative paths only.",
    },
]


def _check_missing_auth(content: str, root: Path) -> list[dict]:
    """Check for missing security controls."""
    findings: list[dict] = []

    # No CSRF protection detected
    if "csrf" not in content.lower() and "csrfprotect" not in content.lower():
        findings.append({
            "category": "csrf",
            "severity": "medium",
            "issue": "No CSRF protection detected in the codebase.",
            "file": "(global)",
            "line": 0,
            "code": "",
            "remediation": "Implement CSRF tokens (Flask-WTF CSRFProtect, Django middleware, csurf for Express).",
        })

    # No rate limiting
    if "ratelimit" not in content.lower() and "rate_limit" not in content.lower() and "throttle" not in content.lower():
        findings.append({
            "category": "rate_limiting",
            "severity": "medium",
            "issue": "No rate limiting detected.",
            "file": "(global)",
            "line": 0,
            "code": "",
            "remediation": "Add rate limiting (Flask-Limiter, express-rate-limit, django-ratelimit).",
        })

    # No helmet/security headers (JS)
    if "helmet" not in content.lower() and "security-headers" not in content.lower():
        pkg = root / "package.json"
        if pkg.exists():
            findings.append({
                "category": "security_headers",
                "severity": "medium",
                "issue": "No security headers middleware detected (e.g., helmet).",
                "file": "(global)",
                "line": 0,
                "code": "",
                "remediation": "Use helmet middleware for Express: app.use(helmet())",
            })

    return findings


def _auth_score(critical: int, high: int, medium: int) -> str:
    """Calculate an auth security score."""
    penalty = critical * 25 + high * 10 + medium * 5
    score = max(0, 100 - penalty)
    if score >= 80:
        return f"{score}/100 (Good)"
    elif score >= 50:
        return f"{score}/100 (Needs Improvement)"
    else:
        return f"{score}/100 (Critical — immediate attention required)"
