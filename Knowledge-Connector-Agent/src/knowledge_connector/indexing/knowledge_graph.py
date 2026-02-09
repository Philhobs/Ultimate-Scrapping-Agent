"""Knowledge Graph — extract concepts and relationships from documents."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import networkx as nx

from knowledge_connector.indexing.scanner import DocumentInfo


class KnowledgeGraph:
    """A graph of concepts and relationships extracted from documents."""

    def __init__(self) -> None:
        self._graph = nx.DiGraph()
        self._doc_concepts: dict[str, list[str]] = {}  # filepath -> concepts

    def build(self, documents: list[DocumentInfo]) -> None:
        """Build the knowledge graph from all indexed documents."""
        # Add document nodes
        for doc in documents:
            self._graph.add_node(
                f"doc:{doc.filepath}",
                type="document",
                title=doc.title,
                file_type=doc.file_type,
                headings=doc.headings,
            )

        # Extract concepts from each document
        for doc in documents:
            concepts = self._extract_concepts(doc)
            self._doc_concepts[doc.filepath] = concepts

            for concept in concepts:
                concept_id = f"concept:{concept.lower()}"
                if not self._graph.has_node(concept_id):
                    self._graph.add_node(concept_id, type="concept", label=concept)
                self._graph.add_edge(
                    f"doc:{doc.filepath}", concept_id,
                    relation="mentions",
                )

        # Cross-link documents that share concepts
        concept_to_docs: dict[str, list[str]] = defaultdict(list)
        for filepath, concepts in self._doc_concepts.items():
            for concept in concepts:
                concept_to_docs[concept.lower()].append(filepath)

        for concept, filepaths in concept_to_docs.items():
            if len(filepaths) > 1:
                for i, fp1 in enumerate(filepaths):
                    for fp2 in filepaths[i + 1:]:
                        edge_key = (f"doc:{fp1}", f"doc:{fp2}")
                        if self._graph.has_edge(*edge_key):
                            data = self._graph.edges[edge_key]
                            data["shared_concepts"].append(concept)
                            data["weight"] += 1
                        else:
                            self._graph.add_edge(
                                *edge_key,
                                relation="shares_concepts",
                                shared_concepts=[concept],
                                weight=1,
                            )

    def _extract_concepts(self, doc: DocumentInfo) -> list[str]:
        """Extract key concepts from a document using heuristics."""
        concepts: list[str] = []

        # From headings (markdown)
        for h in doc.headings:
            text = h.lstrip("#").strip()
            if text and len(text) < 80:
                concepts.append(text)

        content = doc.content

        # Capitalized multi-word terms (likely proper nouns / project names)
        caps = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', content)
        concepts.extend(set(caps))

        # Code identifiers: class/function definitions
        if doc.file_type == "code":
            classes = re.findall(r'class\s+(\w+)', content)
            functions = re.findall(r'def\s+(\w+)', content)
            concepts.extend(classes)
            concepts.extend([f for f in functions if not f.startswith("_")])

        # Markdown bold terms (often key concepts)
        if doc.file_type == "markdown":
            bold = re.findall(r'\*\*([^*]{2,50})\*\*', content)
            concepts.extend(bold)

        # API endpoints
        endpoints = re.findall(r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[\w/{}\-]+)', content)
        concepts.extend(endpoints)

        # Version numbers mentioned
        versions = re.findall(r'v\d+\.\d+(?:\.\d+)?', content)
        concepts.extend(versions)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for c in concepts:
            key = c.lower().strip()
            if key and key not in seen and len(key) > 1:
                seen.add(key)
                unique.append(c.strip())

        return unique

    def get_document_concepts(self, filepath: str) -> list[str]:
        """Get all concepts extracted from a specific document."""
        return self._doc_concepts.get(filepath, [])

    def get_related_documents(self, filepath: str) -> list[dict[str, Any]]:
        """Find documents related to a given one via shared concepts."""
        node = f"doc:{filepath}"
        if not self._graph.has_node(node):
            return []

        related = []
        for neighbor in self._graph.neighbors(node):
            if not neighbor.startswith("doc:"):
                continue
            edge = self._graph.edges[node, neighbor]
            if edge.get("relation") == "shares_concepts":
                related.append({
                    "filepath": neighbor.replace("doc:", ""),
                    "shared_concepts": edge.get("shared_concepts", []),
                    "weight": edge.get("weight", 0),
                })

        # Also check reverse edges
        for pred in self._graph.predecessors(node):
            if not pred.startswith("doc:"):
                continue
            edge = self._graph.edges[pred, node]
            if edge.get("relation") == "shares_concepts":
                fp = pred.replace("doc:", "")
                if not any(r["filepath"] == fp for r in related):
                    related.append({
                        "filepath": fp,
                        "shared_concepts": edge.get("shared_concepts", []),
                        "weight": edge.get("weight", 0),
                    })

        return sorted(related, key=lambda x: x["weight"], reverse=True)

    def get_concept_documents(self, concept: str) -> list[str]:
        """Find all documents that mention a concept."""
        concept_id = f"concept:{concept.lower()}"
        if not self._graph.has_node(concept_id):
            return []
        return [
            pred.replace("doc:", "")
            for pred in self._graph.predecessors(concept_id)
            if pred.startswith("doc:")
        ]

    def find_path(self, source: str, target: str) -> list[str] | None:
        """Find the shortest path between two documents or concepts."""
        src = source if source.startswith(("doc:", "concept:")) else f"doc:{source}"
        tgt = target if target.startswith(("doc:", "concept:")) else f"doc:{target}"

        if not self._graph.has_node(src) or not self._graph.has_node(tgt):
            return None

        try:
            path = nx.shortest_path(self._graph.to_undirected(), src, tgt)
            return path
        except nx.NetworkXNoPath:
            return None

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of the knowledge graph."""
        doc_nodes = [n for n in self._graph.nodes if n.startswith("doc:")]
        concept_nodes = [n for n in self._graph.nodes if n.startswith("concept:")]

        # Most connected concepts
        concept_degree = {
            n: self._graph.in_degree(n)
            for n in concept_nodes
        }
        top_concepts = sorted(concept_degree.items(), key=lambda x: x[1], reverse=True)[:15]

        return {
            "total_documents": len(doc_nodes),
            "total_concepts": len(concept_nodes),
            "total_edges": self._graph.number_of_edges(),
            "top_concepts": [
                {"concept": n.replace("concept:", ""), "mentioned_in": deg}
                for n, deg in top_concepts
            ],
        }

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph
