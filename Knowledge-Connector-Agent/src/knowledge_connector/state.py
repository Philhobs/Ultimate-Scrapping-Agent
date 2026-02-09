"""Shared state for MCP tools.

Holds indexed documents, embedding index, knowledge graph, and scan root.
The agent sets state after scanning; tools read from it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from knowledge_connector.indexing.chunker import Chunk
    from knowledge_connector.indexing.embeddings import EmbeddingIndex
    from knowledge_connector.indexing.knowledge_graph import KnowledgeGraph
    from knowledge_connector.indexing.scanner import DocumentInfo

_documents: list[DocumentInfo] = []
_chunks: list[Chunk] = []
_embedding_index: EmbeddingIndex | None = None
_knowledge_graph: KnowledgeGraph | None = None
_root_path: str | None = None


def set_state(
    documents: list[DocumentInfo],
    chunks: list[Chunk],
    embedding_index: EmbeddingIndex,
    knowledge_graph: KnowledgeGraph,
    root_path: str,
) -> None:
    global _documents, _chunks, _embedding_index, _knowledge_graph, _root_path
    _documents = documents
    _chunks = chunks
    _embedding_index = embedding_index
    _knowledge_graph = knowledge_graph
    _root_path = root_path


def get_documents() -> list[DocumentInfo]:
    if not _documents:
        raise RuntimeError("No documents indexed. Run 'knowledge-connector index' first.")
    return _documents


def get_document(filepath: str) -> DocumentInfo | None:
    for doc in _documents:
        if doc.filepath == filepath:
            return doc
    return None


def get_chunks() -> list[Chunk]:
    return _chunks


def get_embedding_index() -> EmbeddingIndex:
    if _embedding_index is None:
        raise RuntimeError("No embedding index. Run 'knowledge-connector index' first.")
    return _embedding_index


def get_knowledge_graph() -> KnowledgeGraph:
    if _knowledge_graph is None:
        raise RuntimeError("No knowledge graph. Run 'knowledge-connector index' first.")
    return _knowledge_graph


def get_root_path() -> str:
    if _root_path is None:
        raise RuntimeError("No root path set. Run 'knowledge-connector index' first.")
    return _root_path
