"""profile_performance MCP tool — run performance profiling on code."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from testing_agent.analyzers.test_runner import run_with_profiling
from testing_agent.state import get_profile


@tool(
    "profile_performance",
    "Run performance profiling on the test suite or specific code. "
    "Identifies slow functions, hotspots, and timing. "
    "Optional: 'target' (specific test file/function), 'timeout' (seconds, default 120).",
    {"target": str, "timeout": int},
)
async def profile_performance(args: dict[str, Any]) -> dict[str, Any]:
    try:
        profile = get_profile()
    except RuntimeError:
        return {
            "content": [{"type": "text", "text": "Error: Run analyze_codebase first."}],
            "is_error": True,
        }

    target = args.get("target")
    timeout = args.get("timeout", 120)

    result = run_with_profiling(
        root=profile.root,
        test_framework=profile.test_framework or "pytest",
        target=target,
        timeout=timeout,
    )

    # Limit raw output
    raw = result.get("raw_output", "")
    if len(raw) > 5000:
        raw = raw[:5000] + "\n... (output truncated)"
    result["raw_output"] = raw

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
