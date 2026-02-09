"""generate_deploy_script MCP tool — generate deployment scripts and Makefile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from devops_agent.state import get_profile, store_generated, get_output_dir


@tool(
    "generate_deploy_script",
    "Generate deployment convenience scripts. Provide 'type': "
    "'makefile' (Makefile with build/test/deploy/clean targets), "
    "'shell' (deploy.sh script), "
    "'systemd' (systemd service file for Linux servers).",
    {"type": str},
)
async def generate_deploy_script(args: dict[str, Any]) -> dict[str, Any]:
    profile = get_profile()
    script_type = args.get("type", "makefile")

    out = Path(get_output_dir())
    out.mkdir(parents=True, exist_ok=True)

    if script_type == "makefile":
        content = _makefile(profile)
        (out / "Makefile").write_text(content)
        store_generated("Makefile", content)
        filename = "Makefile"

    elif script_type == "shell":
        content = _deploy_sh(profile)
        path = out / "deploy.sh"
        path.write_text(content)
        path.chmod(0o755)
        store_generated("deploy.sh", content)
        filename = "deploy.sh"

    elif script_type == "systemd":
        content = _systemd(profile)
        (out / f"{profile.name}.service").write_text(content)
        store_generated(f"{profile.name}.service", content)
        filename = f"{profile.name}.service"

    else:
        return {
            "content": [{"type": "text", "text": f"Unknown type '{script_type}'. Use: makefile, shell, systemd."}],
            "is_error": True,
        }

    result = {"type": script_type, "file": filename, "output_dir": str(out)}
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _makefile(profile) -> str:
    name = profile.name
    port = profile.ports[0] if profile.ports else 8080

    lines = [
        f".PHONY: help build test lint run docker-build docker-run deploy clean",
        "",
        f"IMAGE_NAME ?= {name}",
        f"IMAGE_TAG  ?= latest",
        f"PORT       ?= {port}",
        "",
        "help: ## Show this help",
        '\t@grep -E "^[a-zA-Z_-]+:.*?## .*$$" $(MAKEFILE_LIST) | sort | awk \'BEGIN {FS = ":.*?## "}; {printf "\\033[36m%-20s\\033[0m %s\\n", $$1, $$2}\'',
        "",
    ]

    if profile.language == "python":
        lines.extend([
            "install: ## Install dependencies",
            "\tpip install -e .",
            "",
            "test: ## Run tests",
            "\tpytest --tb=short -q",
            "",
            "lint: ## Run linter",
            "\truff check . --fix",
            "",
            "run: ## Run locally",
            f"\tpython {profile.entry_point or 'app.py'}",
            "",
        ])
    elif profile.language in ("javascript", "typescript"):
        lines.extend([
            "install: ## Install dependencies",
            "\tnpm ci",
            "",
            "test: ## Run tests",
            "\tnpm test",
            "",
            "lint: ## Run linter",
            "\tnpm run lint",
            "",
            "run: ## Run locally",
            "\tnpm start",
            "",
        ])
    elif profile.language == "go":
        lines.extend([
            "build: ## Build binary",
            f"\tgo build -o bin/{name} .",
            "",
            "test: ## Run tests",
            "\tgo test ./... -v",
            "",
            "lint: ## Run linter",
            "\tgolangci-lint run",
            "",
            "run: ## Run locally",
            f"\tgo run .",
            "",
        ])

    lines.extend([
        "docker-build: ## Build Docker image",
        "\tdocker build -t $(IMAGE_NAME):$(IMAGE_TAG) .",
        "",
        "docker-run: ## Run Docker container",
        "\tdocker run --rm -p $(PORT):$(PORT) --env-file .env $(IMAGE_NAME):$(IMAGE_TAG)",
        "",
        "docker-push: ## Push Docker image",
        "\tdocker push $(IMAGE_NAME):$(IMAGE_TAG)",
        "",
        "deploy: docker-build docker-push ## Build and push",
        "\t@echo 'Deployed $(IMAGE_NAME):$(IMAGE_TAG)'",
        "",
        "clean: ## Clean build artifacts",
    ])

    if profile.language == "python":
        lines.append("\trm -rf __pycache__ *.egg-info dist build .pytest_cache .mypy_cache .ruff_cache")
    elif profile.language in ("javascript", "typescript"):
        lines.append("\trm -rf node_modules dist .next")
    elif profile.language == "go":
        lines.append("\trm -rf bin/")

    lines.append("")
    return "\n".join(lines)


def _deploy_sh(profile) -> str:
    name = profile.name
    port = profile.ports[0] if profile.ports else 8080

    return f"""#!/usr/bin/env bash
set -euo pipefail

# Deploy script for {name}

IMAGE_NAME="${{IMAGE_NAME:-{name}}}"
IMAGE_TAG="${{IMAGE_TAG:-latest}}"
PORT="${{PORT:-{port}}}"

echo "==> Building Docker image..."
docker build -t "$IMAGE_NAME:$IMAGE_TAG" .

echo "==> Running tests..."
docker run --rm "$IMAGE_NAME:$IMAGE_TAG" {"pytest --tb=short" if profile.language == "python" else "npm test" if profile.language in ("javascript", "typescript") else "echo 'No tests configured'"}

echo "==> Pushing image..."
docker push "$IMAGE_NAME:$IMAGE_TAG"

echo "==> Deployed $IMAGE_NAME:$IMAGE_TAG"
echo "    Port: $PORT"
"""


def _systemd(profile) -> str:
    name = profile.name
    entry = profile.entry_point or "app.py"

    return f"""[Unit]
Description={name} service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/{name}
ExecStart=/opt/{name}/venv/bin/python {entry}
Restart=always
RestartSec=5
EnvironmentFile=/opt/{name}/.env

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/{name}

# Resource limits
MemoryMax=512M
CPUQuota=100%

[Install]
WantedBy=multi-user.target
"""
