# GitHub Guru

**AI-powered GitHub repository analyzer using Claude Agent SDK**

> Version `0.1.0` · Python · MIT License

---

## Overview

GitHub Guru is an intelligent command-line tool that deeply analyzes any Git repository — local or remote — and lets you ask natural-language questions about its codebase. It combines **static analysis** (AST parsing, dependency graphing) with **semantic search** (vector embeddings) and channels everything through Anthropic's Claude via the Claude Agent SDK. The result is an AI agent that truly *understands* your code.

### What It Does

1. **Analyzes** a repository: parses source files into an AST, builds a dependency graph, chunks code, and generates semantic embeddings.
2. **Answers questions** about the codebase using Claude, backed by 7 specialized MCP (Model Context Protocol) tools the agent can invoke autonomously.
3. **Generates documentation** (overview, architecture, file reference, API docs) by having the AI agent explore the analyzed codebase and produce Markdown output.

---

## Technology Stack & Key Dependencies

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.10+ | Core runtime |
| **Build System** | Hatchling | PEP 517 packaging |
| **AI Agent** | `claude-agent-sdk ≥ 0.1.0` | Multi-turn Claude orchestration via MCP tools |
| **CLI Framework** | `typer[all] ≥ 0.12.0` + `rich ≥ 13.0.0` | Terminal UI, commands, styled output |
| **GitHub API** | `PyGithub ≥ 2.0.0` | Repo metadata, cloning, issues, commits |
| **Embeddings** | `sentence-transformers ≥ 3.0.0` (`all-MiniLM-L6-v2`) | Semantic code search |
| **Numerical** | `numpy ≥ 1.24.0` | Cosine similarity, embedding storage |
| **Config** | `pyyaml ≥ 6.0` | YAML configuration parsing |
| **AST Parsing** | Python `ast` (stdlib) | Structural extraction from Python source |

---

## Project Structure

```
Github-Guru/
├── pyproject.toml                      # Package metadata, dependencies, CLI entry point
├── config/
│   └── github_guru.yaml                # Default configuration (model, chunking, embedding params)
└── src/
    └── github_guru/
        ├── __init__.py                  # Package init (version)
        ├── cli.py                       # Typer CLI: analyze, ask, docs commands
        ├── agent.py                     # GitHubGuruAgent — orchestrates the full pipeline
        ├── state.py                     # Shared module-level globals for tool access
        ├── system_prompt.py             # System prompt injected into Claude agent
        │
        ├── analysis/                    # ── Analysis Engine ──
        │   ├── __init__.py
        │   ├── ingestion.py             # Repo ingestion (local + GitHub URL cloning)
        │   ├── ast_parser.py            # Python AST visitor → functions, classes, imports
        │   ├── dependency_graph.py       # Build file/class/function dependency graph
        │   ├── chunker.py               # Structure-aware code chunking for embeddings
        │   └── embeddings.py            # Sentence Transformer embedding index + search
        │
        ├── models/                      # ── Data Models ──
        │   ├── __init__.py
        │   ├── codebase.py              # FileInfo, ClassInfo, FunctionInfo, CodebaseAnalysis
        │   ├── graph.py                 # DependencyGraph, GraphNode, GraphEdge
        │   └── cache.py                 # .github-guru/ cache (JSON + NPZ persistence)
        │
        ├── tools/                       # ── MCP Tools (7 total) ──
        │   ├── __init__.py
        │   ├── list_files.py            # List repo files with glob filtering
        │   ├── read_file.py             # Read file contents with line ranges
        │   ├── search_code.py           # Regex search across files
        │   ├── query_structure.py       # Query AST: overview, classes, functions, imports
        │   ├── query_graph.py           # Query dependency graph: dependents, deps, paths
        │   ├── semantic_search.py       # Natural-language code search via embeddings
        │   └── get_git_info.py          # Git metadata: commits, branches, contributors
        │
        ├── docs/                        # ── Documentation Generator ──
        │   ├── __init__.py
        │   └── generator.py             # Doc type prompts (overview, architecture, files, api)
        │
        └── github/                      # ── GitHub Integration ──
            ├── __init__.py
            └── client.py                # PyGithub wrapper for repo metadata & cloning
```

**30 files · 2,644 lines of code · 19 classes · 119 functions**

---

## Getting Started

### Prerequisites

- **Python 3.10** or newer
- **Git** (for cloning remote repositories)
- An **Anthropic API key** (for the Claude Agent SDK)

### Installation

```bash
# Clone the repository
git clone <repo-url> Github-Guru
cd Github-Guru

# Install in development mode
pip install -e .
```

This registers the `github-guru` CLI command via the `[project.scripts]` entry point.

### Configuration

The default configuration lives at `config/github_guru.yaml`. Key settings include:

| Setting | Default | Description |
|---|---|---|
| `model` | `claude-sonnet-4-5-20250929` | Claude model used for agent queries |
| `max_turns` | `20` | Maximum agent conversation turns |
| `analysis.max_file_size` | `524288` (500 KB) | Skip files larger than this |
| `embeddings.model` | `all-MiniLM-L6-v2` | Sentence Transformer model for semantic search |
| `chunking.max_chunk_lines` | `100` | Maximum lines per code chunk |
| `cache_dir` | `.github-guru` | Cache directory (relative to repo root) |

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | API key for Claude Agent SDK |
| `GITHUB_TOKEN` | No | Optional GitHub token for higher API rate limits |

---

## Usage

GitHub Guru provides three CLI commands:

### 1. `analyze` — Analyze a Repository

```bash
# Analyze a local repository
github-guru analyze /path/to/repo

# Analyze a GitHub repository by URL
github-guru analyze https://github.com/owner/repo

# Skip embedding generation (faster, but disables semantic search)
github-guru analyze /path/to/repo --no-embeddings
```

**What happens under the hood:**
1. **Ingest** — Walks the directory tree (or shallow-clones the URL), filtering out binaries, lock files, and ignored directories.
2. **Parse** — Runs Python's `ast` module on `.py` files to extract classes, functions, imports, decorators, docstrings, and call graphs. Non-Python files get basic metadata.
3. **Graph** — Builds a dependency graph with nodes (files, classes, functions) and edges (imports, contains, inherits).
4. **Chunk** — Splits code into structure-aware chunks: individual functions, classes, module headers, and sliding windows for non-Python files.
5. **Embed** — Generates vector embeddings for all chunks using `all-MiniLM-L6-v2`.
6. **Cache** — Persists everything to `.github-guru/` as `analysis.json`, `graph.json`, `chunks.json`, and `embeddings.npz`.

### 2. `ask` — Ask Questions About the Code

```bash
# Ask about the current directory (must be previously analyzed)
github-guru ask "How does the authentication system work?"

# Specify a different repo
github-guru ask "What are the main entry points?" --repo /path/to/repo
```

This launches a multi-turn Claude agent session with access to all 7 MCP tools. The agent can autonomously read files, search code, query the dependency graph, and use semantic search to answer your question.

### 3. `docs` — Generate Documentation

```bash
# Generate all doc types
github-guru docs /path/to/repo

# Generate specific doc types to a custom output directory
github-guru docs /path/to/repo -o ./my-docs -t overview -t architecture

# Available doc types: overview, architecture, files, api
```

Each document type is generated by giving the Claude agent a specialized prompt and letting it explore the analyzed codebase via the MCP tools.

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────┐
│                    CLI (Typer)                       │
│          analyze  │   ask   │   docs                │
└────────┬──────────┴────┬────┴────────┬──────────────┘
         │               │             │
         ▼               ▼             ▼
┌─────────────────────────────────────────────────────┐
│               GitHubGuruAgent                       │
│   Orchestrates analysis pipeline + Claude sessions  │
└────────┬──────────┬────────────────┬────────────────┘
         │          │                │
         ▼          ▼                ▼
┌──────────────┐ ┌──────────┐ ┌──────────────────────┐
│  Analysis    │ │  Shared  │ │  Claude Agent SDK    │
│  Engine      │ │  State   │ │  (MCP Server)        │
│              │ │(state.py)│ │                      │
│ • ingestion  │ │          │ │  7 MCP Tools:        │
│ • ast_parser │◄┼──────────┼─┤  • list_files        │
│ • dep_graph  │ │          │ │  • read_file         │
│ • chunker    │ │          │ │  • search_code       │
│ • embeddings │ │          │ │  • query_structure   │
└──────────────┘ └──────────┘ │  • query_graph       │
                              │  • semantic_search   │
                              │  • get_git_info      │
                              └──────────────────────┘
```

The **shared state module** (`state.py`) acts as the bridge between the analysis engine and the MCP tools. After the agent runs analysis, it populates module-level globals (`_analysis`, `_graph`, `_embedding_index`, `_repo_root`) that the tools read from when invoked by Claude during `ask` or `docs` sessions.

---

## Supported Languages

While GitHub Guru can analyze repositories in **any language** (basic metadata + sliding-window chunking), it provides **deep structural analysis** (AST parsing, function/class extraction, dependency graphing) for:

- **Python** — Full AST parsing with function signatures, class hierarchies, imports, decorators, docstrings, and call graphs

Language detection covers 15+ languages via file extension mapping: Python, JavaScript, TypeScript, Java, Go, Rust, C/C++, Ruby, Shell, Markdown, YAML, JSON, and TOML.

---

## Cache Format

Analysis results are persisted in a `.github-guru/` directory at the repository root:

| File | Format | Contents |
|---|---|---|
| `analysis.json` | JSON | Full structural analysis (files, classes, functions, imports) |
| `graph.json` | JSON | Dependency graph (nodes + edges) |
| `chunks.json` | JSON | Code chunk metadata (filepath, type, name, line ranges) |
| `embeddings.npz` | NumPy compressed | Vector embeddings for all code chunks |