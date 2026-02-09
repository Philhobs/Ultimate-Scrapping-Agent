"""Shared state for MCP tools.

Holds loaded DataFrames, trained models, evaluation results, and plot paths.
The agent sets state at startup; tools read/write to it throughout a session.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

# ── DataFrames ──────────────────────────────────────────────────────────────
_dataframes: dict[str, pd.DataFrame] = {}


def store_df(name: str, df: pd.DataFrame) -> None:
    _dataframes[name] = df


def get_df(name: str) -> pd.DataFrame | None:
    return _dataframes.get(name)


def list_dfs() -> dict[str, tuple[int, int]]:
    """Return {name: (rows, cols)} for every loaded DataFrame."""
    return {k: v.shape for k, v in _dataframes.items()}


def drop_df(name: str) -> bool:
    return _dataframes.pop(name, None) is not None


# ── Trained models ──────────────────────────────────────────────────────────
_models: dict[str, dict[str, Any]] = {}


def store_model(name: str, model: Any, metadata: dict[str, Any] | None = None) -> None:
    _models[name] = {"model": model, "metadata": metadata or {}}


def get_model(name: str) -> dict[str, Any] | None:
    return _models.get(name)


def list_models() -> dict[str, dict[str, Any]]:
    """Return {name: metadata} for every trained model."""
    return {k: v["metadata"] for k, v in _models.items()}


# ── Evaluation results ──────────────────────────────────────────────────────
_evaluations: dict[str, dict[str, Any]] = {}


def store_evaluation(name: str, results: dict[str, Any]) -> None:
    _evaluations[name] = results


def get_evaluation(name: str) -> dict[str, Any] | None:
    return _evaluations.get(name)


def list_evaluations() -> dict[str, str]:
    return {k: str(list(v.keys())) for k, v in _evaluations.items()}


# ── Plot paths ──────────────────────────────────────────────────────────────
_plots: list[str] = []


def store_plot(path: str) -> None:
    _plots.append(path)


def list_plots() -> list[str]:
    return list(_plots)


# ── Output directory ────────────────────────────────────────────────────────
_output_dir: str = "./output"


def set_output_dir(path: str) -> None:
    global _output_dir
    _output_dir = path


def get_output_dir() -> str:
    return _output_dir


# ── Reset ───────────────────────────────────────────────────────────────────
def reset() -> None:
    global _output_dir
    _dataframes.clear()
    _models.clear()
    _evaluations.clear()
    _plots.clear()
    _output_dir = "./output"
