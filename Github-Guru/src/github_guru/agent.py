"""GitHubGuruAgent — orchestrates analysis and Claude Agent SDK interactions."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from rich.console import Console

from github_guru.analysis.ast_parser import parse_file
from github_guru.analysis.chunker import chunk_codebase
from github_guru.analysis.dependency_graph import build_dependency_graph
from github_guru.analysis.embeddings import CodeEmbeddingIndex
from github_guru.analysis.ingestion import ingest_repo
from github_guru.models.cache import AnalysisCache
from github_guru.models.codebase import CodebaseAnalysis, RepoInfo, detect_language
from github_guru.system_prompt import SYSTEM_PROMPT
from github_guru import state

console = Console()


def _get_all_tools() -> list:
    """Import and return all MCP tool functions."""
    from github_guru.tools.list_files import list_files
    from github_guru.tools.read_file import read_file
    from github_guru.tools.search_code import search_code
    from github_guru.tools.query_structure import query_structure
    from github_guru.tools.query_graph import query_graph
    from github_guru.tools.semantic_search import semantic_search
    from github_guru.tools.get_git_info import get_git_info
    return [list_files, read_file, search_code, query_structure, query_graph, semantic_search, get_git_info]


TOOL_NAMES = [
    "mcp__guru__list_files",
    "mcp__guru__read_file",
    "mcp__guru__search_code",
    "mcp__guru__query_structure",
    "mcp__guru__query_graph",
    "mcp__guru__semantic_search",
    "mcp__guru__get_git_info",
]


class GitHubGuruAgent:
    """Main agent that handles analysis and querying."""

    def __init__(self) -> None:
        self._analysis: CodebaseAnalysis | None = None
        self._graph = None
        self._embedding_index: CodeEmbeddingIndex | None = None
        self._repo_root: str | None = None
        self._cache: AnalysisCache | None = None

    def analyze(self, source: str, no_embeddings: bool = False) -> CodebaseAnalysis:
        """Run the full analysis pipeline: ingest -> parse -> graph -> chunk -> embed -> cache."""
        # 1. Ingest
        console.print(f"[bold blue]Ingesting repository:[/] {source}")
        repo_root, file_list = ingest_repo(source)
        self._repo_root = repo_root
        self._cache = AnalysisCache(repo_root)

        console.print(f"  Found [green]{len(file_list)}[/] files")

        # 2. Parse each file
        console.print("[bold blue]Parsing files...[/]")
        root = Path(repo_root)
        files = []
        languages: dict[str, int] = {}
        total_lines = 0

        for filepath in file_list:
            try:
                content = (root / filepath).read_text(errors="replace")
            except (OSError, UnicodeDecodeError):
                continue

            fi = parse_file(filepath, content)
            files.append(fi)
            lang = fi.language.value
            languages[lang] = languages.get(lang, 0) + 1
            total_lines += fi.line_count

        repo_name = Path(repo_root).name
        repo_info = RepoInfo(name=repo_name, root_path=repo_root)

        analysis = CodebaseAnalysis(
            repo=repo_info,
            files=files,
            total_files=len(files),
            total_lines=total_lines,
            languages=languages,
        )
        self._analysis = analysis

        # 3. Build dependency graph
        console.print("[bold blue]Building dependency graph...[/]")
        self._graph = build_dependency_graph(analysis)
        graph_summary = self._graph.get_summary()
        console.print(f"  {graph_summary['total_nodes']} nodes, {graph_summary['total_edges']} edges")

        # 4. Chunk and embed
        self._embedding_index = CodeEmbeddingIndex()
        if not no_embeddings:
            console.print("[bold blue]Chunking and embedding code...[/]")
            chunks = chunk_codebase(analysis, repo_root)
            console.print(f"  Created [green]{len(chunks)}[/] chunks")
            self._embedding_index.build(chunks)

        # 5. Cache everything
        console.print("[bold blue]Saving cache...[/]")
        self._cache.save_analysis(analysis)
        self._cache.save_graph(self._graph)
        if self._embedding_index.get_embeddings() is not None and len(self._embedding_index.get_embeddings()) > 0:
            self._cache.save_embeddings(
                self._embedding_index.get_embeddings(),
                self._embedding_index.get_chunks_metadata(),
            )

        # 6. Set shared state for tools
        state.set_state(analysis, self._graph, self._embedding_index, repo_root)

        console.print("[bold green]Analysis complete![/]")
        return analysis

    def load_from_cache(self, repo_path: str) -> bool:
        """Load a previously cached analysis."""
        cache = AnalysisCache(repo_path)
        if not cache.has_cache():
            return False

        analysis = cache.load_analysis()
        graph = cache.load_graph()
        if analysis is None or graph is None:
            return False

        self._analysis = analysis
        self._graph = graph
        self._repo_root = str(Path(repo_path).resolve())
        self._cache = cache

        # Load embeddings
        self._embedding_index = CodeEmbeddingIndex()
        emb_data = cache.load_embeddings()
        if emb_data is not None:
            embeddings, chunks = emb_data
            self._embedding_index.load(embeddings, chunks)

        # Set shared state
        state.set_state(analysis, graph, self._embedding_index, self._repo_root)
        return True

    async def ask(self, question: str) -> str:
        """Ask a question about the analyzed codebase using Claude Agent SDK."""
        from claude_agent_sdk import (
            ClaudeSDKClient,
            ClaudeAgentOptions,
            AssistantMessage,
            TextBlock,
            ResultMessage,
            create_sdk_mcp_server,
        )

        server = create_sdk_mcp_server(
            name="guru",
            version="1.0.0",
            tools=_get_all_tools(),
        )

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"guru": server},
            allowed_tools=TOOL_NAMES,
            max_turns=20,
        )

        full_response = []

        async with ClaudeSDKClient(options=options) as client:
            await client.query(question)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response.append(block.text)

        return "\n".join(full_response) if full_response else "No response generated."

    async def generate_docs(self, output_dir: str, doc_types: list[str] | None = None) -> list[str]:
        """Generate documentation by querying Claude for each doc section."""
        from claude_agent_sdk import (
            ClaudeSDKClient,
            ClaudeAgentOptions,
            AssistantMessage,
            TextBlock,
            create_sdk_mcp_server,
        )
        from github_guru.docs.generator import DOC_PROMPTS

        if doc_types is None:
            doc_types = list(DOC_PROMPTS.keys())

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        generated: list[str] = []

        for doc_type in doc_types:
            if doc_type not in DOC_PROMPTS:
                console.print(f"[yellow]Unknown doc type: {doc_type}[/]")
                continue

            prompt = DOC_PROMPTS[doc_type]
            console.print(f"[bold blue]Generating {doc_type}...[/]")

            # Create a fresh server + client per doc to avoid transport issues
            server = create_sdk_mcp_server(
                name="guru",
                version="1.0.0",
                tools=_get_all_tools(),
            )

            options = ClaudeAgentOptions(
                system_prompt=SYSTEM_PROMPT,
                mcp_servers={"guru": server},
                allowed_tools=TOOL_NAMES,
                max_turns=15,
            )

            result_text: list[str] = []
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                result_text.append(block.text)

            if result_text:
                content = "\n".join(result_text)
                doc_file = out_path / f"{doc_type}.md"
                doc_file.write_text(content)
                generated.append(str(doc_file))
                console.print(f"  [green]Wrote {doc_file}[/]")

        return generated
