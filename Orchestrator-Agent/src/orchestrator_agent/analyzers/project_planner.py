"""Project planning analyzer.

Generates architecture, tech-stack recommendations, file structures,
milestones, and dependency graphs from a natural-language project description.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Tech-stack presets
# ---------------------------------------------------------------------------

STACK_PRESETS: dict[str, dict[str, list[str]]] = {
    "python-api": {
        "language": ["Python 3.12"],
        "framework": ["FastAPI"],
        "database": ["PostgreSQL", "SQLAlchemy"],
        "testing": ["pytest", "httpx"],
        "tooling": ["ruff", "mypy"],
        "deployment": ["Docker", "uvicorn"],
    },
    "python-cli": {
        "language": ["Python 3.12"],
        "framework": ["Typer", "Rich"],
        "testing": ["pytest"],
        "tooling": ["ruff", "mypy"],
        "deployment": ["pip / pipx"],
    },
    "node-api": {
        "language": ["TypeScript 5"],
        "framework": ["Express", "Zod"],
        "database": ["PostgreSQL", "Prisma"],
        "testing": ["vitest", "supertest"],
        "tooling": ["eslint", "prettier"],
        "deployment": ["Docker", "node"],
    },
    "react-app": {
        "language": ["TypeScript 5"],
        "framework": ["React 18", "Vite"],
        "testing": ["vitest", "testing-library"],
        "tooling": ["eslint", "prettier"],
        "deployment": ["Docker", "nginx"],
    },
    "fullstack-node": {
        "language": ["TypeScript 5"],
        "framework": ["Next.js 14"],
        "database": ["PostgreSQL", "Prisma"],
        "testing": ["vitest", "playwright"],
        "tooling": ["eslint", "prettier"],
        "deployment": ["Docker", "Vercel"],
    },
    "go-api": {
        "language": ["Go 1.22"],
        "framework": ["net/http", "chi"],
        "database": ["PostgreSQL", "pgx"],
        "testing": ["go test", "testify"],
        "tooling": ["golangci-lint"],
        "deployment": ["Docker", "scratch image"],
    },
}

# ---------------------------------------------------------------------------
# Project type heuristics
# ---------------------------------------------------------------------------

PROJECT_KEYWORDS: dict[str, list[str]] = {
    "api":       ["api", "rest", "endpoint", "server", "backend", "graphql"],
    "cli":       ["cli", "command", "terminal", "script", "tool"],
    "web":       ["web", "frontend", "react", "vue", "angular", "dashboard", "ui"],
    "fullstack": ["fullstack", "full-stack", "webapp", "saas", "app"],
    "library":   ["library", "package", "sdk", "module"],
    "bot":       ["bot", "discord", "slack", "telegram", "chatbot"],
}


def detect_project_type(description: str) -> str:
    """Return the best-guess project type from the description."""
    desc_lower = description.lower()
    scores: dict[str, int] = {}
    for ptype, keywords in PROJECT_KEYWORDS.items():
        scores[ptype] = sum(1 for kw in keywords if kw in desc_lower)
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "api"


def detect_language(description: str) -> str:
    """Detect the primary language from the description."""
    desc_lower = description.lower()
    lang_hints = {
        "python": ["python", "fastapi", "django", "flask", "typer", "pytest"],
        "typescript": ["typescript", "ts", "react", "next.js", "express", "node"],
        "javascript": ["javascript", "js", "node"],
        "go": ["go", "golang", "gin", "chi"],
        "rust": ["rust", "cargo", "tokio"],
    }
    for lang, hints in lang_hints.items():
        if any(h in desc_lower for h in hints):
            return lang
    return "python"


def suggest_stack(project_type: str, language: str) -> dict[str, list[str]]:
    """Return a suggested tech stack."""
    key_map = {
        ("api", "python"):     "python-api",
        ("cli", "python"):     "python-cli",
        ("api", "typescript"): "node-api",
        ("api", "javascript"): "node-api",
        ("web", "typescript"): "react-app",
        ("web", "javascript"): "react-app",
        ("fullstack", "typescript"): "fullstack-node",
        ("fullstack", "javascript"): "fullstack-node",
        ("api", "go"):         "go-api",
    }
    key = (project_type, language)
    preset_name = key_map.get(key, "python-api")
    return dict(STACK_PRESETS[preset_name])


# ---------------------------------------------------------------------------
# File-structure templates
# ---------------------------------------------------------------------------

FILE_STRUCTURES: dict[str, list[str]] = {
    "python-api": [
        "src/{name}/__init__.py",
        "src/{name}/main.py",
        "src/{name}/config.py",
        "src/{name}/models.py",
        "src/{name}/schemas.py",
        "src/{name}/routes/__init__.py",
        "src/{name}/routes/health.py",
        "src/{name}/services/__init__.py",
        "src/{name}/db.py",
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/test_health.py",
        "pyproject.toml",
        ".gitignore",
        "Dockerfile",
    ],
    "python-cli": [
        "src/{name}/__init__.py",
        "src/{name}/cli.py",
        "src/{name}/core.py",
        "src/{name}/utils.py",
        "tests/__init__.py",
        "tests/test_core.py",
        "pyproject.toml",
        ".gitignore",
    ],
    "node-api": [
        "src/index.ts",
        "src/config.ts",
        "src/routes/index.ts",
        "src/routes/health.ts",
        "src/middleware/error.ts",
        "src/services/.gitkeep",
        "tests/health.test.ts",
        "package.json",
        "tsconfig.json",
        ".gitignore",
        "Dockerfile",
    ],
    "react-app": [
        "src/main.tsx",
        "src/App.tsx",
        "src/components/.gitkeep",
        "src/hooks/.gitkeep",
        "src/pages/.gitkeep",
        "src/styles/global.css",
        "tests/App.test.tsx",
        "index.html",
        "package.json",
        "tsconfig.json",
        "vite.config.ts",
        ".gitignore",
        "Dockerfile",
    ],
    "fullstack-node": [
        "src/app/layout.tsx",
        "src/app/page.tsx",
        "src/app/api/health/route.ts",
        "src/components/.gitkeep",
        "src/lib/db.ts",
        "prisma/schema.prisma",
        "tests/health.test.ts",
        "package.json",
        "tsconfig.json",
        "next.config.js",
        ".gitignore",
        "Dockerfile",
    ],
    "go-api": [
        "cmd/server/main.go",
        "internal/config/config.go",
        "internal/handler/health.go",
        "internal/handler/router.go",
        "internal/model/.gitkeep",
        "internal/service/.gitkeep",
        "internal/db/db.go",
        "tests/health_test.go",
        "go.mod",
        ".gitignore",
        "Dockerfile",
    ],
}


def generate_file_structure(preset: str, project_name: str) -> list[str]:
    """Return a list of file paths for the project."""
    template = FILE_STRUCTURES.get(preset, FILE_STRUCTURES["python-api"])
    safe_name = project_name.replace("-", "_").replace(" ", "_").lower()
    return [f.format(name=safe_name) for f in template]


# ---------------------------------------------------------------------------
# Milestone generation
# ---------------------------------------------------------------------------

@dataclass
class Milestone:
    """A project milestone."""
    phase: int
    name: str
    description: str
    deliverables: list[str] = field(default_factory=list)


DEFAULT_MILESTONES: list[Milestone] = [
    Milestone(1, "Setup & Scaffolding",
              "Initialize project, install deps, create structure",
              ["Project directory", "Dependencies installed", "Basic config"]),
    Milestone(2, "Core Implementation",
              "Build the main business logic and data models",
              ["Models/schemas", "Core services", "Database layer"]),
    Milestone(3, "API / Interface",
              "Wire up routes, CLI commands, or UI components",
              ["Endpoints or commands", "Input validation", "Error handling"]),
    Milestone(4, "Testing",
              "Write and run unit and integration tests",
              ["Unit tests", "Integration tests", "Coverage report"]),
    Milestone(5, "Review & Polish",
              "Code review, refactoring, documentation",
              ["Clean code", "README", "API docs"]),
    Milestone(6, "Deployment",
              "Dockerfile, CI/CD, deploy scripts",
              ["Dockerfile", "CI pipeline", "Deploy instructions"]),
]


def build_milestones() -> list[dict]:
    """Return milestones as dicts."""
    return [
        {
            "phase": m.phase,
            "name": m.name,
            "description": m.description,
            "deliverables": m.deliverables,
        }
        for m in DEFAULT_MILESTONES
    ]


# ---------------------------------------------------------------------------
# Top-level planner
# ---------------------------------------------------------------------------

def create_project_plan(
    description: str,
    project_name: str = "my-project",
) -> dict:
    """Build a complete project plan from a description."""
    project_type = detect_project_type(description)
    language = detect_language(description)
    stack = suggest_stack(project_type, language)

    # Pick the preset key used for file structure
    preset_key = {
        ("api", "python"):     "python-api",
        ("cli", "python"):     "python-cli",
        ("api", "typescript"): "node-api",
        ("api", "javascript"): "node-api",
        ("web", "typescript"): "react-app",
        ("web", "javascript"): "react-app",
        ("fullstack", "typescript"): "fullstack-node",
        ("fullstack", "javascript"): "fullstack-node",
        ("api", "go"):         "go-api",
    }.get((project_type, language), "python-api")

    files = generate_file_structure(preset_key, project_name)
    milestones = build_milestones()

    return {
        "project_name": project_name,
        "description": description,
        "project_type": project_type,
        "language": language,
        "tech_stack": stack,
        "file_structure": files,
        "milestones": milestones,
        "preset": preset_key,
    }
