"""check_coverage MCP tool — analyze test coverage gaps."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from testing_agent.state import get_profile


@tool(
    "check_coverage",
    "Analyze which functions and classes have tests and which don't. "
    "Reports coverage gaps and suggests what to test next. "
    "No parameters needed — uses the analyzed codebase profile.",
    {},
)
async def check_coverage(args: dict[str, Any]) -> dict[str, Any]:
    try:
        profile = get_profile()
    except RuntimeError:
        return {
            "content": [{"type": "text", "text": "Error: Run analyze_codebase first."}],
            "is_error": True,
        }

    # Get all source functions (exclude test functions)
    source_functions = [
        f for f in profile.functions
        if f.file in profile.source_files and not f.name.startswith("test_")
    ]

    # Get all test functions
    test_functions = [
        f for f in profile.functions
        if f.file in profile.test_files or f.name.startswith("test_")
    ]

    # Scan test files for references to source functions
    test_references: set[str] = set()
    for tf in profile.test_files:
        file_path = Path(profile.root) / tf
        if file_path.exists():
            try:
                content = file_path.read_text(errors="replace")
                for fn in source_functions:
                    if fn.name in content:
                        test_references.add(fn.name)
            except OSError:
                continue

    # Also check test function names for references
    for tf in test_functions:
        name_lower = tf.name.lower()
        for fn in source_functions:
            if fn.name.lower() in name_lower:
                test_references.add(fn.name)

    # Build coverage report
    covered: list[dict] = []
    uncovered: list[dict] = []

    for fn in source_functions:
        # Skip private/dunder methods (usually less important)
        is_private = fn.name.startswith("_") and not fn.name.startswith("__")
        is_dunder = fn.name.startswith("__") and fn.name.endswith("__")

        entry = {
            "name": fn.name,
            "file": fn.file,
            "line": fn.line,
            "params": fn.params,
            "class": fn.class_name,
            "priority": "low" if is_private or is_dunder else "high",
        }

        if fn.name in test_references:
            covered.append(entry)
        else:
            uncovered.append(entry)

    # Sort uncovered by priority (high first)
    uncovered.sort(key=lambda x: (0 if x["priority"] == "high" else 1, x["file"]))

    # Calculate coverage percentage
    total = len(source_functions)
    covered_count = len(covered)
    coverage_pct = round(covered_count / total * 100) if total > 0 else 0

    # Group uncovered by file
    uncovered_by_file: dict[str, list[str]] = {}
    for fn in uncovered:
        uncovered_by_file.setdefault(fn["file"], []).append(fn["name"])

    result = {
        "coverage_percentage": f"{coverage_pct}%",
        "total_functions": total,
        "covered": covered_count,
        "uncovered": total - covered_count,
        "test_files": len(profile.test_files),
        "test_functions": len(test_functions),
        "uncovered_by_file": uncovered_by_file,
        "uncovered_functions": uncovered[:30],
        "suggest_next": [
            f["name"] for f in uncovered
            if f["priority"] == "high"
        ][:10],
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
