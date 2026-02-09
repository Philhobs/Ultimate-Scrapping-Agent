"""generate_infrastructure MCP tool — generate IaC templates (K8s, Terraform, Compose)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from devops_agent.state import get_profile, store_generated, get_output_dir


@tool(
    "generate_infrastructure",
    "Generate infrastructure-as-code templates. Provide 'type': "
    "'kubernetes' (K8s Deployment + Service + Ingress), "
    "'terraform' (AWS ECS or GCP Cloud Run module), "
    "'compose' (docker-compose for local/staging). "
    "Optional: 'replicas' (default 2), 'namespace' (K8s), 'cloud' (aws/gcp for terraform).",
    {"type": str, "replicas": int, "namespace": str, "cloud": str},
)
async def generate_infrastructure(args: dict[str, Any]) -> dict[str, Any]:
    profile = get_profile()
    infra_type = args.get("type", "kubernetes")
    replicas = args.get("replicas", 2)
    namespace = args.get("namespace", "default")
    cloud = args.get("cloud", "aws")

    out = Path(get_output_dir())
    out.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []

    if infra_type == "kubernetes":
        files = _kubernetes(profile, replicas, namespace)
        k8s_dir = out / "k8s"
        k8s_dir.mkdir(exist_ok=True)
        for fname, content in files.items():
            (k8s_dir / fname).write_text(content)
            store_generated(f"k8s/{fname}", content)
            generated.append(f"k8s/{fname}")

    elif infra_type == "terraform":
        files = _terraform(profile, cloud)
        tf_dir = out / "terraform"
        tf_dir.mkdir(exist_ok=True)
        for fname, content in files.items():
            (tf_dir / fname).write_text(content)
            store_generated(f"terraform/{fname}", content)
            generated.append(f"terraform/{fname}")

    elif infra_type == "compose":
        content = _compose_full(profile)
        (out / "docker-compose.prod.yml").write_text(content)
        store_generated("docker-compose.prod.yml", content)
        generated.append("docker-compose.prod.yml")

    else:
        return {
            "content": [{"type": "text", "text": f"Unknown type '{infra_type}'. Use: kubernetes, terraform, compose."}],
            "is_error": True,
        }

    result = {
        "type": infra_type,
        "generated": generated,
        "output_dir": str(out),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _kubernetes(profile, replicas: int, namespace: str) -> dict[str, str]:
    name = profile.name.lower().replace("_", "-").replace(" ", "-")
    port = profile.ports[0] if profile.ports else 8080

    deployment = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {namespace}
  labels:
    app: {name}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {name}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: {name}
    spec:
      containers:
        - name: {name}
          image: {name}:latest
          ports:
            - containerPort: {port}
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: {port}
            initialDelaySeconds: 15
            periodSeconds: 20
          readinessProbe:
            httpGet:
              path: /health
              port: {port}
            initialDelaySeconds: 5
            periodSeconds: 10
"""

    if profile.env_vars:
        env_block = "          env:\n"
        for var in profile.env_vars[:10]:
            env_block += f"            - name: {var}\n"
            env_block += f"              valueFrom:\n"
            env_block += f"                secretKeyRef:\n"
            env_block += f"                  name: {name}-secrets\n"
            env_block += f"                  key: {var}\n"
        deployment = deployment.rstrip() + "\n" + env_block

    service = f"""apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: {namespace}
spec:
  selector:
    app: {name}
  ports:
    - port: 80
      targetPort: {port}
  type: ClusterIP
"""

    ingress = f"""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {name}
  namespace: {namespace}
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
    - host: {name}.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {name}
                port:
                  number: 80
"""

    hpa = f"""apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {name}
  namespace: {namespace}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {name}
  minReplicas: {replicas}
  maxReplicas: {replicas * 5}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
"""

    return {
        "deployment.yaml": deployment,
        "service.yaml": service,
        "ingress.yaml": ingress,
        "hpa.yaml": hpa,
    }


def _terraform(profile, cloud: str) -> dict[str, str]:
    name = profile.name.lower().replace("_", "-").replace(" ", "-")
    port = profile.ports[0] if profile.ports else 8080

    main_tf = f"""# {profile.name} — Terraform deployment
# Cloud: {cloud.upper()}

terraform {{
  required_version = ">= 1.5"
  required_providers {{
    {"aws" if cloud == "aws" else "google"} = {{
      source  = "hashicorp/{"aws" if cloud == "aws" else "google"}"
      version = "~> {"5.0" if cloud == "aws" else "5.0"}"
    }}
  }}
}}

variable "image_tag" {{
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}}

variable "environment" {{
  description = "Deployment environment"
  type        = string
  default     = "production"
}}
"""

    if cloud == "aws":
        main_tf += f"""
# ECS Cluster
resource "aws_ecs_cluster" "{name}_cluster" {{
  name = "{name}-${{var.environment}}"

  setting {{
    name  = "containerInsights"
    value = "enabled"
  }}
}}

# Task Definition
resource "aws_ecs_task_definition" "{name}" {{
  family                   = "{name}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"

  container_definitions = jsonencode([
    {{
      name      = "{name}"
      image     = "${{var.image_tag}}"
      essential = true
      portMappings = [
        {{
          containerPort = {port}
          hostPort      = {port}
        }}
      ]
      healthCheck = {{
        command     = ["CMD-SHELL", "curl -f http://localhost:{port}/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }}
      logConfiguration = {{
        logDriver = "awslogs"
        options = {{
          "awslogs-group"         = "/ecs/{name}"
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "ecs"
        }}
      }}
    }}
  ])
}}

# ECS Service
resource "aws_ecs_service" "{name}" {{
  name            = "{name}"
  cluster         = aws_ecs_cluster.{name}_cluster.id
  task_definition = aws_ecs_task_definition.{name}.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200
}}
"""

    elif cloud == "gcp":
        main_tf += f"""
# Cloud Run Service
resource "google_cloud_run_service" "{name}" {{
  name     = "{name}"
  location = "us-central1"

  template {{
    spec {{
      containers {{
        image = "${{var.image_tag}}"
        ports {{
          container_port = {port}
        }}
        resources {{
          limits = {{
            memory = "512Mi"
            cpu    = "1000m"
          }}
        }}
      }}
    }}

    metadata {{
      annotations = {{
        "autoscaling.knative.dev/minScale" = "1"
        "autoscaling.knative.dev/maxScale" = "10"
      }}
    }}
  }}

  traffic {{
    percent         = 100
    latest_revision = true
  }}
}}

# Allow unauthenticated access
resource "google_cloud_run_service_iam_member" "public" {{
  service  = google_cloud_run_service.{name}.name
  location = google_cloud_run_service.{name}.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}}
"""

    outputs_tf = f"""output "service_url" {{
  description = "URL of the deployed service"
  value       = {"aws_ecs_service." + name + ".id" if cloud == "aws" else "google_cloud_run_service." + name + ".status[0].url"}
}}
"""

    return {"main.tf": main_tf, "outputs.tf": outputs_tf}


def _compose_full(profile) -> str:
    name = profile.name.lower().replace("_", "-").replace(" ", "-")
    port = profile.ports[0] if profile.ports else 8080

    lines = [
        "services:",
        f"  {name}:",
        "    build:",
        "      context: .",
        "      dockerfile: Dockerfile",
        f"    ports:",
        f'      - "{port}:{port}"',
        "    restart: unless-stopped",
        "    healthcheck:",
        f'      test: ["CMD", "curl", "-f", "http://localhost:{port}/health"]',
        "      interval: 30s",
        "      timeout: 10s",
        "      retries: 3",
    ]

    if profile.env_vars:
        lines.append("    env_file:")
        lines.append("      - .env")

    # Add common services
    has_db = any(d in " ".join(profile.dependencies).lower() for d in ("sqlalchemy", "psycopg", "pg", "prisma", "sequelize", "typeorm", "diesel"))
    has_redis = any(d in " ".join(profile.dependencies).lower() for d in ("redis", "celery", "bull"))

    if has_db:
        lines.extend([
            "",
            "  postgres:",
            "    image: postgres:16-alpine",
            "    environment:",
            "      POSTGRES_DB: app",
            "      POSTGRES_USER: app",
            "      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}",
            "    volumes:",
            "      - pgdata:/var/lib/postgresql/data",
            "    ports:",
            '      - "5432:5432"',
            "    healthcheck:",
            '      test: ["CMD-SHELL", "pg_isready -U app"]',
            "      interval: 10s",
            "      timeout: 5s",
        ])

    if has_redis:
        lines.extend([
            "",
            "  redis:",
            "    image: redis:7-alpine",
            "    ports:",
            '      - "6379:6379"',
            "    healthcheck:",
            '      test: ["CMD", "redis-cli", "ping"]',
            "      interval: 10s",
        ])

    if has_db or has_redis:
        lines.extend(["", "volumes:"])
        if has_db:
            lines.append("  pgdata:")

    lines.append("")

    return "\n".join(lines) + "\n"
