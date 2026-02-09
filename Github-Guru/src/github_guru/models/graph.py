"""Dependency graph model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RelationType(str, Enum):
    IMPORTS = "imports"
    CALLS = "calls"
    INHERITS = "inherits"
    CONTAINS = "contains"


class NodeType(str, Enum):
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    MODULE = "module"


@dataclass
class GraphNode:
    id: str
    node_type: NodeType
    name: str
    filepath: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "name": self.name,
            "filepath": self.filepath,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphNode:
        data = dict(data)
        data["node_type"] = NodeType(data["node_type"])
        return cls(**data)


@dataclass
class GraphEdge:
    source: str
    target: str
    relation: RelationType
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphEdge:
        data = dict(data)
        data["relation"] = RelationType(data["relation"])
        return cls(**data)


@dataclass
class DependencyGraph:
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)

    def get_dependents(self, node_id: str) -> list[GraphNode]:
        """Get nodes that depend on the given node (incoming edges)."""
        dependent_ids = [e.source for e in self.edges if e.target == node_id]
        return [self.nodes[nid] for nid in dependent_ids if nid in self.nodes]

    def get_dependencies(self, node_id: str) -> list[GraphNode]:
        """Get nodes that the given node depends on (outgoing edges)."""
        dep_ids = [e.target for e in self.edges if e.source == node_id]
        return [self.nodes[nid] for nid in dep_ids if nid in self.nodes]

    def get_edges_for(self, node_id: str) -> list[GraphEdge]:
        """Get all edges involving a node."""
        return [e for e in self.edges if e.source == node_id or e.target == node_id]

    def find_path(self, start_id: str, end_id: str) -> list[str] | None:
        """BFS to find shortest path between two nodes."""
        if start_id not in self.nodes or end_id not in self.nodes:
            return None
        if start_id == end_id:
            return [start_id]

        visited: set[str] = set()
        queue: list[list[str]] = [[start_id]]

        while queue:
            path = queue.pop(0)
            current = path[-1]
            if current == end_id:
                return path
            if current in visited:
                continue
            visited.add(current)
            # Follow outgoing edges
            for edge in self.edges:
                if edge.source == current and edge.target not in visited:
                    queue.append(path + [edge.target])
                elif edge.target == current and edge.source not in visited:
                    queue.append(path + [edge.source])

        return None

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the graph."""
        node_types: dict[str, int] = {}
        for node in self.nodes.values():
            key = node.node_type.value
            node_types[key] = node_types.get(key, 0) + 1

        relation_types: dict[str, int] = {}
        for edge in self.edges:
            key = edge.relation.value
            relation_types[key] = relation_types.get(key, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": node_types,
            "relation_types": relation_types,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DependencyGraph:
        graph = cls()
        for nid, ndata in data.get("nodes", {}).items():
            graph.nodes[nid] = GraphNode.from_dict(ndata)
        for edata in data.get("edges", []):
            graph.edges.append(GraphEdge.from_dict(edata))
        return graph
