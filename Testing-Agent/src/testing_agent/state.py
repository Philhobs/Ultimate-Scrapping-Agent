"""Shared state for MCP tools.

Holds the codebase profile, test results, bug reports, and applied fixes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from testing_agent.analyzers.code_parser import CodebaseProfile, FunctionInfo
    from testing_agent.analyzers.test_runner import TestResult

_profile: CodebaseProfile | None = None
_test_results: list[TestResult] = []
_bugs: list[dict[str, Any]] = []
_fixes: list[dict[str, Any]] = []
_output_dir: str = "./testing-output"


def set_profile(profile: CodebaseProfile) -> None:
    global _profile
    _profile = profile


def get_profile() -> CodebaseProfile:
    if _profile is None:
        raise RuntimeError("No codebase analyzed. Use analyze_codebase first.")
    return _profile


def set_test_results(results: list[TestResult]) -> None:
    global _test_results
    _test_results = results


def get_test_results() -> list[TestResult]:
    return _test_results


def add_bug(bug: dict[str, Any]) -> None:
    _bugs.append(bug)


def get_bugs() -> list[dict[str, Any]]:
    return _bugs


def add_fix(fix: dict[str, Any]) -> None:
    _fixes.append(fix)


def get_fixes() -> list[dict[str, Any]]:
    return _fixes


def set_output_dir(path: str) -> None:
    global _output_dir
    _output_dir = path


def get_output_dir() -> str:
    return _output_dir
