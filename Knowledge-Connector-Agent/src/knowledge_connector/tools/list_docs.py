"""list_docs MCP tool — list all indexed documents with metadata."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from knowledge_connector.state import get_documents, get_knowledge_graph


@tool(
    "list_docs",
    "List all indexed documents with metadata. Optional 'file_type' to filter "
    "(e.g., 'markdown', 'code', 'config'). Optional 'sort_by': 'name', 'size', 'lines'.",
    {"file_type": str, "sort_by": str},
)
async def list_docs(args: dict[str, Any]) -> dict[str, Any]:
    documents = get_documents()
    kg = get_knowledge_graph()

    file_type = args.get("file_type")
    sort_by = args.get("sort_by", "name")

    docs = documents
    if file_type:
        docs = [d for d in docs if d.file_type == file_type]

    # Sort
    if sort_by == "size":
        docs = sorted(docs, key=lambda d: d.size_bytes, reverse=True)
    elif sort_by == "lines":
        docs = sorted(docs, key=lambda d: d.line_count, reverse=True)
    else:
        docs = sorted(docs, key=lambda d: d.filepath)

    result = {
        "total_documents": len(docs),
        "documents": [
            {
                "filepath": d.filepath,
                "title": d.title,
                "file_type": d.file_type,
                "extension": d.extension,
                "lines": d.line_count,
                "size_kb": round(d.size_bytes / 1024, 1),
                "headings_count": len(d.headings),
                "concepts": len(kg.get_document_concepts(d.filepath)),
            }
            for d in docs
        ],
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
