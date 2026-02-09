"""Shared state for MCP tools.

Holds the project profile, security findings, and generated artifacts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from devops_agent.analyzers.project_scanner import ProjectProfile
    from devops_agent.analyzers.security_scanner import SecurityFinding

_profile: ProjectProfile | None = None
_security_findings: list[SecurityFinding] = []
_generated_files: dict[str, str] = {}  # filename -> content
_output_dir: str = "./output"


def set_profile(profile: ProjectProfile) -> None:
    global _profile
    _profile = profile


def get_profile() -> ProjectProfile:
    if _profile is None:
        raise RuntimeError("No project scanned. Use analyze_project first.")
    return _profile


def set_security_findings(findings: list[SecurityFinding]) -> None:
    global _security_findings
    _security_findings = findings


def get_security_findings() -> list[SecurityFinding]:
    return _security_findings


def store_generated(filename: str, content: str) -> None:
    _generated_files[filename] = content


def get_generated(filename: str) -> str | None:
    return _generated_files.get(filename)


def list_generated() -> dict[str, int]:
    return {k: len(v) for k, v in _generated_files.items()}


def set_output_dir(path: str) -> None:
    global _output_dir
    _output_dir = path


def get_output_dir() -> str:
    return _output_dir
