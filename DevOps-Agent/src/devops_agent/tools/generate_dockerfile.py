"""generate_dockerfile MCP tool — generate Dockerfile and docker-compose.yml."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from devops_agent.state import get_profile, store_generated, get_output_dir

# Base images by language
BASE_IMAGES = {
    "python": {"build": "python:3.12-slim", "runtime": "python:3.12-slim"},
    "javascript": {"build": "node:20-alpine", "runtime": "node:20-alpine"},
    "typescript": {"build": "node:20-alpine", "runtime": "node:20-alpine"},
    "go": {"build": "golang:1.22-alpine", "runtime": "alpine:3.19"},
    "rust": {"build": "rust:1.77-slim", "runtime": "debian:bookworm-slim"},
    "java": {"build": "eclipse-temurin:21-jdk", "runtime": "eclipse-temurin:21-jre"},
    "ruby": {"build": "ruby:3.3-slim", "runtime": "ruby:3.3-slim"},
}


@tool(
    "generate_dockerfile",
    "Generate a Dockerfile for the analyzed project. Uses multi-stage builds, "
    "non-root user, proper base images. Optional: 'include_compose' (true/false) "
    "to also generate docker-compose.yml. Optional 'base_image' override.",
    {"include_compose": str, "base_image": str},
)
async def generate_dockerfile(args: dict[str, Any]) -> dict[str, Any]:
    profile = get_profile()
    include_compose = args.get("include_compose", "true").lower() == "true"
    custom_base = args.get("base_image")

    lang = profile.language
    images = BASE_IMAGES.get(lang, {"build": "ubuntu:22.04", "runtime": "ubuntu:22.04"})
    build_image = custom_base or images["build"]
    runtime_image = images["runtime"]

    lines: list[str] = []
    lines.append(f"# ---- Build stage ----")
    lines.append(f"FROM {build_image} AS builder")
    lines.append("")
    lines.append("WORKDIR /app")
    lines.append("")

    if lang == "python":
        lines.append("# Install dependencies first for layer caching")
        if "requirements.txt" in profile.existing_files:
            lines.append("COPY requirements.txt .")
            lines.append("RUN pip install --no-cache-dir --user -r requirements.txt")
        elif "pyproject.toml" in profile.existing_files:
            lines.append("COPY pyproject.toml .")
            lines.append("RUN pip install --no-cache-dir --user .")
        lines.append("")
        lines.append("COPY . .")
        lines.append("")
        lines.append(f"# ---- Runtime stage ----")
        lines.append(f"FROM {runtime_image}")
        lines.append("")
        lines.append("# Create non-root user")
        lines.append("RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser")
        lines.append("")
        lines.append("WORKDIR /app")
        lines.append("COPY --from=builder /root/.local /root/.local")
        lines.append("COPY --from=builder /app .")
        lines.append("")
        lines.append("ENV PATH=/root/.local/bin:$PATH")
        lines.append("")
        lines.append("USER appuser")
        port = profile.ports[0] if profile.ports else 8000
        lines.append(f"EXPOSE {port}")
        lines.append("")
        entry = profile.entry_point or "app.py"
        if profile.framework == "fastapi":
            lines.append(f'CMD ["uvicorn", "{entry.replace(".py", "").replace("/", ".")}:app", "--host", "0.0.0.0", "--port", "{port}"]')
        elif profile.framework == "flask":
            lines.append(f'CMD ["python", "{entry}"]')
        elif profile.framework == "django":
            lines.append(f'CMD ["gunicorn", "--bind", "0.0.0.0:{port}", "{profile.name}.wsgi:application"]')
        else:
            lines.append(f'CMD ["python", "{entry}"]')

    elif lang in ("javascript", "typescript"):
        lines.append("# Install dependencies first for layer caching")
        lines.append("COPY package*.json ./")
        if "yarn.lock" in profile.existing_files:
            lines.append("RUN yarn install --frozen-lockfile")
        else:
            lines.append("RUN npm ci --only=production")
        lines.append("")
        lines.append("COPY . .")
        if lang == "typescript" or profile.framework in ("next.js",):
            lines.append("RUN npm run build")
        lines.append("")
        lines.append(f"# ---- Runtime stage ----")
        lines.append(f"FROM {runtime_image}")
        lines.append("")
        lines.append("RUN addgroup -S appuser && adduser -S appuser -G appuser")
        lines.append("")
        lines.append("WORKDIR /app")
        lines.append("COPY --from=builder /app .")
        lines.append("")
        lines.append("USER appuser")
        port = profile.ports[0] if profile.ports else 3000
        lines.append(f"EXPOSE {port}")
        lines.append("")
        start = profile.scripts.get("start", f"node {profile.entry_point or 'index.js'}")
        lines.append(f'CMD {json.dumps(start.split())}')

    elif lang == "go":
        lines.append("COPY go.mod go.sum ./")
        lines.append("RUN go mod download")
        lines.append("")
        lines.append("COPY . .")
        lines.append('RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server .')
        lines.append("")
        lines.append(f"# ---- Runtime stage ----")
        lines.append(f"FROM {runtime_image}")
        lines.append("")
        lines.append("RUN addgroup -S appuser && adduser -S appuser -G appuser")
        lines.append("WORKDIR /app")
        lines.append("COPY --from=builder /app/server .")
        lines.append("")
        lines.append("USER appuser")
        port = profile.ports[0] if profile.ports else 8080
        lines.append(f"EXPOSE {port}")
        lines.append(f'CMD ["./server"]')

    else:
        lines.append("COPY . .")
        lines.append("")
        port = profile.ports[0] if profile.ports else 8080
        lines.append(f"EXPOSE {port}")
        entry = profile.entry_point or "app"
        lines.append(f'CMD ["./{entry}"]')

    dockerfile = "\n".join(lines) + "\n"

    # Dockerignore
    dockerignore = "\n".join([
        ".git", "__pycache__", "*.pyc", "node_modules", ".env", ".env.*",
        "*.md", ".vscode", ".idea", "dist", "build", ".tox",
        ".pytest_cache", ".mypy_cache", "*.egg-info", ".DS_Store",
        "venv", ".venv",
    ]) + "\n"

    # Save files
    out = Path(get_output_dir())
    out.mkdir(parents=True, exist_ok=True)
    (out / "Dockerfile").write_text(dockerfile)
    (out / ".dockerignore").write_text(dockerignore)
    store_generated("Dockerfile", dockerfile)
    store_generated(".dockerignore", dockerignore)

    result: dict[str, Any] = {
        "generated": ["Dockerfile", ".dockerignore"],
        "base_image": build_image,
        "runtime_image": runtime_image,
        "port": profile.ports[0] if profile.ports else 8080,
        "output_dir": str(out),
    }

    # Docker Compose
    if include_compose:
        compose = _generate_compose(profile)
        (out / "docker-compose.yml").write_text(compose)
        store_generated("docker-compose.yml", compose)
        result["generated"].append("docker-compose.yml")

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _generate_compose(profile) -> str:
    port = profile.ports[0] if profile.ports else 8080
    lines = [
        "services:",
        f"  {profile.name}:",
        "    build: .",
        f"    ports:",
        f'      - "{port}:{port}"',
    ]

    if profile.env_vars:
        lines.append("    environment:")
        for var in profile.env_vars[:10]:
            lines.append(f"      - {var}=${{{{ {var} }}}}")

    lines.append("    restart: unless-stopped")
    lines.append("    healthcheck:")
    lines.append(f'      test: ["CMD", "curl", "-f", "http://localhost:{port}/health"]')
    lines.append("      interval: 30s")
    lines.append("      timeout: 10s")
    lines.append("      retries: 3")
    lines.append("")

    return "\n".join(lines) + "\n"
