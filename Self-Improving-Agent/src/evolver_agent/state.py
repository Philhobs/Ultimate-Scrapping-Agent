"""Shared state for MCP tools.

Holds agent profiles, prompt versions, metrics history, experiments, and improvements.
"""

from __future__ import annotations

from typing import Any

_agent_profile: dict[str, Any] | None = None
_prompt_versions: list[dict[str, Any]] = []  # version history
_metrics_history: list[dict[str, Any]] = []
_experiments: list[dict[str, Any]] = []
_improvements: list[dict[str, Any]] = []
_output_dir: str = "./evolver-output"


# -- Agent Profile --

def set_agent_profile(profile: dict[str, Any]) -> None:
    global _agent_profile
    _agent_profile = profile


def get_agent_profile() -> dict[str, Any]:
    if _agent_profile is None:
        raise RuntimeError("No agent analyzed. Use analyze_agent first.")
    return _agent_profile


# -- Prompt Versions --

def add_prompt_version(version: dict[str, Any]) -> int:
    """Add a prompt version and return its index."""
    version["version_id"] = len(_prompt_versions)
    _prompt_versions.append(version)
    return version["version_id"]


def get_prompt_version(version_id: int) -> dict[str, Any] | None:
    if 0 <= version_id < len(_prompt_versions):
        return _prompt_versions[version_id]
    return None


def get_all_versions() -> list[dict[str, Any]]:
    return _prompt_versions


def get_latest_version() -> dict[str, Any] | None:
    return _prompt_versions[-1] if _prompt_versions else None


# -- Metrics --

def add_metrics(metrics: dict[str, Any]) -> None:
    _metrics_history.append(metrics)


def get_metrics_history() -> list[dict[str, Any]]:
    return _metrics_history


# -- Experiments --

def add_experiment(experiment: dict[str, Any]) -> None:
    _experiments.append(experiment)


def get_experiments() -> list[dict[str, Any]]:
    return _experiments


# -- Improvements --

def add_improvement(improvement: dict[str, Any]) -> None:
    _improvements.append(improvement)


def get_improvements() -> list[dict[str, Any]]:
    return _improvements


# -- Output Dir --

def set_output_dir(path: str) -> None:
    global _output_dir
    _output_dir = path


def get_output_dir() -> str:
    return _output_dir
