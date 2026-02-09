"""MCP tool: execute_command — Run a shell command in the project directory."""

from __future__ import annotations

import os
import subprocess

from claude_agent_sdk import tool

from orchestrator_agent import state


@tool(
    "execute_command",
    "Run a shell command in the project directory. "
    "Returns stdout, stderr, and exit code. "
    "Provide 'command' and optional 'timeout' (seconds, default 120).",
    {"command": str, "timeout": str},
)
def execute_command(command: str, timeout: str = "120") -> dict:
    plan = state.get_plan()
    out = state.get_output_dir()
    project_dir = os.path.join(out, plan["project_name"])

    os.makedirs(project_dir, exist_ok=True)

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=int(timeout),
        )
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Command: {command}\n"
                        f"Exit code: {result.returncode}\n\n"
                        f"--- stdout ---\n{result.stdout[:5000]}\n\n"
                        f"--- stderr ---\n{result.stderr[:3000]}"
                    ),
                }
            ]
        }
    except subprocess.TimeoutExpired:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Command timed out after {timeout}s: {command}",
                }
            ]
        }
    except Exception as exc:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Command failed: {exc}",
                }
            ]
        }
