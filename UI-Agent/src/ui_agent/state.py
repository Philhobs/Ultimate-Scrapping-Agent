"""Shared state for UI Agent MCP tools.

Holds design context, generated files, output directory, and project profile.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ui_agent.analyzers.design_scanner import DesignProfile

_design_context: dict[str, Any] = {}
_generated_files: dict[str, str] = {}  # filename -> content
_output_dir: str = "./ui-output"
_image_path: str | None = None
_project_profile: DesignProfile | None = None


def set_design_context(context: dict[str, Any]) -> None:
    global _design_context
    _design_context = context


def get_design_context() -> dict[str, Any]:
    return _design_context


def set_image_path(path: str | None) -> None:
    global _image_path
    _image_path = path


def get_image_path() -> str | None:
    return _image_path


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


def set_profile(profile: DesignProfile) -> None:
    global _project_profile
    _project_profile = profile


def get_profile() -> DesignProfile | None:
    return _project_profile
