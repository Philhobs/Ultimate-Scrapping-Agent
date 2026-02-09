"""suggest_updates MCP tool — suggest documentation improvements for a document."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from knowledge_connector.state import (
    get_documents, get_document, get_knowledge_graph, get_embedding_index,
)


@tool(
    "suggest_updates",
    "Analyze a document and suggest improvements: missing cross-references, "
    "outdated sections, gaps that other documents cover, and sections that "
    "could be expanded. Provide 'filepath' of the document to analyze.",
    {"filepath": str},
)
async def suggest_updates(args: dict[str, Any]) -> dict[str, Any]:
    filepath = args.get("filepath", "")
    if not filepath:
        return {
            "content": [{"type": "text", "text": "Error: 'filepath' is required."}],
            "is_error": True,
        }

    doc = get_document(filepath)
    if doc is None:
        available = [d.filepath for d in get_documents()[:20]]
        return {
            "content": [{"type": "text", "text": f"Error: Document '{filepath}' not found. Available: {available}"}],
            "is_error": True,
        }

    suggestions: list[dict[str, Any]] = []
    kg = get_knowledge_graph()
    index = get_embedding_index()

    # 1. Missing cross-references
    related = kg.get_related_documents(filepath)
    if related:
        # Check which related docs are actually referenced in this doc
        content_lower = doc.content.lower()
        unreferenced = []
        for r in related[:10]:
            ref_fp = r["filepath"]
            # Check if this doc mentions the related file
            ref_name = ref_fp.replace("/", " ").replace("\\", " ").replace("_", " ").replace("-", " ").lower()
            ref_stem = ref_fp.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
            if ref_stem not in content_lower and ref_fp not in doc.content:
                unreferenced.append({
                    "file": ref_fp,
                    "shared_concepts": r["shared_concepts"][:5],
                    "relevance": r["weight"],
                })

        if unreferenced:
            suggestions.append({
                "type": "missing_cross_references",
                "severity": "medium",
                "message": f"Found {len(unreferenced)} related document(s) not referenced.",
                "unreferenced_docs": unreferenced[:5],
            })

    # 2. Short sections that could be expanded
    if doc.file_type == "markdown" and doc.headings:
        lines = doc.content.split("\n")
        sections: list[tuple[str, int, int]] = []
        current_heading = ""
        current_start = 0

        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                if current_heading:
                    sections.append((current_heading, current_start, i))
                current_heading = line.strip().lstrip("#").strip()
                current_start = i

        if current_heading:
            sections.append((current_heading, current_start, len(lines)))

        short_sections = []
        for heading, start, end in sections:
            length = end - start
            if 1 < length < 5:
                # Find related content in other docs
                related_chunks = index.search(heading, top_k=3, threshold=0.3)
                other_doc_chunks = [c for c in related_chunks if c["filepath"] != filepath]
                if other_doc_chunks:
                    short_sections.append({
                        "heading": heading,
                        "line": start + 1,
                        "current_lines": length,
                        "expandable_from": [
                            {"file": c["filepath"], "heading": c["heading"], "score": c["score"]}
                            for c in other_doc_chunks[:2]
                        ],
                    })

        if short_sections:
            suggestions.append({
                "type": "expandable_sections",
                "severity": "low",
                "message": f"Found {len(short_sections)} short section(s) with related content elsewhere.",
                "sections": short_sections[:5],
            })

    # 3. Concepts mentioned in this doc but better covered elsewhere
    concepts = kg.get_document_concepts(filepath)
    concept_coverage: list[dict[str, Any]] = []
    for concept in concepts[:10]:
        docs_with_concept = kg.get_concept_documents(concept)
        other_docs = [d for d in docs_with_concept if d != filepath]
        if other_docs:
            concept_coverage.append({
                "concept": concept,
                "also_in": other_docs[:3],
            })

    if concept_coverage:
        suggestions.append({
            "type": "concept_coverage",
            "severity": "info",
            "message": f"{len(concept_coverage)} concept(s) also covered in other documents.",
            "concepts": concept_coverage[:8],
        })

    result = {
        "document": filepath,
        "title": doc.title,
        "total_suggestions": len(suggestions),
        "suggestions": suggestions,
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
