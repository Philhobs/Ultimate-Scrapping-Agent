"""run_tests MCP tool — execute tests and return results."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from testing_agent.analyzers.test_runner import run_tests as execute_tests
from testing_agent.state import get_profile, set_test_results


@tool(
    "run_tests",
    "Execute the test suite or a specific test file. Returns pass/fail results, "
    "error messages, and raw output. "
    "Optional: 'target' (specific test file or test name), 'timeout' (seconds, default 120).",
    {"target": str, "timeout": int},
)
async def run_tests(args: dict[str, Any]) -> dict[str, Any]:
    try:
        profile = get_profile()
    except RuntimeError:
        return {
            "content": [{"type": "text", "text": "Error: Run analyze_codebase first."}],
            "is_error": True,
        }

    target = args.get("target")
    timeout = args.get("timeout", 120)

    result = execute_tests(
        root=profile.root,
        test_framework=profile.test_framework or "pytest",
        target=target,
        timeout=timeout,
    )

    # Store results in state
    from testing_agent.analyzers.test_runner import TestResult
    parsed_results = []
    for r in result.get("results", []):
        parsed_results.append(TestResult(
            name=r["name"],
            status=r["status"],
            duration=r.get("duration"),
            message=r.get("message"),
            file=r.get("file"),
            line=r.get("line"),
        ))
    set_test_results(parsed_results)

    # Limit raw output to avoid overwhelming the context
    raw = result.get("raw_output", "")
    if len(raw) > 5000:
        raw = raw[:5000] + "\n... (output truncated)"
    result["raw_output"] = raw

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
