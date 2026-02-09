"""get_context MCP tool — retrieve comprehensive context about a topic from all sources."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from knowledge_connector.state import get_embedding_index, get_knowledge_graph


@tool(
    "get_context",
    "Retrieve comprehensive context about a topic by gathering relevant passages "
    "from ALL indexed sources. Like RAG retrieval — combines information from "
    "multiple documents into a unified view with source citations. "
    "Provide 'topic' text. Optional: 'top_k' (max passages, default 8).",
    {"topic": str, "top_k": int},
)
async def get_context(args: dict[str, Any]) -> dict[str, Any]:
    topic = args.get("topic", "")
    if not topic:
        return {
            "content": [{"type": "text", "text": "Error: 'topic' is required."}],
            "is_error": True,
        }

    top_k = args.get("top_k", 8)
    index = get_embedding_index()
    kg = get_knowledge_graph()

    # 1. Semantic search for relevant passages
    results = index.search(topic, top_k=top_k, threshold=0.2)

    # 2. Also check knowledge graph for concept matches
    concept_docs = kg.get_concept_documents(topic)

    # 3. Organize by source document
    sources: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        fp = r["filepath"]
        if fp not in sources:
            sources[fp] = []
        sources[fp].append({
            "heading": r["heading"],
            "text": r["text"],
            "lines": f"{r['start_line']}-{r['end_line']}",
            "score": r["score"],
        })

    # Add concept graph info
    graph_docs = [d for d in concept_docs if d not in sources]

    output = {
        "topic": topic,
        "sources_found": len(sources),
        "total_passages": len(results),
        "context_by_source": [
            {
                "document": fp,
                "passages": passages,
            }
            for fp, passages in sorted(sources.items(), key=lambda x: max(p["score"] for p in x[1]), reverse=True)
        ],
    }

    if graph_docs:
        output["also_mentioned_in"] = graph_docs[:5]

    return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}
