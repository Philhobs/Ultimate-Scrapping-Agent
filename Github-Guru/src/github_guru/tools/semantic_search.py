"""semantic_search MCP tool — search code by meaning using embeddings."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from github_guru.state import get_embedding_index


@tool(
    "semantic_search",
    "Search the codebase by meaning using semantic embeddings. "
    "Finds code chunks most similar to the natural language query. "
    "Returns chunks with similarity scores.",
    {"query": str, "top_k": int},
)
async def semantic_search(args: dict[str, Any]) -> dict[str, Any]:
    index = get_embedding_index()
    query = args["query"]
    top_k = args.get("top_k", 10)

    results = index.search(query, top_k=top_k)

    # Truncate content for readability
    for r in results:
        if len(r["content"]) > 2000:
            r["content"] = r["content"][:2000] + "\n... [truncated]"
        r["similarity"] = round(r["similarity"], 4)

    return {
        "content": [{
            "type": "text",
            "text": json.dumps({
                "query": query,
                "results": results,
                "count": len(results),
            }, indent=2),
        }]
    }
