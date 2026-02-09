"""search MCP tool — semantic search across all indexed documents."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from knowledge_connector.state import get_embedding_index


@tool(
    "search",
    "Semantic search across all indexed documents. Finds relevant passages even "
    "when terminology differs. Provide 'query' text. Optional: 'top_k' (default 10), "
    "'threshold' (minimum similarity score, default 0.0).",
    {"query": str, "top_k": int, "threshold": float},
)
async def search(args: dict[str, Any]) -> dict[str, Any]:
    query = args.get("query", "")
    if not query:
        return {
            "content": [{"type": "text", "text": "Error: 'query' is required."}],
            "is_error": True,
        }

    top_k = args.get("top_k", 10)
    threshold = args.get("threshold", 0.0)

    index = get_embedding_index()
    results = index.search(query, top_k=top_k, threshold=threshold)

    if not results:
        return {"content": [{"type": "text", "text": "No relevant results found."}]}

    output = {
        "query": query,
        "results_count": len(results),
        "results": results,
    }

    return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}
