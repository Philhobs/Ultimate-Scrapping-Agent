"""Shared state for MCP tools.

Module-level globals avoid circular imports between agent.py and tool modules.
The agent sets state after analysis; tools read from it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from github_guru.analysis.embeddings import CodeEmbeddingIndex
    from github_guru.models.codebase import CodebaseAnalysis
    from github_guru.models.graph import DependencyGraph

_analysis: CodebaseAnalysis | None = None
_graph: DependencyGraph | None = None
_embedding_index: CodeEmbeddingIndex | None = None
_repo_root: str | None = None


def set_state(
    analysis: CodebaseAnalysis,
    graph: DependencyGraph,
    embedding_index: CodeEmbeddingIndex,
    repo_root: str,
) -> None:
    global _analysis, _graph, _embedding_index, _repo_root
    _analysis = analysis
    _graph = graph
    _embedding_index = embedding_index
    _repo_root = repo_root


def get_analysis() -> CodebaseAnalysis:
    if _analysis is None:
        raise RuntimeError("No analysis loaded. Run 'github-guru analyze' first.")
    return _analysis


def get_graph() -> DependencyGraph:
    if _graph is None:
        raise RuntimeError("No graph loaded. Run 'github-guru analyze' first.")
    return _graph


def get_embedding_index() -> CodeEmbeddingIndex:
    if _embedding_index is None:
        raise RuntimeError("No embedding index loaded. Run 'github-guru analyze' first.")
    return _embedding_index


def get_repo_root() -> str:
    if _repo_root is None:
        raise RuntimeError("No repo root set. Run 'github-guru analyze' first.")
    return _repo_root
