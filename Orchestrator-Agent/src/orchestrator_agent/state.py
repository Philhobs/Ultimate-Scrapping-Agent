"""Shared state for MCP tools.

Holds the project plan, generated files, test results, review findings, and deployment status.
"""

from __future__ import annotations

from typing import Any

_project_plan: dict[str, Any] | None = None
_generated_files: dict[str, str] = {}   # relative path -> content
_test_results: list[dict[str, Any]] = []
_review_findings: list[dict[str, Any]] = []
_output_dir: str = "./orchestrator-output"


# -- Project Plan --

def set_plan(plan: dict[str, Any]) -> None:
    global _project_plan
    _project_plan = plan


def get_plan() -> dict[str, Any]:
    if _project_plan is None:
        raise RuntimeError("No project plan. Use plan_project first.")
    return _project_plan


# -- Generated Files --

def store_file(rel_path: str, content: str) -> None:
    _generated_files[rel_path] = content


def get_file(rel_path: str) -> str | None:
    return _generated_files.get(rel_path)


def list_files() -> dict[str, int]:
    return {k: len(v) for k, v in _generated_files.items()}


def get_all_files() -> dict[str, str]:
    return dict(_generated_files)


# -- Test Results --

def add_test_result(result: dict[str, Any]) -> None:
    _test_results.append(result)


def get_test_results() -> list[dict[str, Any]]:
    return _test_results


# -- Review Findings --

def add_review_finding(finding: dict[str, Any]) -> None:
    _review_findings.append(finding)


def set_review_findings(findings: list[dict[str, Any]]) -> None:
    global _review_findings
    _review_findings = findings


def get_review_findings() -> list[dict[str, Any]]:
    return _review_findings


# -- Output Dir --

def set_output_dir(path: str) -> None:
    global _output_dir
    _output_dir = path


def get_output_dir() -> str:
    return _output_dir
