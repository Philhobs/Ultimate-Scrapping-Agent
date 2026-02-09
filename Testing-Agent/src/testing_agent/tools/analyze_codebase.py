"""analyze_codebase MCP tool — scan a project and extract structure."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from testing_agent.analyzers.code_parser import scan_codebase
from testing_agent.state import set_profile


@tool(
    "analyze_codebase",
    "Scan a project directory to detect language, test framework, source files, "
    "test files, and extract all function/class signatures. Must be called first. "
    "Provide 'path' to the project root.",
    {"path": str},
)
async def analyze_codebase(args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path", ".")
    profile = scan_codebase(path)
    set_profile(profile)

    # Summarize functions (don't dump all details for huge projects)
    func_summary = []
    for fn in profile.functions[:50]:
        entry = {
            "name": fn.name,
            "file": fn.file,
            "line": fn.line,
            "params": fn.params,
        }
        if fn.class_name:
            entry["class"] = fn.class_name
        if fn.docstring:
            entry["docstring"] = fn.docstring[:200]
        func_summary.append(entry)

    result = {
        "name": profile.name,
        "language": profile.language,
        "test_framework": profile.test_framework,
        "source_files": profile.source_files,
        "test_files": profile.test_files,
        "total_functions": profile.total_functions,
        "total_files": profile.total_files,
        "total_lines": profile.total_lines,
        "has_tests": profile.has_tests,
        "existing_configs": profile.existing_configs,
        "functions": func_summary,
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
