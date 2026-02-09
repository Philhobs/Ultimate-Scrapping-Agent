"""query_graph MCP tool — query the dependency graph."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from github_guru.state import get_graph


@tool(
    "query_graph",
    "Query the dependency graph. "
    "Actions: 'dependents' (what depends on a node), "
    "'dependencies' (what a node depends on), "
    "'path' (shortest path between two nodes), "
    "'summary' (graph overview). "
    "Node IDs use format 'file:<path>', 'class:<path>:<name>', 'func:<path>:<name>'.",
    {"action": str, "node_id": str, "target_id": str},
)
async def query_graph(args: dict[str, Any]) -> dict[str, Any]:
    graph = get_graph()
    action = args.get("action", "summary")
    node_id = args.get("node_id")
    target_id = args.get("target_id")

    if action == "summary":
        result = graph.get_summary()

    elif action == "dependents":
        if not node_id:
            return _error("node_id required for 'dependents' action")
        # Try to find the node by partial match
        resolved = _resolve_node_id(node_id, graph)
        if not resolved:
            return _error(f"Node not found: {node_id}")
        nodes = graph.get_dependents(resolved)
        result = {
            "node": resolved,
            "dependents": [{"id": n.id, "name": n.name, "type": n.node_type.value} for n in nodes],
            "count": len(nodes),
        }

    elif action == "dependencies":
        if not node_id:
            return _error("node_id required for 'dependencies' action")
        resolved = _resolve_node_id(node_id, graph)
        if not resolved:
            return _error(f"Node not found: {node_id}")
        nodes = graph.get_dependencies(resolved)
        result = {
            "node": resolved,
            "dependencies": [{"id": n.id, "name": n.name, "type": n.node_type.value} for n in nodes],
            "count": len(nodes),
        }

    elif action == "path":
        if not node_id or not target_id:
            return _error("node_id and target_id required for 'path' action")
        start = _resolve_node_id(node_id, graph)
        end = _resolve_node_id(target_id, graph)
        if not start:
            return _error(f"Start node not found: {node_id}")
        if not end:
            return _error(f"End node not found: {target_id}")
        path = graph.find_path(start, end)
        if path is None:
            result = {"path": None, "message": "No path found between nodes"}
        else:
            result = {
                "path": path,
                "length": len(path),
                "nodes": [
                    {"id": nid, "name": graph.nodes[nid].name, "type": graph.nodes[nid].node_type.value}
                    for nid in path if nid in graph.nodes
                ],
            }

    else:
        return _error(f"Unknown action: {action}")

    return {
        "content": [{
            "type": "text",
            "text": json.dumps(result, indent=2),
        }]
    }


def _resolve_node_id(node_id: str, graph) -> str | None:
    """Resolve a potentially partial node ID to a full one."""
    if node_id in graph.nodes:
        return node_id
    # Try prefix match
    matches = [nid for nid in graph.nodes if nid.endswith(node_id) or node_id in nid]
    if len(matches) == 1:
        return matches[0]
    # Try matching by filepath for file nodes
    file_matches = [nid for nid in graph.nodes if nid.startswith("file:") and node_id in nid]
    if len(file_matches) == 1:
        return file_matches[0]
    return None


def _error(msg: str) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": msg}],
        "is_error": True,
    }
