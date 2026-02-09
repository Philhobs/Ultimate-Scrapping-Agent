"""debug_failure MCP tool — analyze test failures and identify root causes."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from testing_agent.state import get_profile, get_test_results, add_bug


@tool(
    "debug_failure",
    "Analyze a test failure or error. Parses the stack trace, reads the relevant "
    "source code around the error, and provides structured debugging info. "
    "Optional: 'error_output' (raw test output to analyze), 'test_name' (specific failing test).",
    {"error_output": str, "test_name": str},
)
async def debug_failure(args: dict[str, Any]) -> dict[str, Any]:
    try:
        profile = get_profile()
    except RuntimeError:
        return {
            "content": [{"type": "text", "text": "Error: Run analyze_codebase first."}],
            "is_error": True,
        }

    error_output = args.get("error_output", "")
    test_name = args.get("test_name")

    # Get recent test results if no error output provided
    if not error_output:
        results = get_test_results()
        failures = [r for r in results if r.status in ("failed", "error")]
        if test_name:
            failures = [r for r in failures if test_name in r.name]
        if not failures:
            return {"content": [{"type": "text", "text": json.dumps({
                "status": "no_failures",
                "message": "No test failures found. Run tests first to capture results.",
            }, indent=2)}]}
        # Use failure info
        failure_names = [f.name for f in failures]
        error_output = f"Failing tests: {', '.join(failure_names)}"

    # Parse stack traces from error output
    traces = _parse_stack_traces(error_output)

    # Read source code around error locations
    code_context: list[dict] = []
    for trace in traces:
        if trace.get("file") and trace.get("line"):
            file_path = Path(profile.root) / trace["file"]
            if file_path.exists():
                try:
                    content = file_path.read_text(errors="replace")
                    lines = content.split("\n")
                    line_num = trace["line"]
                    start = max(0, line_num - 5)
                    end = min(len(lines), line_num + 5)
                    context_lines = [
                        f"{'>>>' if i + 1 == line_num else '   '} {i + 1:4d} | {lines[i]}"
                        for i in range(start, end)
                    ]
                    code_context.append({
                        "file": trace["file"],
                        "line": line_num,
                        "function": trace.get("function"),
                        "code": "\n".join(context_lines),
                    })
                except OSError:
                    pass

    # Extract error type and message
    error_info = _extract_error_info(error_output)

    # Build bug report
    bug = {
        "error_type": error_info.get("type", "Unknown"),
        "error_message": error_info.get("message", ""),
        "stack_traces": traces,
        "code_context": code_context,
    }
    add_bug(bug)

    result = {
        "error_type": error_info.get("type", "Unknown"),
        "error_message": error_info.get("message", "See raw output"),
        "stack_traces": traces[:10],
        "code_context": code_context[:5],
        "raw_error": error_output[:3000] if len(error_output) > 3000 else error_output,
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _parse_stack_traces(output: str) -> list[dict]:
    """Extract file/line/function from stack traces."""
    traces: list[dict] = []

    # Python traceback: File "path.py", line N, in func
    py_pattern = re.compile(r'File "([^"]+)", line (\d+), in (\w+)')
    for match in py_pattern.finditer(output):
        traces.append({
            "file": match.group(1),
            "line": int(match.group(2)),
            "function": match.group(3),
        })

    # JS/TS stack trace: at FuncName (path.js:line:col)
    js_pattern = re.compile(r"at\s+(\S+)\s+\(([^:]+):(\d+):\d+\)")
    for match in js_pattern.finditer(output):
        traces.append({
            "file": match.group(2),
            "line": int(match.group(3)),
            "function": match.group(1),
        })

    # Go panic: goroutine N [running]: path.go:line
    go_pattern = re.compile(r"(\S+\.go):(\d+)")
    for match in go_pattern.finditer(output):
        traces.append({
            "file": match.group(1),
            "line": int(match.group(2)),
            "function": None,
        })

    # Pytest short traceback: path.py:line: ErrorType
    pytest_pattern = re.compile(r"(\S+\.py):(\d+):\s*(\w+(?:Error|Exception|Warning))")
    for match in pytest_pattern.finditer(output):
        traces.append({
            "file": match.group(1),
            "line": int(match.group(2)),
            "function": None,
            "error": match.group(3),
        })

    # Deduplicate
    seen = set()
    unique: list[dict] = []
    for t in traces:
        key = (t.get("file"), t.get("line"), t.get("function"))
        if key not in seen:
            seen.add(key)
            unique.append(t)

    return unique


def _extract_error_info(output: str) -> dict:
    """Extract error type and message from output."""
    # Python exceptions: ErrorType: message
    py_match = re.search(r"(\w+(?:Error|Exception|Warning|Failure)):\s*(.+)", output)
    if py_match:
        return {"type": py_match.group(1), "message": py_match.group(2).strip()}

    # AssertionError patterns
    assert_match = re.search(r"(assert\s+.+)", output)
    if assert_match:
        return {"type": "AssertionError", "message": assert_match.group(1).strip()}

    # JS errors: Error: message or TypeError: message
    js_match = re.search(r"((?:Type|Reference|Range|Syntax)?Error):\s*(.+)", output)
    if js_match:
        return {"type": js_match.group(1), "message": js_match.group(2).strip()}

    # Generic failure
    if "FAILED" in output:
        return {"type": "TestFailure", "message": "One or more tests failed."}

    return {"type": "Unknown", "message": "Could not parse error details."}
