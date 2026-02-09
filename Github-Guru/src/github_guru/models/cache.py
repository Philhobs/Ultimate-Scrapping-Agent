"""Analysis cache for persisting results to .github-guru/ directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from github_guru.models.codebase import CodebaseAnalysis
from github_guru.models.graph import DependencyGraph


CACHE_DIR = ".github-guru"


class AnalysisCache:
    """Save and load analysis results from a .github-guru/ cache directory."""

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root)
        self.cache_dir = self.repo_root / CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def analysis_path(self) -> Path:
        return self.cache_dir / "analysis.json"

    @property
    def graph_path(self) -> Path:
        return self.cache_dir / "graph.json"

    @property
    def embeddings_path(self) -> Path:
        return self.cache_dir / "embeddings.npz"

    @property
    def chunks_path(self) -> Path:
        return self.cache_dir / "chunks.json"

    def has_cache(self) -> bool:
        return self.analysis_path.exists()

    def save_analysis(self, analysis: CodebaseAnalysis) -> None:
        with open(self.analysis_path, "w") as f:
            json.dump(analysis.to_dict(), f, indent=2)

    def load_analysis(self) -> CodebaseAnalysis | None:
        if not self.analysis_path.exists():
            return None
        with open(self.analysis_path) as f:
            return CodebaseAnalysis.from_dict(json.load(f))

    def save_graph(self, graph: DependencyGraph) -> None:
        with open(self.graph_path, "w") as f:
            json.dump(graph.to_dict(), f, indent=2)

    def load_graph(self) -> DependencyGraph | None:
        if not self.graph_path.exists():
            return None
        with open(self.graph_path) as f:
            return DependencyGraph.from_dict(json.load(f))

    def save_embeddings(self, embeddings: np.ndarray, chunks: list[dict[str, Any]]) -> None:
        np.savez_compressed(self.embeddings_path, embeddings=embeddings)
        with open(self.chunks_path, "w") as f:
            json.dump(chunks, f, indent=2)

    def load_embeddings(self) -> tuple[np.ndarray, list[dict[str, Any]]] | None:
        if not self.embeddings_path.exists() or not self.chunks_path.exists():
            return None
        data = np.load(self.embeddings_path)
        with open(self.chunks_path) as f:
            chunks = json.load(f)
        return data["embeddings"], chunks
