"""KnowledgeConnectorAgent — orchestrates document linking, search, and consistency."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from knowledge_connector.indexing.scanner import scan_directory
from knowledge_connector.indexing.chunker import chunk_all
from knowledge_connector.indexing.embeddings import EmbeddingIndex
from knowledge_connector.indexing.knowledge_graph import KnowledgeGraph
from knowledge_connector.system_prompt import SYSTEM_PROMPT
from knowledge_connector import state

console = Console()


def _get_all_tools() -> list:
    """Import and return all MCP tool functions."""
    from knowledge_connector.tools.scan_docs import scan_docs
    from knowledge_connector.tools.search import search
    from knowledge_connector.tools.find_links import find_links
    from knowledge_connector.tools.check_consistency import check_consistency
    from knowledge_connector.tools.query_graph import query_graph
    from knowledge_connector.tools.suggest_updates import suggest_updates
    from knowledge_connector.tools.get_context import get_context
    from knowledge_connector.tools.list_docs import list_docs
    return [scan_docs, search, find_links, check_consistency, query_graph, suggest_updates, get_context, list_docs]


TOOL_NAMES = [
    "mcp__kc__scan_docs",
    "mcp__kc__search",
    "mcp__kc__find_links",
    "mcp__kc__check_consistency",
    "mcp__kc__query_graph",
    "mcp__kc__suggest_updates",
    "mcp__kc__get_context",
    "mcp__kc__list_docs",
]


class KnowledgeConnectorAgent:
    """Main agent that handles document linking, search, and consistency checks."""

    def __init__(self) -> None:
        self._indexed = False

    def index(self, path: str) -> dict[str, Any]:
        """Scan and index all documents in a directory."""
        console.print(f"[bold blue]Scanning:[/] {path}")
        documents = scan_directory(path)
        console.print(f"  Found [green]{len(documents)}[/] documents")

        console.print("[bold blue]Chunking...[/]")
        chunks = chunk_all(documents)
        console.print(f"  Created [green]{len(chunks)}[/] chunks")

        console.print("[bold blue]Building embeddings...[/]")
        embedding_index = EmbeddingIndex()
        embedding_index.build(chunks)

        console.print("[bold blue]Building knowledge graph...[/]")
        kg = KnowledgeGraph()
        kg.build(documents)
        summary = kg.get_summary()
        console.print(f"  {summary['total_concepts']} concepts, {summary['total_edges']} edges")

        state.set_state(documents, chunks, embedding_index, kg, path)
        self._indexed = True

        console.print("[bold green]Indexing complete![/]")
        return summary

    async def run(self, query: str, doc_path: str | None = None, max_turns: int = 25) -> str:
        """Run a query through the Claude Agent SDK with all tools."""
        from claude_agent_sdk import (
            ClaudeSDKClient,
            ClaudeAgentOptions,
            AssistantMessage,
            TextBlock,
            create_sdk_mcp_server,
        )

        server = create_sdk_mcp_server(
            name="kc",
            version="1.0.0",
            tools=_get_all_tools(),
        )

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"kc": server},
            allowed_tools=TOOL_NAMES,
            max_turns=max_turns,
        )

        # Build prompt
        if doc_path and not self._indexed:
            abs_path = str(Path(doc_path).resolve())
            prompt = (
                f"First, scan and index the documents at: {abs_path}\n\n"
                f"Then: {query}"
            )
        else:
            prompt = query

        full_response: list[str] = []

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response.append(block.text)

        return "\n".join(full_response) if full_response else "No response generated."
