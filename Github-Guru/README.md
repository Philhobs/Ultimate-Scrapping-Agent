# GitHub Guru

AI-powered GitHub repository analyzer using the Claude Agent SDK. Parses codebases via AST analysis, builds dependency graphs, computes semantic embeddings, and exposes everything to Claude through 7 custom MCP tools — so you can ask natural-language questions about any repo.

## Features

- **Analyze** any repository (local path or GitHub URL): AST parsing, dependency graph, semantic embeddings
- **Ask** natural-language questions about a codebase — Claude autonomously uses 7 tools to find answers
- **Generate docs** — overview, architecture, file reference, and API docs — all AI-generated from the analysis

## Architecture

```
CLI (Typer + Rich)  →  Agent (Claude Agent SDK)  →  Analysis Engine
                              ↕
                     7 Custom MCP Tools
```

| Layer | Components |
|---|---|
| **CLI** | `cli.py` — Typer app with `analyze`, `ask`, `docs` commands |
| **Agent** | `agent.py` — Orchestrates Claude via `ClaudeSDKClient` + MCP tools |
| **Analysis** | AST parser, dependency graph builder, structure-aware chunker, embedding index |
| **Tools** | `list_files`, `read_file`, `search_code`, `query_structure`, `query_graph`, `semantic_search`, `get_git_info` |
| **State** | `state.py` — Module-level globals connecting tools to analysis data |

## Installation

```bash
pip install -e .
```

Requires Python 3.10+ and an `ANTHROPIC_API_KEY` environment variable for the `ask` and `docs` commands.

## Usage

### Analyze a repository

```bash
# Local repository
github-guru analyze .

# GitHub URL
github-guru analyze https://github.com/pallets/flask

# Skip embedding generation (faster, but disables semantic search)
github-guru analyze . --no-embeddings
```

This runs the full pipeline: ingest → parse → graph → chunk → embed → cache. Results are saved to `.github-guru/` in the repo root.

### Ask questions

```bash
github-guru ask "How does authentication work?" --repo .
github-guru ask "What classes inherit from BaseModel?" --repo ./my-project
```

The agent loads the cached analysis and uses all 7 MCP tools to explore the codebase and answer your question.

### Generate documentation

```bash
# Generate all doc types
github-guru docs . -o ./docs

# Generate specific types
github-guru docs . -o ./docs -t overview -t architecture
```

Doc types: `overview`, `architecture`, `files`, `api`

## MCP Tools

| Tool | Description |
|---|---|
| `list_files` | List files with glob filtering and optional metadata |
| `read_file` | Read file contents with optional line ranges |
| `search_code` | Regex search across files with context |
| `query_structure` | Query AST data: overview, classes, functions, imports, file summaries |
| `query_graph` | Query dependency graph: dependents, dependencies, paths, summary |
| `semantic_search` | Natural language code search via embeddings |
| `get_git_info` | Git metadata: commits, contributors, branches, file history |

## Analysis Pipeline

1. **Ingest** — Discover files (local or `git clone --depth 1` for URLs), filter by extension/size
2. **Parse** — Python AST visitor extracts classes, functions, imports, docstrings, calls; basic metadata for other languages
3. **Graph** — Build dependency graph with nodes (file/class/function) and edges (imports/calls/inherits/contains)
4. **Chunk** — Structure-aware splitting: each function/class = 1 chunk; sliding window for non-Python files
5. **Embed** — `all-MiniLM-L6-v2` via sentence-transformers; cosine similarity search via numpy

## Project Structure

```
src/github_guru/
├── cli.py                  # Typer CLI: analyze, ask, docs
├── agent.py                # GitHubGuruAgent orchestrator
├── state.py                # Shared state for MCP tools
├── system_prompt.py        # Agent system prompt
├── models/
│   ├── codebase.py         # FileInfo, FunctionInfo, ClassInfo, etc.
│   ├── graph.py            # DependencyGraph, GraphNode, GraphEdge
│   └── cache.py            # JSON + .npz cache in .github-guru/
├── analysis/
│   ├── ingestion.py        # Local + GitHub repo ingestion
│   ├── ast_parser.py       # Python AST visitor
│   ├── dependency_graph.py # Graph builder
│   ├── chunker.py          # Structure-aware code chunking
│   └── embeddings.py       # Sentence Transformers index
├── tools/                  # 7 MCP tools (one per file)
├── github/
│   └── client.py           # PyGithub wrapper
└── docs/
    └── generator.py        # Doc generation prompts
```

## Dependencies

- `claude-agent-sdk` — Claude Agent SDK for MCP tool integration
- `typer` + `rich` — CLI framework with styled output
- `sentence-transformers` — Semantic embeddings (`all-MiniLM-L6-v2`)
- `numpy` — Cosine similarity search
- `PyGithub` — GitHub API access
- `pyyaml` — Configuration

## License

MIT
