"""Shared state for MCP tools.

Holds target profile, findings, tested payloads, and defense evaluations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redteam_agent.analyzers.vulnerability_scanner import VulnFinding

_target_info: dict[str, Any] | None = None
_findings: list[VulnFinding] = []
_payloads_tested: list[dict[str, Any]] = []
_defense_evals: list[dict[str, Any]] = []
_output_dir: str = "./redteam-output"


def set_target(info: dict[str, Any]) -> None:
    global _target_info
    _target_info = info


def get_target() -> dict[str, Any]:
    if _target_info is None:
        raise RuntimeError("No target scanned. Use scan_target first.")
    return _target_info


def set_findings(findings: list[VulnFinding]) -> None:
    global _findings
    _findings = findings


def add_finding(finding: VulnFinding) -> None:
    _findings.append(finding)


def get_findings() -> list[VulnFinding]:
    return _findings


def add_payload_result(result: dict[str, Any]) -> None:
    _payloads_tested.append(result)


def get_payload_results() -> list[dict[str, Any]]:
    return _payloads_tested


def add_defense_eval(evaluation: dict[str, Any]) -> None:
    _defense_evals.append(evaluation)


def get_defense_evals() -> list[dict[str, Any]]:
    return _defense_evals


def set_output_dir(path: str) -> None:
    global _output_dir
    _output_dir = path


def get_output_dir() -> str:
    return _output_dir
