"""Embeddings — generate and search vector embeddings for document chunks."""

from __future__ import annotations

from typing import Any

import numpy as np

from knowledge_connector.indexing.chunker import Chunk

# Lazy-loaded model
_model = None


def _get_model():
    """Lazy-load the sentence-transformers model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


class EmbeddingIndex:
    """Vector index for semantic search over document chunks."""

    def __init__(self) -> None:
        self._embeddings: np.ndarray | None = None
        self._chunks: list[Chunk] = []

    def build(self, chunks: list[Chunk], batch_size: int = 64) -> None:
        """Generate embeddings for all chunks."""
        if not chunks:
            return

        self._chunks = chunks
        model = _get_model()

        texts = [self._chunk_text(c) for c in chunks]
        self._embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False)

    def search(self, query: str, top_k: int = 10, threshold: float = 0.0) -> list[dict[str, Any]]:
        """Search for chunks most similar to the query."""
        if self._embeddings is None or len(self._chunks) == 0:
            return []

        model = _get_model()
        query_emb = model.encode([query])[0]

        # Cosine similarity
        norms = np.linalg.norm(self._embeddings, axis=1)
        query_norm = np.linalg.norm(query_emb)
        similarities = np.dot(self._embeddings, query_emb) / (norms * query_norm + 1e-10)

        # Top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score < threshold:
                continue
            chunk = self._chunks[idx]
            results.append({
                "chunk_id": chunk.chunk_id,
                "filepath": chunk.doc_filepath,
                "title": chunk.doc_title,
                "heading": chunk.heading,
                "text": chunk.text[:500],
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "file_type": chunk.file_type,
                "score": round(score, 4),
            })

        return results

    def find_similar_chunks(self, chunk_idx: int, top_k: int = 5) -> list[dict[str, Any]]:
        """Find chunks most similar to a given chunk (for cross-linking)."""
        if self._embeddings is None or chunk_idx >= len(self._chunks):
            return []

        source = self._chunks[chunk_idx]
        query_emb = self._embeddings[chunk_idx]

        norms = np.linalg.norm(self._embeddings, axis=1)
        query_norm = np.linalg.norm(query_emb)
        similarities = np.dot(self._embeddings, query_emb) / (norms * query_norm + 1e-10)

        # Exclude same document
        top_indices = np.argsort(similarities)[::-1]
        results = []
        for idx in top_indices:
            if idx == chunk_idx:
                continue
            chunk = self._chunks[idx]
            if chunk.doc_filepath == source.doc_filepath:
                continue
            score = float(similarities[idx])
            if score < 0.3:
                break
            results.append({
                "source_file": source.doc_filepath,
                "source_heading": source.heading,
                "related_file": chunk.doc_filepath,
                "related_heading": chunk.heading,
                "related_text": chunk.text[:300],
                "score": round(score, 4),
            })
            if len(results) >= top_k:
                break

        return results

    @property
    def chunks(self) -> list[Chunk]:
        return self._chunks

    @property
    def embeddings(self) -> np.ndarray | None:
        return self._embeddings

    def _chunk_text(self, chunk: Chunk) -> str:
        """Build the text to embed — includes context."""
        parts = [f"File: {chunk.doc_filepath}"]
        if chunk.heading and chunk.heading != chunk.doc_title:
            parts.append(f"Section: {chunk.heading}")
        parts.append(chunk.text)
        return " | ".join(parts)
