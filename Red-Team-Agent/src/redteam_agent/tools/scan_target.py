"""scan_target MCP tool — reconnaissance: map the attack surface of a project."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from redteam_agent.state import set_target

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build",
    "vendor", "target", ".mypy_cache",
}

SOURCE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rb", ".java", ".php"}


@tool(
    "scan_target",
    "Reconnaissance: scan a codebase to identify the attack surface — endpoints, "
    "input handlers, auth mechanisms, data flows, external calls, and tech stack. "
    "Provide 'path' to the project root.",
    {"path": str},
)
async def scan_target(args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path", ".")
    root = Path(path).resolve()

    if not root.is_dir():
        return {
            "content": [{"type": "text", "text": f"Error: Not a directory: {path}"}],
            "is_error": True,
        }

    # Gather target info
    info: dict[str, Any] = {
        "root": str(root),
        "name": root.name,
        "language": "unknown",
        "framework": None,
        "endpoints": [],
        "input_handlers": [],
        "auth_mechanisms": [],
        "external_calls": [],
        "env_vars": [],
        "sensitive_files": [],
        "tech_stack": [],
        "total_files": 0,
        "total_lines": 0,
    }

    lang_counts: dict[str, int] = {}
    endpoints: list[dict] = []
    input_handlers: list[dict] = []
    auth_refs: list[dict] = []
    external_calls: list[dict] = []
    env_vars: set[str] = set()

    for file_path in root.rglob("*"):
        if any(skip in file_path.parts for skip in SKIP_DIRS):
            continue
        if not file_path.is_file() or file_path.suffix not in SOURCE_EXTS:
            continue

        try:
            content = file_path.read_text(errors="replace")
        except OSError:
            continue

        rel = str(file_path.relative_to(root))
        lines = content.split("\n")
        lang = _detect_lang(file_path.suffix)
        lang_counts[lang] = lang_counts.get(lang, 0) + len(lines)
        info["total_files"] += 1
        info["total_lines"] += len(lines)

        for i, line in enumerate(lines, 1):
            # Find endpoints (routes/handlers)
            ep = _find_endpoint(line, rel, i, lang)
            if ep:
                endpoints.append(ep)

            # Find input handling
            inp = _find_input_handler(line, rel, i, lang)
            if inp:
                input_handlers.append(inp)

            # Find auth references
            auth = _find_auth(line, rel, i)
            if auth:
                auth_refs.append(auth)

            # Find external calls
            ext = _find_external_call(line, rel, i)
            if ext:
                external_calls.append(ext)

            # Find env var usage
            env_matches = re.findall(r"""(?:os\.environ|process\.env|os\.Getenv)\[?\.?['""]?(\w+)""", line)
            for e in env_matches:
                env_vars.add(e)

    # Detect primary language and framework
    if lang_counts:
        info["language"] = max(lang_counts, key=lang_counts.get)

    info["framework"] = _detect_framework(root)
    info["endpoints"] = endpoints[:50]
    info["input_handlers"] = input_handlers[:30]
    info["auth_mechanisms"] = auth_refs[:20]
    info["external_calls"] = external_calls[:30]
    info["env_vars"] = sorted(env_vars)
    info["sensitive_files"] = _find_sensitive_files(root)
    info["tech_stack"] = _detect_tech_stack(root)

    set_target(info)

    # Summary for the agent
    summary = {
        "name": info["name"],
        "language": info["language"],
        "framework": info["framework"],
        "total_files": info["total_files"],
        "total_lines": info["total_lines"],
        "endpoints_found": len(endpoints),
        "input_handlers_found": len(input_handlers),
        "auth_references": len(auth_refs),
        "external_calls": len(external_calls),
        "env_vars": len(env_vars),
        "sensitive_files": len(info["sensitive_files"]),
        "tech_stack": info["tech_stack"],
        "endpoints": endpoints[:20],
        "input_handlers": input_handlers[:10],
        "auth_mechanisms": auth_refs[:10],
        "external_calls": external_calls[:10],
        "sensitive_files_list": info["sensitive_files"][:10],
    }

    return {"content": [{"type": "text", "text": json.dumps(summary, indent=2)}]}


def _detect_lang(suffix: str) -> str:
    return {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "javascript", ".tsx": "typescript", ".go": "go",
        ".rb": "ruby", ".java": "java", ".php": "php",
    }.get(suffix, "unknown")


def _find_endpoint(line: str, file: str, line_num: int, lang: str) -> dict | None:
    """Detect API endpoint definitions."""
    patterns = [
        (r"""@app\.(?:route|get|post|put|delete|patch)\s*\(['""]([^'""]+)""", "flask/fastapi"),
        (r"""@(?:api_view|action)\s*\(\[?['""](\w+)""", "django"),
        (r"""router\.(?:get|post|put|delete|patch)\s*\(['""]([^'""]+)""", "express"),
        (r"""app\.(?:get|post|put|delete|patch)\s*\(['""]([^'""]+)""", "express"),
        (r"""@(?:Get|Post|Put|Delete|Patch)Mapping\s*\(['""]?([^'"")\s]+)""", "spring"),
        (r"""(?:Get|Post|Put|Delete)\s*\(['""]([^'""]+)""", "go/gin"),
    ]
    for pat, fw in patterns:
        m = re.search(pat, line)
        if m:
            method = "unknown"
            for meth in ("get", "post", "put", "delete", "patch"):
                if meth in line.lower():
                    method = meth.upper()
                    break
            return {"path": m.group(1), "method": method, "file": file, "line": line_num, "framework": fw}
    return None


def _find_input_handler(line: str, file: str, line_num: int, lang: str) -> dict | None:
    """Detect user input handling."""
    patterns = [
        (r"""request\.(?:form|args|json|data|files|get_json|values)\b""", "flask_request"),
        (r"""request\.(?:body|params|query|cookies|headers)\b""", "express_request"),
        (r"""request\.(?:GET|POST|FILES|META|COOKIES)\b""", "django_request"),
        (r"""input\s*\(""", "stdin_input"),
        (r"""sys\.argv""", "cli_args"),
        (r"""(?:FormData|URLSearchParams|document\.getElementById)""", "dom_input"),
    ]
    for pat, input_type in patterns:
        if re.search(pat, line):
            return {"type": input_type, "file": file, "line": line_num, "code": line.strip()[:100]}
    return None


def _find_auth(line: str, file: str, line_num: int) -> dict | None:
    """Detect authentication/authorization references."""
    patterns = [
        (r"""(?:login|authenticate|verify_password|check_password)""", "auth_function"),
        (r"""(?:jwt\.(?:encode|decode|verify)|jsonwebtoken)""", "jwt"),
        (r"""(?:session|cookie)\b.*(?:set|get|create|destroy)""", "session"),
        (r"""(?:bcrypt|argon2|scrypt|pbkdf2)""", "password_hash"),
        (r"""(?:OAuth|oauth|Bearer|bearer|Authorization)""", "oauth_bearer"),
        (r"""(?:@login_required|@auth|@authenticated|isAuthenticated)""", "auth_decorator"),
        (r"""(?:CORS|cors|Access-Control)""", "cors"),
    ]
    for pat, auth_type in patterns:
        if re.search(pat, line, re.IGNORECASE):
            return {"type": auth_type, "file": file, "line": line_num, "code": line.strip()[:100]}
    return None


def _find_external_call(line: str, file: str, line_num: int) -> dict | None:
    """Detect external HTTP calls, DB queries, etc."""
    patterns = [
        (r"""(?:requests\.(?:get|post|put|delete)|httpx\.|fetch\(|axios\.)""", "http_call"),
        (r"""(?:\.execute|\.query|\.raw|\.find\(|\.aggregate\()""", "db_query"),
        (r"""(?:subprocess\.|os\.system|exec\.|child_process)""", "command_exec"),
        (r"""(?:open\(|readFile|writeFile|fs\.)""", "file_io"),
        (r"""(?:smtp|sendmail|send_email|ses\.send)""", "email"),
    ]
    for pat, call_type in patterns:
        if re.search(pat, line):
            return {"type": call_type, "file": file, "line": line_num, "code": line.strip()[:100]}
    return None


def _find_sensitive_files(root: Path) -> list[str]:
    """Find sensitive files in the project."""
    sensitive_patterns = [
        ".env", ".env.local", ".env.production",
        "id_rsa", "id_ed25519", "*.pem", "*.key",
        "credentials.json", "service-account*.json",
        ".htpasswd", "wp-config.php", "secrets.*",
    ]
    found: list[str] = []
    for pattern in sensitive_patterns:
        for f in root.rglob(pattern):
            if ".git" not in f.parts and not any(skip in f.parts for skip in SKIP_DIRS):
                found.append(str(f.relative_to(root)))
    return found


def _detect_framework(root: Path) -> str | None:
    """Detect the web framework."""
    checks = [
        ("requirements.txt", [("fastapi", "fastapi"), ("flask", "flask"), ("django", "django")]),
        ("package.json", [("express", "express"), ("next", "next.js"), ("@nestjs", "nest.js"), ("koa", "koa")]),
        ("go.mod", [("gin-gonic", "gin"), ("echo", "echo"), ("fiber", "fiber")]),
        ("Gemfile", [("rails", "rails"), ("sinatra", "sinatra")]),
    ]
    for config, pairs in checks:
        path = root / config
        if path.exists():
            try:
                content = path.read_text(errors="replace").lower()
                for keyword, name in pairs:
                    if keyword in content:
                        return name
            except OSError:
                continue
    return None


def _detect_tech_stack(root: Path) -> list[str]:
    """Detect technology stack from config files."""
    stack: list[str] = []
    file_indicators = {
        "Dockerfile": "Docker",
        "docker-compose.yml": "Docker Compose",
        ".github/workflows": "GitHub Actions",
        ".gitlab-ci.yml": "GitLab CI",
        "Jenkinsfile": "Jenkins",
        "terraform": "Terraform",
        "k8s": "Kubernetes",
        "nginx.conf": "Nginx",
        "redis.conf": "Redis",
        ".eslintrc": "ESLint",
        "tsconfig.json": "TypeScript",
        "pyproject.toml": "Python",
        "package.json": "Node.js",
        "go.mod": "Go",
        "Cargo.toml": "Rust",
    }
    for indicator, tech in file_indicators.items():
        if (root / indicator).exists():
            stack.append(tech)
    return stack
