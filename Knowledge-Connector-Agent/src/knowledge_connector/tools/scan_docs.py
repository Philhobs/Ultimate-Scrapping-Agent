"""scan_docs MCP tool — scan a directory and index all documents."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from knowledge_connector.indexing.scanner import scan_directory
from knowledge_connector.indexing.chunker import chunk_all
from knowledge_connector.indexing.embeddings import EmbeddingIndex
from knowledge_connector.indexing.knowledge_graph import KnowledgeGraph
from knowledge_connector import state


@tool(
    "scan_docs",
    "Scan a directory to index all documents. Builds embeddings for semantic search "
    "and a knowledge graph of concepts. Provide 'path' to the directory. "
    "Optional: 'ignore_patterns' (JSON list of glob patterns to skip).",
    {"path": str, "ignore_patterns": str},
)
async def scan_docs(args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path", ".")
    ignore_raw = args.get("ignore_patterns")
    ignore = []
    if ignore_raw:
        try:
            ignore = json.loads(ignore_raw) if isinstance(ignore_raw, str) else ignore_raw
        except (json.JSONDecodeError, TypeError):
            pass

    try:
        documents = scan_directory(path, ignore_patterns=ignore)
    except FileNotFoundError as e:
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "is_error": True,
        }

    if not documents:
        return {
            "content": [{"type": "text", "text": f"No documents found in '{path}'."}],
            "is_error": True,
        }

    # Chunk
    chunks = chunk_all(documents)

    # Build embedding index
    embedding_index = EmbeddingIndex()
    embedding_index.build(chunks)

    # Build knowledge graph
    kg = KnowledgeGraph()
    kg.build(documents)

    # Set shared state
    state.set_state(documents, chunks, embedding_index, kg, path)

    # Summary
    type_counts: dict[str, int] = {}
    for doc in documents:
        type_counts[doc.file_type] = type_counts.get(doc.file_type, 0) + 1

    graph_summary = kg.get_summary()

    result = {
        "documents_indexed": len(documents),
        "chunks_created": len(chunks),
        "file_types": type_counts,
        "total_lines": sum(d.line_count for d in documents),
        "knowledge_graph": {
            "concepts": graph_summary["total_concepts"],
            "edges": graph_summary["total_edges"],
            "top_concepts": graph_summary["top_concepts"][:10],
        },
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
