"""find_links MCP tool — discover cross-document relationships and suggest links."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from knowledge_connector.state import get_embedding_index, get_knowledge_graph, get_documents


@tool(
    "find_links",
    "Find cross-document relationships for a given document. Uses both semantic "
    "similarity and the knowledge graph to discover related documents that should "
    "reference each other. Provide 'filepath' of the document. "
    "Optional: 'top_k' (max related docs, default 5).",
    {"filepath": str, "top_k": int},
)
async def find_links(args: dict[str, Any]) -> dict[str, Any]:
    filepath = args.get("filepath", "")
    top_k = args.get("top_k", 5)

    if not filepath:
        return {
            "content": [{"type": "text", "text": "Error: 'filepath' is required."}],
            "is_error": True,
        }

    kg = get_knowledge_graph()
    index = get_embedding_index()
    documents = get_documents()

    # Check document exists
    doc = None
    for d in documents:
        if d.filepath == filepath:
            doc = d
            break

    if doc is None:
        available = [d.filepath for d in documents[:20]]
        return {
            "content": [{"type": "text", "text": f"Error: Document '{filepath}' not found. Available: {available}"}],
            "is_error": True,
        }

    # 1. Graph-based relationships (shared concepts)
    graph_related = kg.get_related_documents(filepath)

    # 2. Embedding-based relationships (semantic similarity)
    # Find chunks belonging to this document, then find similar chunks in other docs
    chunks = index.chunks
    doc_chunk_indices = [i for i, c in enumerate(chunks) if c.doc_filepath == filepath]

    semantic_related: dict[str, float] = {}
    for idx in doc_chunk_indices[:5]:  # Sample up to 5 chunks
        similar = index.find_similar_chunks(idx, top_k=top_k)
        for s in similar:
            fp = s["related_file"]
            score = s["score"]
            if fp not in semantic_related or score > semantic_related[fp]:
                semantic_related[fp] = score

    # Combine results
    all_related: dict[str, dict[str, Any]] = {}

    for gr in graph_related:
        fp = gr["filepath"]
        all_related[fp] = {
            "filepath": fp,
            "shared_concepts": gr["shared_concepts"],
            "concept_weight": gr["weight"],
            "semantic_score": semantic_related.pop(fp, 0),
        }

    for fp, score in semantic_related.items():
        if fp not in all_related:
            all_related[fp] = {
                "filepath": fp,
                "shared_concepts": [],
                "concept_weight": 0,
                "semantic_score": score,
            }

    # Sort by combined relevance
    sorted_related = sorted(
        all_related.values(),
        key=lambda x: x["concept_weight"] * 0.4 + x["semantic_score"] * 0.6,
        reverse=True,
    )[:top_k]

    result = {
        "document": filepath,
        "title": doc.title,
        "concepts_in_document": kg.get_document_concepts(filepath)[:15],
        "related_documents": sorted_related,
        "suggestion": f"Consider adding cross-references between '{filepath}' and the related documents above.",
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
