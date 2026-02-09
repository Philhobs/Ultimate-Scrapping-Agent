"""check_defenses MCP tool — evaluate existing security controls and suggest improvements."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from redteam_agent.state import get_target, add_defense_eval

SKIP_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build", "vendor"}


@tool(
    "check_defenses",
    "Evaluate existing security controls: input validation, output encoding, CSP headers, "
    "rate limiting, error handling, logging, and dependency security. "
    "Scores each defense area and suggests improvements. Uses scanned target or provide 'path'.",
    {"path": str},
)
async def check_defenses(args: dict[str, Any]) -> dict[str, Any]:
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
    all_content = ""
    file_list: list[str] = []

    for file_path in root.rglob("*"):
        if any(skip in file_path.parts for skip in SKIP_DIRS):
            continue
        if not file_path.is_file():
            continue
        if file_path.suffix in (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rb"):
            try:
                all_content += file_path.read_text(errors="replace") + "\n"
                file_list.append(str(file_path.relative_to(root)))
            except OSError:
                continue

    evaluations: list[dict] = []

    # 1. Input Validation
    evaluations.append(_check_input_validation(all_content))

    # 2. Output Encoding
    evaluations.append(_check_output_encoding(all_content))

    # 3. Authentication
    evaluations.append(_check_authentication(all_content))

    # 4. Error Handling
    evaluations.append(_check_error_handling(all_content))

    # 5. Logging
    evaluations.append(_check_logging(all_content))

    # 6. Dependency Security
    evaluations.append(_check_dependencies(root))

    # 7. Security Headers
    evaluations.append(_check_security_headers(all_content))

    # 8. Rate Limiting
    evaluations.append(_check_rate_limiting(all_content))

    # 9. HTTPS/TLS
    evaluations.append(_check_https(all_content))

    # 10. Secrets Management
    evaluations.append(_check_secrets_management(all_content, root))

    # Store evaluations
    for ev in evaluations:
        add_defense_eval(ev)

    # Calculate overall score
    scores = [ev["score"] for ev in evaluations]
    overall = round(sum(scores) / len(scores)) if scores else 0

    grade = "A" if overall >= 90 else "B" if overall >= 75 else "C" if overall >= 60 else "D" if overall >= 40 else "F"

    result = {
        "overall_score": f"{overall}/100 ({grade})",
        "total_areas_checked": len(evaluations),
        "evaluations": evaluations,
        "priority_improvements": [
            ev["area"] for ev in sorted(evaluations, key=lambda x: x["score"])
            if ev["score"] < 60
        ],
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _check_input_validation(content: str) -> dict:
    indicators = [
        ("schema validation", bool(re.search(r"(?:pydantic|marshmallow|joi|yup|zod|cerberus|voluptuous)", content, re.I))),
        ("type checking", bool(re.search(r"(?:isinstance|typeof|type\s+assertion)", content))),
        ("regex validation", bool(re.search(r"(?:re\.match|re\.search|\.test\(|RegExp)", content))),
        ("length checks", bool(re.search(r"(?:len\(|\.length|maxlength|minlength)", content, re.I))),
        ("sanitization", bool(re.search(r"(?:sanitize|escape|strip_tags|bleach|DOMPurify)", content, re.I))),
    ]
    present = sum(1 for _, v in indicators if v)
    score = min(100, present * 20)
    return {
        "area": "Input Validation",
        "score": score,
        "checks": {name: "present" if val else "missing" for name, val in indicators},
        "recommendation": "Add schema validation (Pydantic/Joi/Zod), sanitize all user inputs." if score < 60 else "Good input validation coverage.",
    }


def _check_output_encoding(content: str) -> dict:
    indicators = [
        ("template auto-escaping", bool(re.search(r"(?:autoescape|Jinja2|mustache|handlebars|React)", content, re.I))),
        ("html escaping", bool(re.search(r"(?:escape|markupsafe|html\.escape|encode)", content, re.I))),
        ("json encoding", bool(re.search(r"(?:json\.dumps|JSON\.stringify|jsonify)", content))),
        ("no innerHTML", not bool(re.search(r"innerHTML\s*=", content))),
    ]
    present = sum(1 for _, v in indicators if v)
    score = min(100, present * 25)
    return {
        "area": "Output Encoding",
        "score": score,
        "checks": {name: "present" if val else "missing" for name, val in indicators},
        "recommendation": "Use auto-escaping templates. Never use innerHTML. Encode all outputs." if score < 60 else "Good output encoding.",
    }


def _check_authentication(content: str) -> dict:
    indicators = [
        ("password hashing", bool(re.search(r"(?:bcrypt|argon2|scrypt|pbkdf2)", content, re.I))),
        ("jwt handling", bool(re.search(r"(?:jwt|jsonwebtoken|jose)", content, re.I))),
        ("session management", bool(re.search(r"(?:session|cookie.*secure|httponly)", content, re.I))),
        ("auth middleware", bool(re.search(r"(?:login_required|authenticated|isAuth|passport|guard)", content, re.I))),
        ("csrf protection", bool(re.search(r"(?:csrf|csrfprotect|csurf)", content, re.I))),
    ]
    present = sum(1 for _, v in indicators if v)
    score = min(100, present * 20)
    return {
        "area": "Authentication & Authorization",
        "score": score,
        "checks": {name: "present" if val else "missing" for name, val in indicators},
        "recommendation": "Use bcrypt for passwords, validate JWTs strictly, add CSRF protection." if score < 60 else "Decent auth controls.",
    }


def _check_error_handling(content: str) -> dict:
    indicators = [
        ("try-catch blocks", bool(re.search(r"(?:try\s*:|try\s*\{|rescue|catch)", content))),
        ("custom error handler", bool(re.search(r"(?:error_handler|errorHandler|@app\.errorhandler)", content))),
        ("no stack traces exposed", not bool(re.search(r"(?:traceback\.print|console\.error.*stack|DEBUG.*True)", content))),
        ("graceful shutdown", bool(re.search(r"(?:signal\.signal|process\.on\(['""]SIGTERM|graceful)", content, re.I))),
    ]
    present = sum(1 for _, v in indicators if v)
    score = min(100, present * 25)
    return {
        "area": "Error Handling",
        "score": score,
        "checks": {name: "present" if val else "missing" for name, val in indicators},
        "recommendation": "Add global error handler. Never expose stack traces in production." if score < 60 else "Good error handling.",
    }


def _check_logging(content: str) -> dict:
    indicators = [
        ("structured logging", bool(re.search(r"(?:logging\.|logger\.|winston|pino|bunyan|log\.)", content))),
        ("security events", bool(re.search(r"(?:login.*log|auth.*log|failed.*attempt)", content, re.I))),
        ("no sensitive data logged", not bool(re.search(r"(?:log.*password|log.*secret|log.*token)", content, re.I))),
    ]
    present = sum(1 for _, v in indicators if v)
    score = min(100, present * 33)
    return {
        "area": "Logging & Monitoring",
        "score": score,
        "checks": {name: "present" if val else "missing" for name, val in indicators},
        "recommendation": "Add structured logging. Log auth events. Never log sensitive data." if score < 60 else "Logging looks reasonable.",
    }


def _check_dependencies(root: Path) -> dict:
    checks: dict[str, str] = {}

    # Lock files
    lock_files = ["requirements.txt", "Pipfile.lock", "poetry.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "go.sum"]
    has_lock = any((root / lf).exists() for lf in lock_files)
    checks["dependency lock file"] = "present" if has_lock else "missing"

    # .npmrc / pip.conf security
    npmrc = root / ".npmrc"
    if npmrc.exists():
        content = npmrc.read_text(errors="replace")
        checks["npm audit"] = "configured" if "audit" in content else "not configured"

    # Dependabot / Renovate
    has_dep_bot = (root / ".github" / "dependabot.yml").exists() or (root / "renovate.json").exists()
    checks["automated dependency updates"] = "present" if has_dep_bot else "missing"

    present = sum(1 for v in checks.values() if v in ("present", "configured"))
    score = min(100, present * 33)
    return {
        "area": "Dependency Security",
        "score": score,
        "checks": checks,
        "recommendation": "Use lock files, enable Dependabot/Renovate, run npm audit regularly." if score < 60 else "Good dependency management.",
    }


def _check_security_headers(content: str) -> dict:
    indicators = [
        ("helmet/security middleware", bool(re.search(r"(?:helmet|secure_headers|SecurityMiddleware)", content, re.I))),
        ("CSP header", bool(re.search(r"(?:Content-Security-Policy|CSP)", content, re.I))),
        ("HSTS", bool(re.search(r"(?:Strict-Transport-Security|HSTS)", content, re.I))),
        ("X-Frame-Options", bool(re.search(r"(?:X-Frame-Options|DENY|SAMEORIGIN)", content))),
    ]
    present = sum(1 for _, v in indicators if v)
    score = min(100, present * 25)
    return {
        "area": "Security Headers",
        "score": score,
        "checks": {name: "present" if val else "missing" for name, val in indicators},
        "recommendation": "Add helmet (Express) or SecurityMiddleware (Django). Set CSP, HSTS, X-Frame-Options." if score < 60 else "Good header coverage.",
    }


def _check_rate_limiting(content: str) -> dict:
    indicators = [
        ("rate limiter", bool(re.search(r"(?:ratelimit|rate_limit|RateLimiter|throttle|slowDown)", content, re.I))),
        ("login rate limit", bool(re.search(r"(?:login.*limit|auth.*throttle|brute.*force)", content, re.I))),
    ]
    present = sum(1 for _, v in indicators if v)
    score = min(100, present * 50)
    return {
        "area": "Rate Limiting",
        "score": score,
        "checks": {name: "present" if val else "missing" for name, val in indicators},
        "recommendation": "Add rate limiting to auth endpoints and APIs (Flask-Limiter, express-rate-limit)." if score < 60 else "Rate limiting present.",
    }


def _check_https(content: str) -> dict:
    indicators = [
        ("https enforcement", bool(re.search(r"(?:https|ssl|tls|redirect.*https|force_https|SECURE_SSL_REDIRECT)", content, re.I))),
        ("no http hardcoded", not bool(re.search(r"""http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)""", content))),
    ]
    present = sum(1 for _, v in indicators if v)
    score = min(100, present * 50)
    return {
        "area": "HTTPS/TLS",
        "score": score,
        "checks": {name: "present" if val else "missing" for name, val in indicators},
        "recommendation": "Enforce HTTPS. Redirect HTTP to HTTPS. No hardcoded HTTP URLs." if score < 60 else "HTTPS looks good.",
    }


def _check_secrets_management(content: str, root: Path) -> dict:
    indicators = [
        ("env vars for secrets", bool(re.search(r"(?:os\.environ|process\.env|os\.Getenv|dotenv)", content))),
        (".env in gitignore", _env_in_gitignore(root)),
        ("no hardcoded secrets", not bool(re.search(r"""(?:password|secret|api_key)\s*=\s*['""][^'""]{10,}""", content, re.I))),
        ("secrets manager", bool(re.search(r"(?:vault|aws.*secrets|SecretClient|KeyVault)", content, re.I))),
    ]
    present = sum(1 for _, v in indicators if v)
    score = min(100, present * 25)
    return {
        "area": "Secrets Management",
        "score": score,
        "checks": {name: "present" if val else "missing" for name, val in indicators},
        "recommendation": "Use env vars or a secrets manager. Add .env to .gitignore. No hardcoded secrets." if score < 60 else "Good secrets handling.",
    }


def _env_in_gitignore(root: Path) -> bool:
    gi = root / ".gitignore"
    if gi.exists():
        return ".env" in gi.read_text(errors="replace")
    return False
