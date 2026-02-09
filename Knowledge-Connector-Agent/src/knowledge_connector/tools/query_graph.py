"""query_graph MCP tool — query the knowledge graph of concepts and documents."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from knowledge_connector.state import get_knowledge_graph


@tool(
    "query_graph",
    "Query the knowledge graph. Provide 'action': "
    "'summary' (overview of graph stats and top concepts), "
    "'concepts' (list concepts for a document — provide 'filepath'), "
    "'documents' (find docs mentioning a concept — provide 'concept'), "
    "'related' (find documents related to a given one — provide 'filepath'), "
    "'path' (find connection path between two nodes — provide 'source' and 'target').",
    {"action": str, "filepath": str, "concept": str, "source": str, "target": str},
)
async def query_graph(args: dict[str, Any]) -> dict[str, Any]:
    action = args.get("action", "summary")
    kg = get_knowledge_graph()

    if action == "summary":
        summary = kg.get_summary()
        return {"content": [{"type": "text", "text": json.dumps(summary, indent=2)}]}

    elif action == "concepts":
        filepath = args.get("filepath", "")
        if not filepath:
            return {
                "content": [{"type": "text", "text": "Error: 'filepath' required for 'concepts' action."}],
                "is_error": True,
            }
        concepts = kg.get_document_concepts(filepath)
        result = {
            "document": filepath,
            "concepts": concepts,
            "count": len(concepts),
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    elif action == "documents":
        concept = args.get("concept", "")
        if not concept:
            return {
                "content": [{"type": "text", "text": "Error: 'concept' required for 'documents' action."}],
                "is_error": True,
            }
        docs = kg.get_concept_documents(concept)
        result = {
            "concept": concept,
            "documents": docs,
            "count": len(docs),
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    elif action == "related":
        filepath = args.get("filepath", "")
        if not filepath:
            return {
                "content": [{"type": "text", "text": "Error: 'filepath' required for 'related' action."}],
                "is_error": True,
            }
        related = kg.get_related_documents(filepath)
        result = {
            "document": filepath,
            "related": related,
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    elif action == "path":
        source = args.get("source", "")
        target = args.get("target", "")
        if not source or not target:
            return {
                "content": [{"type": "text", "text": "Error: 'source' and 'target' required for 'path' action."}],
                "is_error": True,
            }
        path = kg.find_path(source, target)
        if path is None:
            result = {"source": source, "target": target, "connected": False}
        else:
            result = {"source": source, "target": target, "connected": True, "path": path}
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    return {
        "content": [{"type": "text", "text": f"Unknown action '{action}'."}],
        "is_error": True,
    }
