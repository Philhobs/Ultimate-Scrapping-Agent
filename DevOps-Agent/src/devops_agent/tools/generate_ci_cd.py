"""generate_ci_cd MCP tool — generate CI/CD pipeline configurations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from devops_agent.state import get_profile, store_generated, get_output_dir


@tool(
    "generate_ci_cd",
    "Generate a CI/CD pipeline config. Provide 'platform': github_actions (default), "
    "gitlab_ci, or jenkinsfile. Includes build, test, lint, security scan, and deploy "
    "stages. Optional 'deploy_target' (docker_hub, aws_ecr, gcp_gcr, heroku, none).",
    {"platform": str, "deploy_target": str},
)
async def generate_ci_cd(args: dict[str, Any]) -> dict[str, Any]:
    profile = get_profile()
    platform = args.get("platform", "github_actions")
    deploy_target = args.get("deploy_target", "docker_hub")

    out = Path(get_output_dir())
    out.mkdir(parents=True, exist_ok=True)

    if platform == "github_actions":
        content, filename = _github_actions(profile, deploy_target)
        out_path = out / ".github" / "workflows"
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "ci-cd.yml").write_text(content)
        store_generated(f".github/workflows/ci-cd.yml", content)
        rel_path = ".github/workflows/ci-cd.yml"

    elif platform == "gitlab_ci":
        content, filename = _gitlab_ci(profile, deploy_target)
        (out / filename).write_text(content)
        store_generated(filename, content)
        rel_path = filename

    elif platform == "jenkinsfile":
        content, filename = _jenkinsfile(profile, deploy_target)
        (out / filename).write_text(content)
        store_generated(filename, content)
        rel_path = filename

    else:
        return {
            "content": [{"type": "text", "text": f"Unknown platform '{platform}'. Use: github_actions, gitlab_ci, jenkinsfile."}],
            "is_error": True,
        }

    result = {
        "platform": platform,
        "deploy_target": deploy_target,
        "file": rel_path,
        "stages": ["build", "test", "lint", "security", "deploy"],
        "output_dir": str(out),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _github_actions(profile, deploy_target: str) -> tuple[str, str]:
    lang = profile.language
    lines = [
        f"name: CI/CD Pipeline",
        "",
        "on:",
        "  push:",
        "    branches: [main, master]",
        "  pull_request:",
        "    branches: [main, master]",
        "",
        "env:",
        f"  IMAGE_NAME: {profile.name}",
        "",
        "jobs:",
    ]

    # Build & Test job
    lines.extend([
        "  build-and-test:",
        f'    runs-on: ubuntu-latest',
        "    steps:",
        '      - uses: actions/checkout@v4',
        "",
    ])

    if lang == "python":
        lines.extend([
            "      - name: Set up Python",
            "        uses: actions/setup-python@v5",
            "        with:",
            "          python-version: '3.12'",
            "          cache: 'pip'",
            "",
            "      - name: Install dependencies",
            "        run: |",
            "          python -m pip install --upgrade pip",
        ])
        if "requirements.txt" in profile.existing_files:
            lines.append("          pip install -r requirements.txt")
        else:
            lines.append("          pip install -e .")
        lines.extend([
            "",
            "      - name: Lint",
            "        run: |",
            "          pip install ruff",
            "          ruff check .",
            "",
            "      - name: Test",
            "        run: |",
            "          pip install pytest",
            "          pytest --tb=short -q",
            "",
        ])

    elif lang in ("javascript", "typescript"):
        lines.extend([
            "      - name: Set up Node.js",
            "        uses: actions/setup-node@v4",
            "        with:",
            "          node-version: '20'",
            "          cache: 'npm'",
            "",
            "      - name: Install dependencies",
            "        run: npm ci",
            "",
            "      - name: Lint",
            "        run: npm run lint --if-present",
            "",
            "      - name: Test",
            "        run: npm test --if-present",
            "",
        ])
        if lang == "typescript":
            lines.extend([
                "      - name: Type check",
                "        run: npx tsc --noEmit",
                "",
            ])

    elif lang == "go":
        lines.extend([
            "      - name: Set up Go",
            "        uses: actions/setup-go@v5",
            "        with:",
            "          go-version: '1.22'",
            "",
            "      - name: Build",
            "        run: go build ./...",
            "",
            "      - name: Test",
            "        run: go test ./... -v",
            "",
            "      - name: Lint",
            "        uses: golangci/golangci-lint-action@v4",
            "",
        ])

    # Security scan
    lines.extend([
        "  security:",
        "    runs-on: ubuntu-latest",
        "    needs: build-and-test",
        "    steps:",
        "      - uses: actions/checkout@v4",
        "",
        "      - name: Run security scan",
        "        uses: github/codeql-action/analyze@v3",
        "",
    ])

    # Deploy job
    if deploy_target != "none":
        lines.extend([
            "  deploy:",
            "    runs-on: ubuntu-latest",
            "    needs: [build-and-test, security]",
            "    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'",
            "    steps:",
            "      - uses: actions/checkout@v4",
            "",
        ])

        if deploy_target == "docker_hub":
            lines.extend([
                "      - name: Log in to Docker Hub",
                "        uses: docker/login-action@v3",
                "        with:",
                "          username: ${{ secrets.DOCKER_USERNAME }}",
                "          password: ${{ secrets.DOCKER_PASSWORD }}",
                "",
                "      - name: Build and push Docker image",
                "        uses: docker/build-push-action@v5",
                "        with:",
                "          push: true",
                "          tags: |",
                "            ${{ secrets.DOCKER_USERNAME }}/${{ env.IMAGE_NAME }}:latest",
                "            ${{ secrets.DOCKER_USERNAME }}/${{ env.IMAGE_NAME }}:${{ github.sha }}",
                "",
            ])

        elif deploy_target == "aws_ecr":
            lines.extend([
                "      - name: Configure AWS credentials",
                "        uses: aws-actions/configure-aws-credentials@v4",
                "        with:",
                "          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}",
                "          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}",
                "          aws-region: ${{ secrets.AWS_REGION }}",
                "",
                "      - name: Login to Amazon ECR",
                "        uses: aws-actions/amazon-ecr-login@v2",
                "",
                "      - name: Build and push to ECR",
                "        run: |",
                "          docker build -t ${{ env.IMAGE_NAME }} .",
                "          docker tag ${{ env.IMAGE_NAME }}:latest ${{ secrets.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:latest",
                "          docker push ${{ secrets.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:latest",
                "",
            ])

    return "\n".join(lines) + "\n", "ci-cd.yml"


def _gitlab_ci(profile, deploy_target: str) -> tuple[str, str]:
    lang = profile.language
    lines = [
        "stages:",
        "  - build",
        "  - test",
        "  - security",
        "  - deploy",
        "",
        "variables:",
        f"  IMAGE_NAME: {profile.name}",
        "",
    ]

    if lang == "python":
        lines.extend([
            "build:",
            "  stage: build",
            "  image: python:3.12-slim",
            "  script:",
            "    - pip install --upgrade pip",
        ])
        if "requirements.txt" in profile.existing_files:
            lines.append("    - pip install -r requirements.txt")
        lines.extend([
            "",
            "test:",
            "  stage: test",
            "  image: python:3.12-slim",
            "  script:",
            "    - pip install pytest",
            "    - pytest --tb=short",
            "",
            "lint:",
            "  stage: test",
            "  image: python:3.12-slim",
            "  script:",
            "    - pip install ruff",
            "    - ruff check .",
            "",
        ])

    elif lang in ("javascript", "typescript"):
        lines.extend([
            "build:",
            "  stage: build",
            "  image: node:20-alpine",
            "  script:",
            "    - npm ci",
            "    - npm run build --if-present",
            "",
            "test:",
            "  stage: test",
            "  image: node:20-alpine",
            "  script:",
            "    - npm ci",
            "    - npm test --if-present",
            "",
        ])

    lines.extend([
        "security_scan:",
        "  stage: security",
        "  image: python:3.12-slim",
        "  script:",
        "    - pip install safety",
        "    - safety check || true",
        "  allow_failure: true",
        "",
    ])

    if deploy_target != "none":
        lines.extend([
            "deploy:",
            "  stage: deploy",
            "  image: docker:latest",
            "  services:",
            "    - docker:dind",
            "  only:",
            "    - main",
            "    - master",
            "  script:",
            "    - docker build -t $IMAGE_NAME .",
            "    - docker tag $IMAGE_NAME $CI_REGISTRY_IMAGE:latest",
            "    - docker push $CI_REGISTRY_IMAGE:latest",
            "",
        ])

    return "\n".join(lines) + "\n", ".gitlab-ci.yml"


def _jenkinsfile(profile, deploy_target: str) -> tuple[str, str]:
    lang = profile.language
    lines = [
        "pipeline {",
        "    agent any",
        "",
        "    stages {",
    ]

    if lang == "python":
        lines.extend([
            "        stage('Build') {",
            "            steps {",
            "                sh 'python -m pip install --upgrade pip'",
        ])
        if "requirements.txt" in profile.existing_files:
            lines.append("                sh 'pip install -r requirements.txt'")
        lines.extend([
            "            }",
            "        }",
            "",
            "        stage('Test') {",
            "            steps {",
            "                sh 'pip install pytest'",
            "                sh 'pytest --tb=short'",
            "            }",
            "        }",
            "",
        ])

    elif lang in ("javascript", "typescript"):
        lines.extend([
            "        stage('Build') {",
            "            steps {",
            "                sh 'npm ci'",
            "                sh 'npm run build --if-present'",
            "            }",
            "        }",
            "",
            "        stage('Test') {",
            "            steps {",
            "                sh 'npm test --if-present'",
            "            }",
            "        }",
            "",
        ])

    lines.extend([
        "        stage('Docker Build') {",
        "            steps {",
        f"                sh 'docker build -t {profile.name} .'",
        "            }",
        "        }",
        "",
        "        stage('Deploy') {",
        "            when {",
        "                branch 'main'",
        "            }",
        "            steps {",
        "                echo 'Deploying...'",
        "            }",
        "        }",
        "    }",
        "",
        "    post {",
        "        failure {",
        "            echo 'Pipeline failed!'",
        "        }",
        "    }",
        "}",
    ])

    return "\n".join(lines) + "\n", "Jenkinsfile"
