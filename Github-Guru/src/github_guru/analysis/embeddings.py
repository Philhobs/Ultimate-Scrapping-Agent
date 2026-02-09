"""Semantic embedding index using Sentence Transformers."""

from __future__ import annotations

from typing import Any

import numpy as np

from github_guru.analysis.chunker import CodeChunk

MODEL_NAME = "all-MiniLM-L6-v2"


class CodeEmbeddingIndex:
    """Build and query a semantic embedding index over code chunks."""

    def __init__(self) -> None:
        self._model = None
        self._embeddings: np.ndarray | None = None
        self._chunks: list[CodeChunk] = []

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model

    def build(self, chunks: list[CodeChunk]) -> None:
        """Compute embeddings for all chunks."""
        self._chunks = chunks
        if not chunks:
            self._embeddings = np.array([])
            return

        model = self._load_model()
        texts = [c.to_embedding_text() for c in chunks]
        self._embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    def load(self, embeddings: np.ndarray, chunks: list[dict[str, Any]]) -> None:
        """Load pre-computed embeddings and chunk metadata."""
        self._embeddings = embeddings
        self._chunks = [CodeChunk.from_dict(c) for c in chunks]

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Search for chunks most similar to the query."""
        if self._embeddings is None or len(self._embeddings) == 0:
            return []

        model = self._load_model()
        query_embedding = model.encode([query], convert_to_numpy=True)[0]

        # Cosine similarity
        norms = np.linalg.norm(self._embeddings, axis=1)
        query_norm = np.linalg.norm(query_embedding)
        # Avoid division by zero
        norms = np.maximum(norms, 1e-10)
        query_norm = max(query_norm, 1e-10)

        similarities = self._embeddings @ query_embedding / (norms * query_norm)
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            chunk = self._chunks[idx]
            results.append({
                "content": chunk.content,
                "filepath": chunk.filepath,
                "chunk_type": chunk.chunk_type,
                "name": chunk.name,
                "line_start": chunk.line_start,
                "line_end": chunk.line_end,
                "similarity": float(similarities[idx]),
            })
        return results

    def get_embeddings(self) -> np.ndarray | None:
        return self._embeddings

    def get_chunks_metadata(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._chunks]
