"""MCP tool: generate_deployment — Generate deployment configs."""

from __future__ import annotations

import os
from pathlib import Path

from claude_agent_sdk import tool

from orchestrator_agent import state


# ---------------------------------------------------------------------------
# Dockerfile templates
# ---------------------------------------------------------------------------

DOCKERFILES: dict[str, str] = {
    "python-api": """\
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "{module}.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
    "python-cli": """\
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

ENTRYPOINT ["{name}"]
""",
    "node-api": """\
FROM node:20-slim

WORKDIR /app
COPY package*.json ./
RUN npm ci --production

COPY . .
RUN npm run build

EXPOSE 3000
CMD ["node", "dist/index.js"]
""",
    "react-app": """\
FROM node:20-slim AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
""",
    "go-api": """\
FROM golang:1.22 AS build

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /server ./cmd/server

FROM scratch
COPY --from=build /server /server
EXPOSE 8080
CMD ["/server"]
""",
}

# ---------------------------------------------------------------------------
# Docker Compose
# ---------------------------------------------------------------------------

COMPOSE_TEMPLATE = """\
version: "3.9"

services:
  app:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      - NODE_ENV=production
    restart: unless-stopped
"""

# ---------------------------------------------------------------------------
# CI/CD templates
# ---------------------------------------------------------------------------

GITHUB_ACTIONS: dict[str, str] = {
    "python": """\
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: pytest --tb=short -q
""",
    "typescript": """\
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - run: npm test
      - run: npm run build
""",
    "go": """\
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: "1.22"
      - run: go test ./...
      - run: go build ./...
""",
}

# ---------------------------------------------------------------------------
# Makefile
# ---------------------------------------------------------------------------

MAKEFILES: dict[str, str] = {
    "python": """\
.PHONY: install test lint run docker

install:
\tpip install -e ".[dev]"

test:
\tpytest --tb=short -q

lint:
\truff check src/

run:
\tpython -m {module}

docker:
\tdocker build -t {name} .
\tdocker run --rm -p 8000:8000 {name}
""",
    "typescript": """\
.PHONY: install test lint run docker

install:
\tnpm ci

test:
\tnpm test

lint:
\tnpm run lint

run:
\tnpm run dev

docker:
\tdocker build -t {name} .
\tdocker run --rm -p 3000:3000 {name}
""",
    "go": """\
.PHONY: build test lint run docker

build:
\tgo build -o bin/server ./cmd/server

test:
\tgo test ./...

lint:
\tgolangci-lint run

run:
\tgo run cmd/server/main.go

docker:
\tdocker build -t {name} .
\tdocker run --rm -p 8080:8080 {name}
""",
}


@tool(
    "generate_deployment",
    "Generate deployment configuration files: Dockerfile, docker-compose.yml, "
    "GitHub Actions CI/CD pipeline, and Makefile. "
    "Optional 'configs': comma-separated list of 'dockerfile', 'compose', 'ci', "
    "'makefile', 'all' (default 'all').",
    {"configs": str},
)
def generate_deployment(configs: str = "all") -> dict:
    plan = state.get_plan()
    out = state.get_output_dir()
    project_dir = os.path.join(out, plan["project_name"])
    preset = plan.get("preset", "python-api")
    lang = plan.get("language", "python")
    name = plan["project_name"]
    module = name.replace("-", "_")
    port = "8000" if lang == "python" else ("8080" if lang == "go" else "3000")

    requested = {c.strip().lower() for c in configs.split(",")}
    do_all = "all" in requested
    generated: list[str] = []

    if do_all or "dockerfile" in requested:
        template = DOCKERFILES.get(preset, DOCKERFILES["python-api"])
        content = template.format(name=name, module=module)
        fpath = os.path.join(project_dir, "Dockerfile")
        Path(fpath).parent.mkdir(parents=True, exist_ok=True)
        Path(fpath).write_text(content)
        state.store_file("Dockerfile", content)
        generated.append("Dockerfile")

    if do_all or "compose" in requested:
        content = COMPOSE_TEMPLATE.format(port=port)
        fpath = os.path.join(project_dir, "docker-compose.yml")
        Path(fpath).write_text(content)
        state.store_file("docker-compose.yml", content)
        generated.append("docker-compose.yml")

    if do_all or "ci" in requested:
        ci_lang = lang if lang in GITHUB_ACTIONS else "python"
        content = GITHUB_ACTIONS[ci_lang]
        ci_dir = os.path.join(project_dir, ".github", "workflows")
        os.makedirs(ci_dir, exist_ok=True)
        fpath = os.path.join(ci_dir, "ci.yml")
        Path(fpath).write_text(content)
        state.store_file(".github/workflows/ci.yml", content)
        generated.append(".github/workflows/ci.yml")

    if do_all or "makefile" in requested:
        mk_lang = lang if lang in MAKEFILES else "python"
        content = MAKEFILES[mk_lang].format(name=name, module=module)
        fpath = os.path.join(project_dir, "Makefile")
        Path(fpath).write_text(content)
        state.store_file("Makefile", content)
        generated.append("Makefile")

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Generated deployment configs:\n"
                    + "\n".join(f"  - {f}" for f in generated)
                ),
            }
        ]
    }
