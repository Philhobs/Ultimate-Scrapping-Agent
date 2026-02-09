# GitHub Guru — File Reference

> Auto-generated file-by-file reference for every source module in the **GitHub Guru** project.
> 
> **Repository:** `Github-Guru`  
> **Total source files:** 27 Python files  
> **Total lines of code:** 2,644  

---

## Table of Contents

- [Package Root](#package-root)
  - [`src/github_guru/__init__.py`](#srcgithub_guru__init__py)
- [Core Modules](#core-modules)
  - [`src/github_guru/agent.py`](#srcgithub_guruagentpy)
  - [`src/github_guru/cli.py`](#srcgithub_guruClipy)
  - [`src/github_guru/state.py`](#srcgithub_gurustatepy)
  - [`src/github_guru/system_prompt.py`](#srcgithub_gurusystem_promptpy)
- [Analysis Engine](#analysis-engine-srcgithub_guruanalysis)
  - [`analysis/ast_parser.py`](#srcgithub_guruanalysisast_parserpy)
  - [`analysis/chunker.py`](#srcgithub_guruanalysischunkerpy)
  - [`analysis/dependency_graph.py`](#srcgithub_guruanalysisdependency_graphpy)
  - [`analysis/embeddings.py`](#srcgithub_guruanalysisembeddingspy)
  - [`analysis/ingestion.py`](#srcgithub_guruanalysisingestionpy)
- [Data Models](#data-models-srcgithub_gurumodels)
  - [`models/codebase.py`](#srcgithub_gurumodelscodebasepy)
  - [`models/graph.py`](#srcgithub_gurumodelsgraphpy)
  - [`models/cache.py`](#srcgithub_gurumodelscachepy)
- [MCP Tools](#mcp-tools-srcgithub_gurutools)
  - [`tools/list_files.py`](#srcgithub_gurutoolslist_filespy)
  - [`tools/read_file.py`](#srcgithub_gurutoolsread_filepy)
  - [`tools/search_code.py`](#srcgithub_gurutoolssearch_codepy)
  - [`tools/query_structure.py`](#srcgithub_gurutoolsquery_structurepy)
  - [`tools/query_graph.py`](#srcgithub_gurutoolsquery_graphpy)
  - [`tools/semantic_search.py`](#srcgithub_gurutoolssemantic_searchpy)
  - [`tools/get_git_info.py`](#srcgithub_gurutoolsget_git_infopy)
- [Documentation Generator](#documentation-generator-srcgithub_gurudocs)
  - [`docs/generator.py`](#srcgithub_gurudocsgeneratorpy)
- [GitHub Client](#github-client-srcgithub_gurugithub)
  - [`github/client.py`](#srcgithub_gurugithubclientpy)

---

## Package Root

### `src/github_guru/__init__.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 4 |
| **Purpose** | Package root. Declares the project docstring and exposes `__version__`. |

- **Key Definitions:** `__version__ = "0.1.0"`
- **Dependencies:** None

---

## Core Modules

### `src/github_guru/agent.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 246 |
| **Purpose** | Central orchestrator that drives the entire analysis pipeline (ingest → parse → graph → chunk → embed → cache) and manages Claude Agent SDK interactions for the `ask` and `docs` commands. |

#### Classes

| Class | Methods |
|-------|---------|
| `GitHubGuruAgent` | `__init__`, `analyze`, `load_from_cache`, `ask`, `generate_docs` |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `_get_all_tools()` | — | Imports and returns all 7 MCP tool functions as a list. |

#### Dependencies

| Import | Source |
|--------|--------|
| `asyncio` | stdlib |
| `Path` | `pathlib` |
| `Any` | `typing` |
| `Console` | `rich.console` |
| `parse_file` | `github_guru.analysis.ast_parser` |
| `chunk_codebase` | `github_guru.analysis.chunker` |
| `build_dependency_graph` | `github_guru.analysis.dependency_graph` |
| `CodeEmbeddingIndex` | `github_guru.analysis.embeddings` |
| `ingest_repo` | `github_guru.analysis.ingestion` |
| `AnalysisCache` | `github_guru.models.cache` |
| `CodebaseAnalysis`, `RepoInfo`, `detect_language` | `github_guru.models.codebase` |
| `SYSTEM_PROMPT` | `github_guru.system_prompt` |
| `state` | `github_guru` |

---

### `src/github_guru/cli.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 110 |
| **Purpose** | CLI interface using **Typer** and **Rich**. Provides the three user-facing commands: `analyze`, `ask`, and `docs`. Entry point for the `github-guru` console script. |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `analyze` | `source`, `no_embeddings` | Analyze a local path or GitHub URL. |
| `ask` | `question`, `repo` | Ask a natural-language question about an analyzed repo. |
| `docs` | `source`, `output`, `doc_types` | Generate documentation for a repository. |
| `main` | — | Typer app entry point. |

#### Dependencies

| Import | Source |
|--------|--------|
| `asyncio` | stdlib |
| `Path` | `pathlib` |
| `typer` | third-party |
| `Console` | `rich.console` |
| `Markdown` | `rich.markdown` |
| `Table` | `rich.table` |

---

### `src/github_guru/state.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 57 |
| **Purpose** | Shared module-level global state that decouples the agent from MCP tool modules, avoiding circular imports. The agent writes state after analysis; tools read from it. |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `set_state` | `analysis`, `graph`, `embedding_index`, `repo_root` | Populate all global state variables at once. |
| `get_analysis` | — | Return the current `CodebaseAnalysis` or raise if unset. |
| `get_graph` | — | Return the current `DependencyGraph` or raise if unset. |
| `get_embedding_index` | — | Return the current `CodeEmbeddingIndex` or raise if unset. |
| `get_repo_root` | — | Return the repo root path or raise if unset. |

#### Dependencies

| Import | Source |
|--------|--------|
| `TYPE_CHECKING` | `typing` |
| `CodeEmbeddingIndex` | `github_guru.analysis.embeddings` (type-check only) |
| `CodebaseAnalysis` | `github_guru.models.codebase` (type-check only) |
| `DependencyGraph` | `github_guru.models.graph` (type-check only) |

---

### `src/github_guru/system_prompt.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 45 |
| **Purpose** | Defines the `SYSTEM_PROMPT` constant — the persona and behavioral instructions injected into the Claude Agent SDK session. Describes available tools, analysis strategy, and documentation generation guidelines. |

- **Key Definitions:** `SYSTEM_PROMPT: str` (multi-line string constant)
- **Dependencies:** None

---

## Analysis Engine (`src/github_guru/analysis/`)

### `src/github_guru/analysis/ast_parser.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 200 |
| **Purpose** | Python AST parser that extracts structural information (classes, functions, imports, parameters, docstrings, call graphs) from source files using the `ast` module. |

#### Classes

| Class | Bases | Methods |
|-------|-------|---------|
| `PythonASTVisitor` | `ast.NodeVisitor` | `__init__`, `visit_Module`, `visit_Import`, `visit_ImportFrom`, `visit_FunctionDef`, `visit_AsyncFunctionDef`, `_extract_function`, `visit_ClassDef` |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `_extract_calls` | `node` | Extract function call names from an AST node. |
| `parse_python_file` | `filepath`, `content` | Parse a single Python file into a `FileInfo` model. |
| `parse_file` | `filepath`, `content` | Language-dispatching entry point (currently routes Python files). |

#### Dependencies

| Import | Source |
|--------|--------|
| `ast` | stdlib |
| `Path` | `pathlib` |
| `ClassInfo`, `FileInfo`, `FunctionInfo`, `ImportInfo`, `Language`, `ParameterInfo`, `detect_language` | `github_guru.models.codebase` |

---

### `src/github_guru/analysis/chunker.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 196 |
| **Purpose** | Structure-aware code chunking for semantic embedding. Splits source files into meaningful chunks (by function/class for Python, sliding-window for others) to create high-quality embedding inputs. |

#### Classes

| Class | Methods | Description |
|-------|---------|-------------|
| `CodeChunk` | `to_embedding_text`, `to_dict`, `from_dict` | Dataclass representing a single embeddable code fragment with metadata (filepath, chunk type, start/end lines, content). |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `chunk_file` | `fi`, `content` | Chunk a single file based on its language. |
| `_chunk_python` | `fi`, `content` | Python-specific chunking using AST-aware boundaries. |
| `_chunk_sliding_window` | `fi`, `content` | Generic sliding-window chunking for non-Python files. |
| `chunk_codebase` | `analysis`, `repo_root` | Chunk all files in a `CodebaseAnalysis` and return a list of `CodeChunk`. |

#### Dependencies

| Import | Source |
|--------|--------|
| `dataclass` | `dataclasses` |
| `Path` | `pathlib` |
| `CodebaseAnalysis`, `FileInfo`, `Language` | `github_guru.models.codebase` |

---

### `src/github_guru/analysis/dependency_graph.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 202 |
| **Purpose** | Builds a dependency graph from `CodebaseAnalysis` data. Creates nodes for files, classes, and functions, then adds edges for import relationships, class inheritance, and containment. |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `_file_node_id` | `filepath` | Generate a canonical node ID for a file. |
| `_class_node_id` | `filepath`, `class_name` | Generate a canonical node ID for a class. |
| `_func_node_id` | `filepath`, `func_name`, `class_name` | Generate a canonical node ID for a function. |
| `_resolve_import_to_file` | `module`, `level`, `source_filepath`, `file_index` | Resolve a Python import statement to its target file path. |
| `_build_file_index` | `analysis` | Build a lookup index mapping module paths to file paths. |
| `build_dependency_graph` | `analysis` | **Main entry point.** Build the full `DependencyGraph` from a `CodebaseAnalysis`. |
| `_add_import_edges` | `graph`, `fi`, `file_index` | Add import-relationship edges for a single file. |
| `_add_inheritance_edge` | `graph`, `cls_id`, `base_name`, `analysis` | Add inheritance edges between classes. |

#### Dependencies

| Import | Source |
|--------|--------|
| `PurePosixPath` | `pathlib` |
| `CodebaseAnalysis`, `FileInfo`, `Language` | `github_guru.models.codebase` |
| `DependencyGraph`, `GraphEdge`, `GraphNode`, `NodeType`, `RelationType` | `github_guru.models.graph` |

---

### `src/github_guru/analysis/embeddings.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 81 |
| **Purpose** | Semantic embedding index using the **sentence-transformers** library (`all-MiniLM-L6-v2` model). Builds a vector index from code chunks and supports cosine-similarity search for natural-language queries. |

#### Classes

| Class | Methods | Description |
|-------|---------|-------------|
| `CodeEmbeddingIndex` | `__init__`, `_load_model`, `build`, `load`, `search`, `get_embeddings`, `get_chunks_metadata` | Manages embedding generation, persistence (via numpy `.npz`), and similarity-based code search. |

#### Dependencies

| Import | Source |
|--------|--------|
| `Any` | `typing` |
| `numpy` (as `np`) | third-party |
| `CodeChunk` | `github_guru.analysis.chunker` |

---

### `src/github_guru/analysis/ingestion.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 101 |
| **Purpose** | Repository ingestion module handling both local directories and remote GitHub URLs. Clones remote repos to a temp directory, walks the file tree, and collects all source files while respecting ignore rules. |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `is_github_url` | `source` | Check if a source string is a GitHub URL. |
| `clone_repo` | `url` | Clone a remote repo to a temporary directory via `git clone`. |
| `_should_ignore_dir` | `name` | Check if a directory name should be skipped (e.g., `.git`, `node_modules`). |
| `_should_ignore_file` | `path` | Check if a file should be skipped (e.g., binary, too large). |
| `collect_files` | `repo_root` | Walk the repo tree and return a list of `(relative_path, content)` tuples. |
| `ingest_repo` | `source` | **Main entry point.** Accept a local path or GitHub URL, return `(repo_root, files)`. |

#### Dependencies

| Import | Source |
|--------|--------|
| `os`, `re`, `subprocess`, `tempfile` | stdlib |
| `Path` | `pathlib` |

---

## Data Models (`src/github_guru/models/`)

### `src/github_guru/models/codebase.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 249 |
| **Purpose** | Core data models for codebase analysis. Defines all dataclasses that represent parsed source code structure, from individual parameters up to the full codebase. Every model supports round-trip serialization via `to_dict` / `from_dict`. |

#### Classes

| Class | Bases | Description |
|-------|-------|-------------|
| `Language` | `str`, `Enum` | Enum of supported programming languages (Python, JavaScript, TypeScript, Java, Go, Rust, C, C++, Ruby, Shell, Markdown, YAML, JSON, TOML, Other). |
| `ParameterInfo` | — | Dataclass for function parameter metadata (name, type annotation, default value). |
| `FunctionInfo` | — | Dataclass for function metadata (name, params, return type, docstring, decorators, line range, calls). |
| `ClassInfo` | — | Dataclass for class metadata (name, bases, methods, docstring, line range). |
| `ImportInfo` | — | Dataclass for import metadata (module, names, alias, relative level). |
| `FileInfo` | — | Dataclass for file-level metadata (path, language, lines, size, classes, functions, imports, docstring). |
| `RepoInfo` | — | Dataclass for repository-level metadata (name, root path, remote URL, default branch, description). |
| `CodebaseAnalysis` | — | Top-level container holding `RepoInfo` and a list of `FileInfo` objects. |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `detect_language` | `filepath` | Map a file extension to a `Language` enum value. |

#### Dependencies

| Import | Source |
|--------|--------|
| `dataclass`, `field` | `dataclasses` |
| `Enum` | `enum` |
| `Any` | `typing` |

---

### `src/github_guru/models/graph.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 155 |
| **Purpose** | Dependency graph data model. Defines the node/edge types and the `DependencyGraph` class which supports dependency queries, path-finding (BFS), and serialization. |

#### Classes

| Class | Bases | Description |
|-------|-------|-------------|
| `RelationType` | `str`, `Enum` | Edge relationship types: `IMPORTS`, `CALLS`, `INHERITS`, `CONTAINS`. |
| `NodeType` | `str`, `Enum` | Node types: `FILE`, `CLASS`, `FUNCTION`, `MODULE`. |
| `GraphNode` | — | Dataclass for a single node (id, type, name, filepath, metadata). |
| `GraphEdge` | — | Dataclass for a directed edge (source, target, relation type, metadata). |
| `DependencyGraph` | — | Graph container with adjacency lists. Methods: `add_node`, `add_edge`, `get_dependents`, `get_dependencies`, `get_edges_for`, `find_path`, `get_summary`, `to_dict`, `from_dict`. |

#### Dependencies

| Import | Source |
|--------|--------|
| `dataclass`, `field` | `dataclasses` |
| `Enum` | `enum` |
| `Any` | `typing` |

---

### `src/github_guru/models/cache.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 77 |
| **Purpose** | Persistence layer for analysis results. Saves and loads `CodebaseAnalysis`, `DependencyGraph`, embedding vectors, and chunk metadata to/from the `.github-guru/` directory in the analyzed repo. |

#### Classes

| Class | Methods | Description |
|-------|---------|-------------|
| `AnalysisCache` | `__init__`, `analysis_path`, `graph_path`, `embeddings_path`, `chunks_path`, `has_cache`, `save_analysis`, `load_analysis`, `save_graph`, `load_graph`, `save_embeddings`, `load_embeddings` | Manages file-based caching of all analysis artifacts. |

#### Cache File Layout

| Property | File |
|----------|------|
| `analysis_path` | `.github-guru/analysis.json` |
| `graph_path` | `.github-guru/graph.json` |
| `embeddings_path` | `.github-guru/embeddings.npz` |
| `chunks_path` | `.github-guru/chunks.json` |

#### Dependencies

| Import | Source |
|--------|--------|
| `json` | stdlib |
| `Path` | `pathlib` |
| `Any` | `typing` |
| `numpy` (as `np`) | third-party |
| `CodebaseAnalysis` | `github_guru.models.codebase` |
| `DependencyGraph` | `github_guru.models.graph` |

---

## MCP Tools (`src/github_guru/tools/`)

Each tool module defines a single MCP tool function decorated with `@tool` from `claude_agent_sdk`. Tools read global state via `github_guru.state` accessors.

---

### `src/github_guru/tools/list_files.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 45 |
| **Purpose** | MCP tool to list files in the analyzed repository. Supports glob-pattern filtering and optional metadata (size, language, line count). |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `list_files` | `args` | List repo files, optionally filtered by glob `pattern`. Returns JSON with file paths and metadata. |

#### Dependencies

| Import | Source |
|--------|--------|
| `fnmatch`, `json` | stdlib |
| `Any` | `typing` |
| `tool` | `claude_agent_sdk` |
| `get_analysis` | `github_guru.state` |

---

### `src/github_guru/tools/read_file.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 63 |
| **Purpose** | MCP tool to read file contents from the analyzed repository. Supports optional line ranges (`start_line`, `end_line`). Returns content with line numbers, truncated at 30K characters. |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `read_file` | `args` | Read a file by `filepath`, optionally sliced by line range. |

#### Dependencies

| Import | Source |
|--------|--------|
| `Path` | `pathlib` |
| `Any` | `typing` |
| `tool` | `claude_agent_sdk` |
| `get_repo_root` | `github_guru.state` |

---

### `src/github_guru/tools/search_code.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 84 |
| **Purpose** | MCP tool for regex-based code search across all repository files. Supports glob-based file filtering and configurable result limits. Returns matching lines with surrounding context. |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `search_code` | `args` | Search for a `pattern` (regex) across files, with optional `file_glob` filter and `max_results` cap. |

#### Dependencies

| Import | Source |
|--------|--------|
| `fnmatch`, `json`, `re` | stdlib |
| `Path` | `pathlib` |
| `Any` | `typing` |
| `tool` | `claude_agent_sdk` |
| `get_analysis`, `get_repo_root` | `github_guru.state` |

---

### `src/github_guru/tools/query_structure.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 156 |
| **Purpose** | MCP tool to query AST-extracted structural data. Supports five query types: `overview`, `classes`, `functions`, `imports`, and `file_summary`. Optional `name_filter` supports wildcard matching. |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `query_structure` | `args` | Dispatch to one of the five sub-queries based on `query_type`. |
| `_overview` | `analysis` | Compute repo-wide statistics (file count, LOC, language breakdown, class/function counts). |
| `_classes` | `analysis`, `name_filter` | List all classes with bases, methods, and docstrings. |
| `_functions` | `analysis`, `name_filter` | List all top-level functions with parameters and return types. |
| `_imports` | `analysis`, `filepath` | List all imports, optionally scoped to a single file. |
| `_file_summary` | `analysis`, `filepath` | Detailed summary of a single file (language, LOC, docstring, classes, functions, imports). |

#### Dependencies

| Import | Source |
|--------|--------|
| `fnmatch`, `json` | stdlib |
| `Any` | `typing` |
| `tool` | `claude_agent_sdk` |
| `get_analysis` | `github_guru.state` |

---

### `src/github_guru/tools/query_graph.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 112 |
| **Purpose** | MCP tool to query the dependency graph. Supports four actions: `dependents`, `dependencies`, `path` (BFS shortest path between two nodes), and `summary`. |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `query_graph` | `args` | Dispatch graph query by `action` and `node_id` (+ optional `target_id` for path). |
| `_resolve_node_id` | `node_id`, `graph` | Fuzzy-match a user-provided node ID against the graph's node IDs. |
| `_error` | `msg` | Return a standardized error response. |

#### Dependencies

| Import | Source |
|--------|--------|
| `json` | stdlib |
| `Any` | `typing` |
| `tool` | `claude_agent_sdk` |
| `get_graph` | `github_guru.state` |

---

### `src/github_guru/tools/semantic_search.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 43 |
| **Purpose** | MCP tool for semantic code search. Accepts a natural-language `query` and returns the top-k most similar code chunks ranked by cosine similarity against the embedding index. |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `semantic_search` | `args` | Search code by meaning using the `CodeEmbeddingIndex`. |

#### Dependencies

| Import | Source |
|--------|--------|
| `json` | stdlib |
| `Any` | `typing` |
| `tool` | `claude_agent_sdk` |
| `get_embedding_index` | `github_guru.state` |

---

### `src/github_guru/tools/get_git_info.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 147 |
| **Purpose** | MCP tool for retrieving git metadata via subprocess calls. Supports four info types: `commits`, `contributors`, `branches`, and `file_history`. |

#### Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `get_git_info` | `args` | Dispatch git query by `info_type`. |
| `_run_git` | `repo_root`, `args` | Execute a git command and return stdout. |
| `_get_commits` | `repo_root`, `limit`, `filepath` | Retrieve recent commits (optionally filtered by file). |
| `_get_contributors` | `repo_root`, `limit` | Retrieve top contributors by commit count. |
| `_get_branches` | `repo_root` | List all branches with current branch marked. |
| `_get_file_history` | `repo_root`, `filepath`, `limit` | Retrieve commit history for a specific file. |
| `_error` | `msg` | Return a standardized error response. |

#### Dependencies

| Import | Source |
|--------|--------|
| `json`, `subprocess` | stdlib |
| `Any` | `typing` |
| `tool` | `claude_agent_sdk` |
| `get_repo_root` | `github_guru.state` |

---

## Documentation Generator (`src/github_guru/docs/`)

### `src/github_guru/docs/generator.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 52 |
| **Purpose** | Defines documentation generation prompt templates. Contains the `DOC_PROMPTS` dictionary mapping doc types (`overview`, `architecture`, `files`, `api`) to detailed prompt strings that instruct the agent on what to generate. |

#### Key Definitions

| Name | Type | Description |
|------|------|-------------|
| `DOC_PROMPTS` | `dict[str, str]` | Maps four doc types to their generation prompts: `overview`, `architecture`, `files`, `api`. |

#### Dependencies

| Import | Source |
|--------|--------|
| *(none beyond `__future__.annotations`)* | — |

---

## GitHub Client (`src/github_guru/github/`)

### `src/github_guru/github/client.py`

| Attribute | Value |
|-----------|-------|
| **Lines** | 81 |
| **Purpose** | GitHub API client wrapping **PyGithub**. Provides authenticated access to repository metadata, recent commits, issues, and clone operations. |

#### Classes

| Class | Methods | Description |
|-------|---------|-------------|
| `GitHubClient` | `__init__`, `get_repo_metadata`, `get_recent_commits`, `get_issues`, `clone_repo` | Wraps PyGithub's `Github` object. Authenticates via `GITHUB_TOKEN` environment variable. |

#### Dependencies

| Import | Source |
|--------|--------|
| `os`, `subprocess`, `tempfile` | stdlib |
| `Any` | `typing` |
| `Auth`, `Github` | `github` (PyGithub) |

---

## Package `__init__.py` Files (Minimal)

The following init files simply re-export or declare sub-packages:

| File | Lines | Content |
|------|-------|---------|
| `src/github_guru/analysis/__init__.py` | 2 | Package marker |
| `src/github_guru/docs/__init__.py` | 2 | Package marker |
| `src/github_guru/github/__init__.py` | 2 | Package marker |
| `src/github_guru/models/__init__.py` | 2 | Package marker |
| `src/github_guru/tools/__init__.py` | 2 | Package marker |