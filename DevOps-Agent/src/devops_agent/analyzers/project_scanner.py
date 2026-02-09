"""Project scanner — detect language, framework, dependencies, and structure."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProjectProfile:
    """Profile of a scanned project."""
    root: str
    name: str
    language: str                             # primary language
    languages: list[str] = field(default_factory=list)
    framework: str = ""                       # detected framework
    package_manager: str = ""                 # pip, npm, cargo, go mod, etc.
    entry_point: str = ""                     # main file or script
    has_docker: bool = False
    has_ci: bool = False
    has_tests: bool = False
    has_git: bool = False
    dependencies: list[str] = field(default_factory=list)
    dev_dependencies: list[str] = field(default_factory=list)
    scripts: dict[str, str] = field(default_factory=dict)
    env_vars: list[str] = field(default_factory=list)
    ports: list[int] = field(default_factory=list)
    existing_files: dict[str, str] = field(default_factory=dict)  # filename -> rel path
    file_count: int = 0
    total_lines: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "language": self.language,
            "languages": self.languages,
            "framework": self.framework,
            "package_manager": self.package_manager,
            "entry_point": self.entry_point,
            "has_docker": self.has_docker,
            "has_ci": self.has_ci,
            "has_tests": self.has_tests,
            "has_git": self.has_git,
            "dependency_count": len(self.dependencies),
            "env_vars": self.env_vars,
            "ports": self.ports,
            "file_count": self.file_count,
            "total_lines": self.total_lines,
        }


# Language detection by file extension
LANG_EXTENSIONS = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".jsx": "javascript", ".go": "go",
    ".rs": "rust", ".java": "java", ".rb": "ruby", ".php": "php",
    ".cs": "csharp", ".cpp": "cpp", ".c": "c", ".swift": "swift",
    ".kt": "kotlin", ".scala": "scala", ".sh": "shell",
}

# Framework detection patterns
FRAMEWORK_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "python": [
        ("django", r"django"),
        ("flask", r"flask"),
        ("fastapi", r"fastapi"),
        ("streamlit", r"streamlit"),
        ("celery", r"celery"),
    ],
    "javascript": [
        ("next.js", r"next"),
        ("react", r"react"),
        ("express", r"express"),
        ("vue", r"vue"),
        ("angular", r"@angular"),
        ("nest.js", r"@nestjs"),
    ],
    "typescript": [
        ("next.js", r"next"),
        ("nest.js", r"@nestjs"),
        ("react", r"react"),
        ("angular", r"@angular"),
    ],
    "go": [("gin", r"gin-gonic"), ("fiber", r"gofiber"), ("echo", r"labstack/echo")],
    "rust": [("actix", r"actix"), ("rocket", r"rocket"), ("axum", r"axum")],
    "ruby": [("rails", r"rails"), ("sinatra", r"sinatra")],
}

SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", "target", ".tox", ".mypy_cache",
}


def scan_project(root: str) -> ProjectProfile:
    """Scan a project directory and build a profile."""
    root_path = Path(root).resolve()
    profile = ProjectProfile(root=str(root_path), name=root_path.name)

    if not root_path.is_dir():
        raise FileNotFoundError(f"Not a directory: {root}")

    # Detect git
    profile.has_git = (root_path / ".git").is_dir()

    # Count files by extension
    ext_counts: dict[str, int] = {}
    total_lines = 0
    file_count = 0

    for path in root_path.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue

        file_count += 1
        ext = path.suffix.lower()
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

        # Track important files
        name = path.name.lower()
        rel = str(path.relative_to(root_path))
        if name in ("dockerfile", "docker-compose.yml", "docker-compose.yaml"):
            profile.has_docker = True
            profile.existing_files[name] = rel
        elif name in (".github", "jenkinsfile", ".gitlab-ci.yml", ".circleci"):
            profile.has_ci = True
            profile.existing_files[name] = rel
        elif name in ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
                       "package.json", "cargo.toml", "go.mod", "gemfile",
                       "pom.xml", "build.gradle", "makefile", ".env.example"):
            profile.existing_files[name] = rel

        # Count lines for source files
        if ext in LANG_EXTENSIONS:
            try:
                total_lines += path.read_text(errors="replace").count("\n")
            except OSError:
                pass

    # Check for CI directory
    if (root_path / ".github" / "workflows").is_dir():
        profile.has_ci = True
        profile.existing_files[".github/workflows"] = ".github/workflows"

    # Check for tests
    profile.has_tests = any(
        (root_path / d).exists()
        for d in ("tests", "test", "spec", "specs", "__tests__")
    )

    profile.file_count = file_count
    profile.total_lines = total_lines

    # Primary language
    lang_scores: dict[str, int] = {}
    for ext, count in ext_counts.items():
        lang = LANG_EXTENSIONS.get(ext)
        if lang:
            lang_scores[lang] = lang_scores.get(lang, 0) + count

    if lang_scores:
        sorted_langs = sorted(lang_scores.items(), key=lambda x: x[1], reverse=True)
        profile.language = sorted_langs[0][0]
        profile.languages = [l for l, _ in sorted_langs]

    # Parse dependency files
    _parse_dependencies(root_path, profile)

    # Detect framework
    _detect_framework(profile)

    # Detect env vars and ports
    _detect_env_and_ports(root_path, profile)

    return profile


def _parse_dependencies(root: Path, profile: ProjectProfile) -> None:
    """Parse dependency files to get packages."""
    # Python
    req = root / "requirements.txt"
    if req.exists():
        profile.package_manager = "pip"
        for line in req.read_text(errors="replace").split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                profile.dependencies.append(line.split("==")[0].split(">=")[0].split("[")[0].strip())

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        profile.package_manager = profile.package_manager or "pip"
        content = pyproject.read_text(errors="replace")
        # Simple TOML parsing for dependencies
        in_deps = False
        for line in content.split("\n"):
            if "dependencies" in line and "=" in line and "[" in line:
                in_deps = True
                continue
            if in_deps:
                if line.strip().startswith("]"):
                    in_deps = False
                    continue
                dep = line.strip().strip('",').split(">=")[0].split("==")[0].strip()
                if dep:
                    profile.dependencies.append(dep)

    # Node.js
    pkg = root / "package.json"
    if pkg.exists():
        profile.package_manager = "npm"
        try:
            data = json.loads(pkg.read_text())
            profile.dependencies.extend(data.get("dependencies", {}).keys())
            profile.dev_dependencies.extend(data.get("devDependencies", {}).keys())
            profile.scripts = data.get("scripts", {})
            if "main" in data:
                profile.entry_point = data["main"]
        except (json.JSONDecodeError, KeyError):
            pass

    # Go
    gomod = root / "go.mod"
    if gomod.exists():
        profile.package_manager = "go"
        for line in gomod.read_text(errors="replace").split("\n"):
            if line.strip().startswith("require"):
                continue
            parts = line.strip().split()
            if len(parts) >= 1 and "/" in parts[0]:
                profile.dependencies.append(parts[0])

    # Rust
    cargo = root / "Cargo.toml"
    if cargo.exists():
        profile.package_manager = "cargo"

    # Detect entry point
    if not profile.entry_point:
        for candidate in ("main.py", "app.py", "server.py", "index.js", "index.ts",
                          "main.go", "main.rs", "src/main.py", "src/index.ts",
                          "src/app.py", "src/main.rs", "cmd/main.go"):
            if (root / candidate).exists():
                profile.entry_point = candidate
                break


def _detect_framework(profile: ProjectProfile) -> None:
    """Detect the framework from dependencies."""
    if profile.language not in FRAMEWORK_PATTERNS:
        return

    patterns = FRAMEWORK_PATTERNS[profile.language]
    all_deps = " ".join(profile.dependencies + profile.dev_dependencies).lower()

    for framework_name, pattern in patterns:
        if re.search(pattern, all_deps, re.IGNORECASE):
            profile.framework = framework_name
            return


def _detect_env_and_ports(root: Path, profile: ProjectProfile) -> None:
    """Detect environment variables and ports from config files."""
    # Check .env.example or .env.sample
    for env_file in (".env.example", ".env.sample", ".env.template"):
        path = root / env_file
        if path.exists():
            for line in path.read_text(errors="replace").split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    var = line.split("=")[0].strip()
                    if var:
                        profile.env_vars.append(var)

    # Detect ports from common patterns in source files
    port_pattern = re.compile(r'(?:PORT|port)\s*[=:]\s*(\d{4,5})')
    for ext in (".py", ".js", ".ts", ".go", ".env.example"):
        for path in root.rglob(f"*{ext}"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            try:
                content = path.read_text(errors="replace")
                for match in port_pattern.finditer(content):
                    port = int(match.group(1))
                    if 1024 < port < 65535 and port not in profile.ports:
                        profile.ports.append(port)
            except OSError:
                pass
