# GitHub Guru — Architecture Document

## 1. System Architecture Overview

GitHub Guru is an AI-powered repository analysis tool built in Python (2,644 lines across 30 files). It combines **static code analysis** (AST parsing, dependency graphing) with **semantic understanding** (vector embeddings) and exposes both through a **Claude AI agent** powered by the Claude Agent SDK's MCP (Model Context Protocol) tool system.

The system follows a **pipeline architecture** for analysis and a **tool-mediated agent architecture** for querying:

1. **Analysis Phase** — A deterministic pipeline ingests a repository, parses its structure, builds a dependency graph, chunks the code, and computes semantic embeddings. Results are cached to disk.
2. **Query Phase** — A Claude LLM agent is given access to 7 MCP tools that read from the cached analysis. The agent autonomously decides which tools to invoke to answer user questions or generate documentation.

### Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| CLI Framework | Typer + Rich |
| AI Agent | Claude Agent SDK (`ClaudeSDKClient`, MCP) |
| AST Parsing | Python `ast` module |
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2) |
| Vector Math | NumPy (cosine similarity) |
| GitHub API | PyGithub |
| Build System | Hatchling |
| Config | YAML (`config/github_guru.yaml`) |

---

## 2. Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                 │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     cli.py (Typer CLI)                              │    │
│  │   ┌──────────┐    ┌──────────┐    ┌──────────┐                     │    │
│  │   │ analyze  │    │   ask    │    │   docs   │                     │    │
│  │   └────┬─────┘    └────┬─────┘    └────┬─────┘                     │    │
│  └────────┼───────────────┼───────────────┼───────────────────────────┘    │
│           │               │               │                                 │
└───────────┼───────────────┼───────────────┼─────────────────────────────────┘
            │               │               │
            ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                 │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    agent.py (GitHubGuruAgent)                       │    │
│  │                                                                     │    │
│  │   analyze()          ask()              generate_docs()             │    │
│  │   ┌──────────┐      ┌──────────────┐   ┌──────────────┐           │    │
│  │   │ Pipeline │      │ Claude Agent │   │ Claude Agent │           │    │
│  │   │ Runner   │      │ SDK Client   │   │ SDK Client   │           │    │
│  │   └────┬─────┘      └──────┬───────┘   └──────┬───────┘           │    │
│  └────────┼───────────────────┼───────────────────┼───────────────────┘    │
│           │                   │                   │                         │
└───────────┼───────────────────┼───────────────────┼─────────────────────────┘
            │                   │                   │
     ┌──────▼──────┐    ┌──────▼───────────────────▼──────┐
     │             │    │                                  │
     ▼             │    ▼                                  │
┌─────────────┐    │  ┌──────────────────────────────────┐ │
│  ANALYSIS   │    │  │     MCP TOOL LAYER               │ │
│  ENGINE     │    │  │                                  │ │
│             │    │  │  ┌───────────┐ ┌──────────────┐  │ │
│ ingestion   │    │  │  │list_files │ │ read_file    │  │ │
│ ast_parser  │    │  │  ├───────────┤ ├──────────────┤  │ │
│ dep_graph   │    │  │  │search_code│ │query_structure│ │ │
│ chunker     │    │  │  ├───────────┤ ├──────────────┤  │ │
│ embeddings  │    │  │  │query_graph│ │semantic_search│ │ │
│             │    │  │  ├───────────┤ └──────────────┘  │ │
└──────┬──────┘    │  │  │get_git_info│                  │ │
       │           │  │  └───────────┘                   │ │
       │           │  └──────────────┬───────────────────┘ │
       │           │                 │                      │
       ▼           ▼                 ▼                      │
┌──────────────────────────────────────────────┐           │
│              SHARED STATE (state.py)          │◄──────────┘
│                                              │
│  _analysis: CodebaseAnalysis                 │
│  _graph:    DependencyGraph                  │
│  _embedding_index: CodeEmbeddingIndex        │
│  _repo_root: str                             │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│           DATA / MODELS LAYER                │
│                                              │
│  models/codebase.py    models/graph.py       │
│  ┌──────────────┐      ┌────────────────┐    │
│  │CodebaseAnalysis│    │DependencyGraph │    │
│  │FileInfo       │    │GraphNode       │    │
│  │FunctionInfo   │    │GraphEdge       │    │
│  │ClassInfo      │    │RelationType    │    │
│  │ImportInfo     │    │NodeType        │    │
│  │ParameterInfo  │    └────────────────┘    │
│  │RepoInfo       │                          │
│  │Language       │    models/cache.py        │
│  └──────────────┘     ┌────────────────┐    │
│                       │AnalysisCache   │    │
│                       └───────┬────────┘    │
└───────────────────────────────┼──────────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │   .github-guru/ cache  │
                   │                        │
                   │  analysis.json         │
                   │  graph.json            │
                   │  embeddings.npz        │
                   │  chunks.json           │
                   └────────────────────────┘
```

---

## 3. Data Flow Description

### 3.1 Analysis Pipeline (`github-guru analyze`)

The analysis pipeline is a **six-stage sequential process** orchestrated by `GitHubGuruAgent.analyze()` (`src/github_guru/agent.py`, lines 57–126):

```
  Source (path/URL)
        │
        ▼
  ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
  │ 1. INGEST   │────▶│ 2. PARSE     │────▶│ 3. GRAPH BUILD  │
  │             │     │              │     │                 │
  │ clone/walk  │     │ AST visitor  │     │ nodes + edges   │
  │ filter files│     │ per file     │     │ imports/inherit │
  └─────────────┘     └──────────────┘     └────────┬────────┘
                                                     │
                                                     ▼
  ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
  │ 6. CACHE    │◀────│ 5. EMBED     │◀────│ 4. CHUNK        │
  │             │     │              │     │                 │
  │ .github-guru│     │ MiniLM-L6-v2 │     │ struct-aware    │
  │ JSON + NPZ  │     │ encode()     │     │ split           │
  └──────┬──────┘     └──────────────┘     └─────────────────┘
         │
         ▼
  shared state (state.py)
```

**Stage details:**

| Stage | Module | Input | Output | Description |
|-------|--------|-------|--------|-------------|
| 1. Ingest | `analysis/ingestion.py` | Local path or GitHub URL | `(repo_root, file_list)` | Clones remote repos (shallow `--depth 1`), walks directory tree, filters by extension/size/ignored dirs |
| 2. Parse | `analysis/ast_parser.py` | File paths + content | `list[FileInfo]` → `CodebaseAnalysis` | Full AST parsing for Python via `PythonASTVisitor` (extracts functions, classes, imports, parameters, decorators, docstrings, call sites); basic metadata for other languages |
| 3. Graph | `analysis/dependency_graph.py` | `CodebaseAnalysis` | `DependencyGraph` | Creates file/class/function nodes; adds `CONTAINS`, `IMPORTS`, and `INHERITS` edges; resolves imports to repo-internal files via a dotted-module index |
| 4. Chunk | `analysis/chunker.py` | `CodebaseAnalysis` + file content | `list[CodeChunk]` | Python files: structure-aware chunks (per function, per class, module header); Non-Python: sliding window (60 lines, 10 overlap); large classes split into method-level chunks |
| 5. Embed | `analysis/embeddings.py` | `list[CodeChunk]` | `np.ndarray` | Encodes chunk text (`type + name + path + content`) via `all-MiniLM-L6-v2` Sentence Transformer |
| 6. Cache | `models/cache.py` | All artifacts | `.github-guru/` directory | `analysis.json`, `graph.json`, `chunks.json` (JSON), `embeddings.npz` (compressed NumPy) |

### 3.2 Query Flow (`github-guru ask`)

```
  User Question
        │
        ▼
  ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
  │ Load Cache   │────▶│ Create MCP Server│────▶│ Claude Agent │
  │ (or analyze) │     │ + SDK Client     │     │ Multi-turn   │
  └──────────────┘     └──────────────────┘     └──────┬───────┘
                                                        │
                                            ┌───────────┼───────────┐
                                            │     Tool Calls        │
                                            ▼           ▼           ▼
                                     ┌──────────┐ ┌──────────┐ ┌──────────┐
                                     │query_    │ │semantic_ │ │read_file │
                                     │structure │ │search    │ │          │
                                     └──────────┘ └──────────┘ └──────────┘
                                            │           │           │
                                            ▼           ▼           ▼
                                     ┌──────────────────────────────────┐
                                     │        state.py globals         │
                                     │  (analysis, graph, embeddings)  │
                                     └──────────────────────────────────┘
```

The agent creates a fresh `ClaudeSDKClient` per query with an `create_sdk_mcp_server` in-process MCP server exposing all 7 tools. Claude autonomously decides which tools to call across up to 20 turns to formulate a complete answer.

### 3.3 Documentation Generation (`github-guru docs`)

Same architecture as `ask`, but iterates over predefined prompts from `docs/generator.py` (`DOC_PROMPTS` dictionary), creating a **fresh MCP server + client per document type** to avoid transport issues. Supports 4 document types: `overview`, `architecture`, `files`, `api`.

---

## 4. Key Design Patterns

### 4.1 Pipeline Pattern
The analysis phase (`agent.py:57–126`) implements a classic **pipeline** where each stage transforms data sequentially: `ingest → parse → graph → chunk → embed → cache`. Each stage is a pure function in its own module, making stages independently testable and replaceable.

### 4.2 Mediator Pattern (Global Shared State)
`state.py` acts as a **mediator** between the agent and the MCP tools. Module-level globals (`_analysis`, `_graph`, `_embedding_index`, `_repo_root`) are written by the agent after analysis and read by tool functions. This deliberately avoids circular imports between `agent.py` and the tool modules, as noted in the module docstring (line 1–5).

### 4.3 Visitor Pattern
`PythonASTVisitor` (`analysis/ast_parser.py:19–138`) extends `ast.NodeVisitor` to walk Python ASTs, implementing `visit_Module`, `visit_Import`, `visit_ImportFrom`, `visit_FunctionDef`, `visit_AsyncFunctionDef`, and `visit_ClassDef` hooks — a textbook application of the **Visitor** pattern.

### 4.4 Strategy Pattern (Chunking)
The chunker (`analysis/chunker.py:44–48`) uses a **strategy** selection based on language:
- Python files → `_chunk_python()` (structure-aware, AST-based boundaries)
- All other files → `_chunk_sliding_window()` (fixed window with overlap)

### 4.5 Tool-Mediated Agent Architecture (MCP)
The 7 MCP tools follow a uniform contract: each is an `async` function decorated with `@tool(name, description, params)` from `claude_agent_sdk`. Each returns `{"content": [{"type": "text", "text": ...}]}`. The Claude agent autonomously selects and sequences tool calls — a **tool-use agent** pattern where the LLM acts as the controller.

### 4.6 Data Transfer Objects (Dataclasses)
All domain models (`models/codebase.py`, `models/graph.py`) are Python `@dataclass` types with explicit `to_dict()` / `from_dict()` serialization — acting as **DTOs** between the analysis pipeline, cache layer, and tool layer.

### 4.7 Lazy Loading
The embedding model (`analysis/embeddings.py:22–26`) uses **lazy initialization**: `SentenceTransformer` is only imported and instantiated on first use via `_load_model()`, avoiding heavy startup cost when embeddings aren't needed (e.g., `--no-embeddings` flag).

---

## 5. Module Responsibilities

### 5.1 Entry Points & Orchestration

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `cli.py` | 110 | Typer CLI with 3 commands (`analyze`, `ask`, `docs`). Handles argument parsing, delegates to `GitHubGuruAgent`, renders Rich output (tables, Markdown). |
| `agent.py` | 246 | Central orchestrator. `GitHubGuruAgent` class owns the analysis pipeline, cache loading, and Claude Agent SDK session management. Creates MCP servers and clients for AI interactions. |
| `state.py` | 57 | Module-level global state store. 4 globals + getter/setter functions. Bridge between agent (writer) and tools (readers). |
| `system_prompt.py` | 45 | Contains the `SYSTEM_PROMPT` constant — the instruction text given to the Claude agent describing available tools and analysis strategy. |

### 5.2 Analysis Engine (`analysis/`)

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `ingestion.py` | 101 | Repository ingestion. Detects GitHub URLs vs local paths, shallow-clones remote repos, walks directory tree filtering by ignore lists (dirs, extensions, file size ≤ 500KB). |
| `ast_parser.py` | 200 | AST parsing. `PythonASTVisitor` extracts full structural info from Python files (functions, classes, methods, imports, parameters, decorators, docstrings, call sites). Non-Python files get basic metadata only. |
| `dependency_graph.py` | 202 | Graph construction. Builds `DependencyGraph` from analysis: file/class/function nodes with `CONTAINS`, `IMPORTS`, and `INHERITS` edges. Resolves imports to repo files via a dotted-module path index. |
| `chunker.py` | 196 | Code chunking for embedding. Python: structure-aware splitting by function/class/module-header (large classes split into methods). Non-Python: sliding window (60 lines, 10 overlap). Max 100 lines per chunk. |
| `embeddings.py` | 81 | Semantic embedding index. Encodes `CodeChunk` texts via `all-MiniLM-L6-v2`, stores as NumPy array, supports cosine-similarity search. |

### 5.3 Data Models (`models/`)

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `codebase.py` | 249 | Core domain model. Defines `Language` enum, `ParameterInfo`, `FunctionInfo`, `ClassInfo`, `ImportInfo`, `FileInfo`, `RepoInfo`, `CodebaseAnalysis` — all as serializable dataclasses. Also provides `detect_language()` via extension mapping. |
| `graph.py` | 155 | Graph domain model. `NodeType`/`RelationType` enums, `GraphNode`, `GraphEdge`, and `DependencyGraph` with traversal operations (dependents, dependencies, BFS path finding, summary). |
| `cache.py` | 77 | Persistence layer. `AnalysisCache` reads/writes analysis, graph (JSON), and embeddings (NPZ + JSON) to `.github-guru/` directory. |

### 5.4 MCP Tools (`tools/`)

| Module | Lines | Tool | Data Source |
|--------|-------|------|-------------|
| `list_files.py` | 45 | `list_files` | `state.get_analysis()` → file list with glob filtering and optional metadata |
| `read_file.py` | 63 | `read_file` | Filesystem via `state.get_repo_root()` → file content with line ranges |
| `search_code.py` | 84 | `search_code` | Filesystem → regex search across files with context lines and glob filtering |
| `query_structure.py` | 156 | `query_structure` | `state.get_analysis()` → overview, classes, functions, imports, file_summary |
| `query_graph.py` | 112 | `query_graph` | `state.get_graph()` → dependents, dependencies, path, summary |
| `semantic_search.py` | 43 | `semantic_search` | `state.get_embedding_index()` → cosine similarity search over code chunks |
| `get_git_info.py` | 147 | `get_git_info` | Git subprocess → commits, contributors, branches, file history |

### 5.5 Supporting Modules

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `docs/generator.py` | 52 | Documentation prompt templates. `DOC_PROMPTS` dict maps doc types (`overview`, `architecture`, `files`, `api`) to detailed generation prompts. |
| `github/client.py` | 81 | GitHub API wrapper. `GitHubClient` uses PyGithub for repo metadata, commits, issues, and `git clone` via subprocess. |
| `config/github_guru.yaml` | 65 | Configuration file defining model, analysis settings, chunking parameters, and embedding model name. |

---

## 6. Inter-Module Dependencies

### 6.1 Dependency Graph Summary

The codebase dependency graph contains **168 nodes** and **138 edges** across 3 node types:

| Node Type | Count |
|-----------|-------|
| File | 30 |
| Class | 19 |
| Function | 119 |

### 6.2 Core Dependency Map

```
                    ┌──────────────┐
                    │   cli.py     │
                    └──────┬───────┘
                           │ imports
                           ▼
                    ┌──────────────┐
                    │  agent.py    │ ◄── Central hub
                    └──┬──┬──┬──┬─┘
                       │  │  │  │
          ┌────────────┘  │  │  └──────────────┐
          ▼               ▼  ▼                  ▼
  ┌──────────────┐  ┌─────────────┐    ┌──────────────┐
  │ingestion.py  │  │ast_parser.py│    │embeddings.py │
  └──────────────┘  └──────┬──────┘    └──────┬───────┘
                           │                  │
                           ▼                  ▼
                    ┌──────────────┐    ┌──────────────┐
                    │ codebase.py  │    │ chunker.py   │
                    │ (models)     │◄───┘              │
                    └──────┬───────┘    └──────────────┘
                           │
                           │ ◄── also imported by:
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐
  │  graph.py    │  │  cache.py   │  │dependency_   │
  │  (models)    │◄─┤  (models)   │  │graph.py      │
  └──────────────┘  └─────────────┘  └──────────────┘

  ┌──────────────────────────────────────────────────┐
  │               tools/*.py (7 modules)             │
  │  All import from state.py (never from agent.py)  │
  └──────────────────────┬───────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  state.py    │ ◄── Written by agent.py
                  └──────────────┘     Read by tools/*.py
```

### 6.3 Key Dependency Chains

**agent.py** is the most connected module, importing from 6 internal modules:
- `analysis.ingestion` → `ingest_repo`
- `analysis.ast_parser` → `parse_file`
- `analysis.dependency_graph` → `build_dependency_graph`
- `analysis.chunker` → `chunk_codebase`
- `analysis.embeddings` → `CodeEmbeddingIndex`
- `models.cache` → `AnalysisCache`
- `models.codebase` → `CodebaseAnalysis`, `RepoInfo`, `detect_language`
- `state` → `set_state`
- `system_prompt` → `SYSTEM_PROMPT`

**models/codebase.py** is the most depended-upon module — imported by:
- `analysis/ast_parser.py` (7 symbols: `ClassInfo`, `FileInfo`, `FunctionInfo`, `ImportInfo`, `Language`, `ParameterInfo`, `detect_language`)
- `analysis/chunker.py` (3 symbols: `CodebaseAnalysis`, `FileInfo`, `Language`)
- `analysis/dependency_graph.py` (3 symbols: `CodebaseAnalysis`, `FileInfo`, `Language`)
- `models/cache.py` (1 symbol: `CodebaseAnalysis`)
- `state.py` (TYPE_CHECKING only)
- `agent.py` (3 symbols)

**Tool isolation**: All 7 tool modules import exclusively from `state.py` and `claude_agent_sdk` — never from `agent.py` or the analysis modules directly. This prevents circular dependencies since `agent.py` lazy-imports the tools via `_get_all_tools()`.

### 6.4 Circular Dependency Avoidance

The architecture carefully avoids circular imports through two mechanisms:

1. **`state.py` as mediator**: `agent.py` writes to `state.py` globals; `tools/*.py` reads from them. Neither side imports the other.
2. **`TYPE_CHECKING` guards**: `state.py` uses `from typing import TYPE_CHECKING` to import type annotations only at static analysis time (line 9–14), avoiding runtime circular imports.
3. **Lazy tool imports**: `_get_all_tools()` in `agent.py` (line 24–33) uses local imports inside the function body, deferring tool module loading until the MCP server is actually created.