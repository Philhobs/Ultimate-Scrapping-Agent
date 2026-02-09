"""Test runner — execute tests using the project's test framework."""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestResult:
    """Result of a single test case."""
    name: str
    status: str  # "passed", "failed", "error", "skipped"
    duration: float | None
    message: str | None
    file: str | None
    line: int | None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "duration": self.duration,
            "message": self.message,
            "file": self.file,
            "line": self.line,
        }


def run_tests(
    root: str,
    test_framework: str,
    target: str | None = None,
    timeout: int = 120,
) -> dict:
    """Execute tests and return structured results.

    Args:
        root: Project root directory.
        test_framework: The test framework to use (pytest, unittest, jest, etc.).
        target: Specific test file or test name to run (optional).
        timeout: Timeout in seconds.

    Returns:
        Dict with summary and individual test results.
    """
    start = time.time()

    if test_framework == "pytest":
        return _run_pytest(root, target, timeout)
    elif test_framework == "unittest":
        return _run_unittest(root, target, timeout)
    elif test_framework in ("jest", "vitest"):
        return _run_jest(root, target, timeout, test_framework)
    elif test_framework == "go_test":
        return _run_go_test(root, target, timeout)
    elif test_framework == "mocha":
        return _run_mocha(root, target, timeout)
    else:
        return {
            "error": f"Unsupported test framework: {test_framework}",
            "results": [],
            "raw_output": "",
        }


def _run_command(cmd: list[str], cwd: str, timeout: int) -> tuple[str, str, int]:
    """Run a command and return stdout, stderr, returncode."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        return proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return "", f"Test execution timed out after {timeout}s", 1
    except FileNotFoundError:
        return "", f"Command not found: {cmd[0]}", 1


def _run_pytest(root: str, target: str | None, timeout: int) -> dict:
    """Run pytest and parse results."""
    cmd = ["python", "-m", "pytest", "-v", "--tb=short", "-q"]
    if target:
        cmd.append(target)

    stdout, stderr, rc = _run_command(cmd, root, timeout)
    output = stdout + "\n" + stderr
    results: list[TestResult] = []

    # Parse pytest verbose output
    # Lines like: tests/test_foo.py::test_bar PASSED
    for line in output.split("\n"):
        match = re.match(r"(\S+::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED)", line)
        if match:
            name = match.group(1)
            status = match.group(2).lower()
            results.append(TestResult(
                name=name,
                status=status,
                duration=None,
                message=None,
                file=name.split("::")[0] if "::" in name else None,
                line=None,
            ))

    # Parse summary line: "X passed, Y failed, Z error"
    summary_match = re.search(r"(\d+) passed", output)
    passed = int(summary_match.group(1)) if summary_match else 0
    fail_match = re.search(r"(\d+) failed", output)
    failed = int(fail_match.group(1)) if fail_match else 0
    error_match = re.search(r"(\d+) error", output)
    errors = int(error_match.group(1)) if error_match else 0

    # Extract failure details
    failure_details: list[str] = []
    in_failure = False
    for line in output.split("\n"):
        if line.startswith("FAILED") or line.startswith("ERROR") or "FAILURES" in line:
            in_failure = True
        if in_failure:
            failure_details.append(line)

    return {
        "framework": "pytest",
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "total": passed + failed + errors,
        "results": [r.to_dict() for r in results],
        "failure_details": "\n".join(failure_details) if failure_details else None,
        "raw_output": output,
        "returncode": rc,
    }


def _run_unittest(root: str, target: str | None, timeout: int) -> dict:
    """Run unittest and parse results."""
    cmd = ["python", "-m", "unittest"]
    if target:
        cmd.append(target)
    else:
        cmd.extend(["discover", "-s", ".", "-p", "test_*.py", "-v"])

    stdout, stderr, rc = _run_command(cmd, root, timeout)
    output = stdout + "\n" + stderr
    results: list[TestResult] = []

    # Parse unittest verbose output
    for line in output.split("\n"):
        match = re.match(r"(\S+)\s+\((\S+)\)\s+\.\.\.\s+(ok|FAIL|ERROR|skip)", line)
        if match:
            test_name = f"{match.group(2)}.{match.group(1)}"
            status_map = {"ok": "passed", "FAIL": "failed", "ERROR": "error", "skip": "skipped"}
            results.append(TestResult(
                name=test_name,
                status=status_map.get(match.group(3), "error"),
                duration=None,
                message=None,
                file=None,
                line=None,
            ))

    return {
        "framework": "unittest",
        "passed": sum(1 for r in results if r.status == "passed"),
        "failed": sum(1 for r in results if r.status == "failed"),
        "errors": sum(1 for r in results if r.status == "error"),
        "total": len(results),
        "results": [r.to_dict() for r in results],
        "raw_output": output,
        "returncode": rc,
    }


def _run_jest(root: str, target: str | None, timeout: int, framework: str) -> dict:
    """Run Jest/Vitest and parse results."""
    cmd = ["npx", framework, "--verbose"]
    if target:
        cmd.append(target)

    stdout, stderr, rc = _run_command(cmd, root, timeout)
    output = stdout + "\n" + stderr
    results: list[TestResult] = []

    # Parse Jest/Vitest output
    for line in output.split("\n"):
        pass_match = re.match(r"\s*✓\s+(.*?)(?:\s+\((\d+)\s*ms\))?$", line)
        fail_match = re.match(r"\s*✕\s+(.*?)(?:\s+\((\d+)\s*ms\))?$", line)
        if pass_match:
            results.append(TestResult(
                name=pass_match.group(1).strip(),
                status="passed",
                duration=int(pass_match.group(2)) / 1000 if pass_match.group(2) else None,
                message=None,
                file=None,
                line=None,
            ))
        elif fail_match:
            results.append(TestResult(
                name=fail_match.group(1).strip(),
                status="failed",
                duration=int(fail_match.group(2)) / 1000 if fail_match.group(2) else None,
                message=None,
                file=None,
                line=None,
            ))

    return {
        "framework": framework,
        "passed": sum(1 for r in results if r.status == "passed"),
        "failed": sum(1 for r in results if r.status == "failed"),
        "errors": 0,
        "total": len(results),
        "results": [r.to_dict() for r in results],
        "raw_output": output,
        "returncode": rc,
    }


def _run_go_test(root: str, target: str | None, timeout: int) -> dict:
    """Run go test and parse results."""
    cmd = ["go", "test", "-v"]
    if target:
        cmd.append(target)
    else:
        cmd.append("./...")

    stdout, stderr, rc = _run_command(cmd, root, timeout)
    output = stdout + "\n" + stderr
    results: list[TestResult] = []

    # Parse go test verbose output
    for line in output.split("\n"):
        match = re.match(r"--- (PASS|FAIL|SKIP):\s+(\S+)\s+\(([0-9.]+)s\)", line)
        if match:
            status_map = {"PASS": "passed", "FAIL": "failed", "SKIP": "skipped"}
            results.append(TestResult(
                name=match.group(2),
                status=status_map.get(match.group(1), "error"),
                duration=float(match.group(3)),
                message=None,
                file=None,
                line=None,
            ))

    return {
        "framework": "go_test",
        "passed": sum(1 for r in results if r.status == "passed"),
        "failed": sum(1 for r in results if r.status == "failed"),
        "errors": sum(1 for r in results if r.status == "error"),
        "total": len(results),
        "results": [r.to_dict() for r in results],
        "raw_output": output,
        "returncode": rc,
    }


def _run_mocha(root: str, target: str | None, timeout: int) -> dict:
    """Run mocha and parse results."""
    cmd = ["npx", "mocha", "--reporter", "spec"]
    if target:
        cmd.append(target)

    stdout, stderr, rc = _run_command(cmd, root, timeout)
    output = stdout + "\n" + stderr

    return {
        "framework": "mocha",
        "passed": output.count("passing"),
        "failed": output.count("failing"),
        "errors": 0,
        "total": 0,
        "results": [],
        "raw_output": output,
        "returncode": rc,
    }


def run_with_profiling(
    root: str,
    test_framework: str,
    target: str | None = None,
    timeout: int = 120,
) -> dict:
    """Run tests with profiling enabled."""
    if test_framework == "pytest":
        cmd = ["python", "-m", "cProfile", "-s", "cumulative", "-m", "pytest", "-v", "--tb=short"]
        if target:
            cmd.append(target)
    elif test_framework in ("jest", "vitest"):
        cmd = ["npx", test_framework, "--verbose"]
        if target:
            cmd.append(target)
        # Jest doesn't have built-in profiling; we time the run
    elif test_framework == "go_test":
        cmd = ["go", "test", "-v", "-bench=.", "-benchmem"]
        if target:
            cmd.append(target)
        else:
            cmd.append("./...")
    else:
        cmd = ["python", "-m", "cProfile", "-s", "cumulative", "-m", "pytest"]
        if target:
            cmd.append(target)

    start = time.time()
    stdout, stderr, rc = _run_command(cmd, root, timeout)
    elapsed = time.time() - start
    output = stdout + "\n" + stderr

    # Parse cProfile output for Python
    hotspots: list[dict] = []
    if test_framework in ("pytest", "unittest"):
        lines = output.split("\n")
        in_profile = False
        for line in lines:
            if "ncalls" in line and "tottime" in line:
                in_profile = True
                continue
            if in_profile and line.strip():
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        hotspots.append({
                            "ncalls": parts[0],
                            "tottime": float(parts[1]),
                            "percall": float(parts[2]),
                            "cumtime": float(parts[3]),
                            "function": parts[5] if len(parts) > 5 else parts[-1],
                        })
                    except (ValueError, IndexError):
                        continue
            if len(hotspots) >= 20:
                break

    # Sort by cumulative time
    hotspots.sort(key=lambda x: x.get("cumtime", 0), reverse=True)

    return {
        "framework": test_framework,
        "elapsed_seconds": round(elapsed, 3),
        "hotspots": hotspots[:15],
        "raw_output": output,
        "returncode": rc,
    }
