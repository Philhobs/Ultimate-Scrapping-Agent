"""Shared state for MCP tools.

Module-level globals avoid circular imports between agent.py and tool modules.
The agent sets state at startup; tools read from it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from api_integrator.registry.api_registry import APIRegistry
    from api_integrator.registry.model_registry import ModelRegistry

_api_registry: APIRegistry | None = None
_model_registry: ModelRegistry | None = None
_pipeline_results: dict[str, Any] = {}


def set_state(
    api_registry: APIRegistry,
    model_registry: ModelRegistry,
) -> None:
    global _api_registry, _model_registry, _pipeline_results
    _api_registry = api_registry
    _model_registry = model_registry
    _pipeline_results = {}


def get_api_registry() -> APIRegistry:
    if _api_registry is None:
        raise RuntimeError("API registry not initialized. Run setup first.")
    return _api_registry


def get_model_registry() -> ModelRegistry:
    if _model_registry is None:
        raise RuntimeError("Model registry not initialized. Run setup first.")
    return _model_registry


def store_result(key: str, value: Any) -> None:
    """Store an intermediate result for pipeline chaining."""
    _pipeline_results[key] = value


def get_result(key: str) -> Any | None:
    """Retrieve a stored pipeline result."""
    return _pipeline_results.get(key)


def list_results() -> dict[str, str]:
    """List all stored result keys with type info."""
    return {
        k: f"{type(v).__name__} ({len(str(v))} chars)"
        for k, v in _pipeline_results.items()
    }


def clear_results() -> None:
    """Clear all stored pipeline results."""
    _pipeline_results.clear()
