"""MCP tool: run_tests — Execute the test suite and capture results."""

from __future__ import annotations

import os
import subprocess

from claude_agent_sdk import tool

from orchestrator_agent import state


DETECT_MAP = {
    "pyproject.toml": "pytest",
    "setup.py":       "pytest",
    "package.json":   "npm test",
    "go.mod":         "go test ./...",
    "Cargo.toml":     "cargo test",
}


def _detect_runner(project_dir: str) -> str:
    for marker, cmd in DETECT_MAP.items():
        if os.path.exists(os.path.join(project_dir, marker)):
            return cmd
    return "pytest"


@tool(
    "run_tests",
    "Execute the project test suite. Auto-detects the test runner "
    "(pytest, npm test, go test, cargo test) or accepts a custom command. "
    "Optional 'command' overrides auto-detect. Optional 'timeout' in seconds.",
    {"command": str, "timeout": str},
)
def run_tests(command: str = "", timeout: str = "120") -> dict:
    plan = state.get_plan()
    out = state.get_output_dir()
    project_dir = os.path.join(out, plan["project_name"])

    cmd = command.strip() or _detect_runner(project_dir)

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=int(timeout),
        )
        passed = result.returncode == 0
        test_result = {
            "command": cmd,
            "exit_code": result.returncode,
            "passed": passed,
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:3000],
        }
        state.add_test_result(test_result)

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Tests {'PASSED' if passed else 'FAILED'}\n"
                        f"Command: {cmd}\n"
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
                {"type": "text", "text": f"Tests timed out after {timeout}s: {cmd}"}
            ]
        }
    except Exception as exc:
        return {
            "content": [
                {"type": "text", "text": f"Test execution failed: {exc}"}
            ]
        }
