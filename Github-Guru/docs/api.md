# GitHub Guru — API Reference

> **Package:** `github_guru`
> **Source:** `src/github_guru/`
> **Python:** ≥ 3.10

---

## Table of Contents

- [1. Agent — `github_guru.agent`](#1-agent--github_guruagent)
  - [`GitHubGuruAgent`](#githubguruagent)
- [2. Data Models — `github_guru.models`](#2-data-models--github_gurumodels)
  - [`Language`](#language)
  - [`ParameterInfo`](#parameterinfo)
  - [`FunctionInfo`](#functioninfo)
  - [`ClassInfo`](#classinfo)
  - [`ImportInfo`](#importinfo)
  - [`FileInfo`](#fileinfo)
  - [`RepoInfo`](#repoinfo)
  - [`CodebaseAnalysis`](#codebaseanalysis)
- [3. Graph Models — `github_guru.models.graph`](#3-graph-models--github_gurumodelsgraph)
  - [`RelationType`](#relationtype)
  - [`NodeType`](#nodetype)
  - [`GraphNode`](#graphnode)
  - [`GraphEdge`](#graphedge)
  - [`DependencyGraph`](#dependencygraph)
- [4. Cache — `github_guru.models.cache`](#4-cache--github_gurumodelscache)
  - [`AnalysisCache`](#analysiscache)
- [5. Analysis Engine — `github_guru.analysis`](#5-analysis-engine--github_guruanalysis)
  - [Ingestion — `analysis.ingestion`](#ingestion--analysisingestion)
  - [AST Parser — `analysis.ast_parser`](#ast-parser--analysisast_parser)
  - [Chunker — `analysis.chunker`](#chunker--analysischunker)
  - [Embeddings — `analysis.embeddings`](#embeddings--analysisembeddings)
  - [Dependency Graph Builder — `analysis.dependency_graph`](#dependency-graph-builder--analysisdependency_graph)
- [6. GitHub Client — `github_guru.github.client`](#6-github-client--github_gurugithubclient)
  - [`GitHubClient`](#githubclient)
- [7. MCP Tools — `github_guru.tools`](#7-mcp-tools--github_gurutools)
  - [`list_files`](#list_files)
  - [`read_file`](#read_file)
  - [`search_code`](#search_code)
  - [`query_structure`](#query_structure)
  - [`query_graph`](#query_graph-tool)
  - [`semantic_search`](#semantic_search)
  - [`get_git_info`](#get_git_info)
- [8. State Management — `github_guru.state`](#8-state-management--github_gurustate)
- [9. CLI — `github_guru.cli`](#9-cli--github_gurucli)

---

## 1. Agent — `github_guru.agent`

**File:** `src/github_guru/agent.py`

### `GitHubGuruAgent`

```python
class GitHubGuruAgent:
    """Main agent that handles analysis and querying."""
```

The central orchestrator. Manages the full pipeline — ingestion, parsing, graph construction, embedding, caching — and exposes AI-powered querying via the Claude Agent SDK.

#### `__init__`

```python
def __init__(self) -> None
```

Initializes an empty agent. All internal state is `None` until `analyze()` or `load_from_cache()` is called.

**Example:**

```python
from github_guru.agent import GitHubGuruAgent

agent = GitHubGuruAgent()
```

---

#### `analyze`

```python
def analyze(self, source: str, no_embeddings: bool = False) -> CodebaseAnalysis
```

Run the full analysis pipeline: **ingest → parse → graph → chunk → embed → cache**.

| Parameter | Type | Description |
|---|---|---|
| `source` | `str` | Local filesystem path or GitHub URL (e.g. `https://github.com/owner/repo`) |
| `no_embeddings` | `bool` | If `True`, skip the embedding generation step. Default `False`. |

**Returns:** [`CodebaseAnalysis`](#codebaseanalysis) — the complete structural analysis result.

**Example:**

```python
agent = GitHubGuruAgent()

# Analyze a local repo
analysis = agent.analyze("/path/to/my-project")

# Analyze from GitHub, skip embeddings for speed
analysis = agent.analyze("https://github.com/owner/repo", no_embeddings=True)

print(f"Files: {analysis.total_files}, Lines: {analysis.total_lines}")
```

**Related:** [`ingest_repo`](#ingest_repo), [`parse_file`](#parse_file), [`build_dependency_graph`](#build_dependency_graph), [`chunk_codebase`](#chunk_codebase), [`CodeEmbeddingIndex.build`](#build)

---

#### `load_from_cache`

```python
def load_from_cache(self, repo_path: str) -> bool
```

Load a previously cached analysis from the `.github-guru/` directory.

| Parameter | Type | Description |
|---|---|---|
| `repo_path` | `str` | Absolute or relative path to the repository root. |

**Returns:** `bool` — `True` if cache was found and loaded successfully, `False` otherwise.

**Example:**

```python
agent = GitHubGuruAgent()
if not agent.load_from_cache("/path/to/my-project"):
    agent.analyze("/path/to/my-project")
```

**Related:** [`AnalysisCache`](#analysiscache)

---

#### `ask`

```python
async def ask(self, question: str) -> str
```

Ask a natural-language question about the analyzed codebase. Uses the Claude Agent SDK with all 7 MCP tools.

| Parameter | Type | Description |
|---|---|---|
| `question` | `str` | Natural language question about the codebase. |

**Returns:** `str` — The AI-generated answer.

**Example:**

```python
import asyncio

agent = GitHubGuruAgent()
agent.load_from_cache(".")

answer = asyncio.run(agent.ask("How does the dependency graph get built?"))
print(answer)
```

**Related:** [`set_state`](#set_state), all [MCP Tools](#7-mcp-tools--github_gurutools)

---

#### `generate_docs`

```python
async def generate_docs(
    self,
    output_dir: str,
    doc_types: list[str] | None = None,
) -> list[str]
```

Generate documentation by querying Claude for each doc section. Each document type is generated in a fresh Claude session.

| Parameter | Type | Description |
|---|---|---|
| `output_dir` | `str` | Directory where `.md` files will be written. Created if missing. |
| `doc_types` | `list[str] \| None` | Subset of doc types to generate (e.g. `["overview", "api"]`). `None` generates all. |

**Returns:** `list[str]` — List of file paths written.

**Example:**

```python
import asyncio

agent = GitHubGuruAgent()
agent.analyze(".")

files = asyncio.run(agent.generate_docs("./docs", doc_types=["overview", "architecture"]))
for f in files:
    print(f"Generated: {f}")
```

---

## 2. Data Models — `github_guru.models`

**File:** `src/github_guru/models/codebase.py`

All data models are `@dataclass` classes with `to_dict()` / `from_dict()` serialization.

---

### `Language`

```python
class Language(str, Enum)
```

Supported programming languages detected via file extension.

| Member | Value |
|---|---|
| `PYTHON` | `"python"` |
| `JAVASCRIPT` | `"javascript"` |
| `TYPESCRIPT` | `"typescript"` |
| `JAVA` | `"java"` |
| `GO` | `"go"` |
| `RUST` | `"rust"` |
| `C` | `"c"` |
| `CPP` | `"cpp"` |
| `RUBY` | `"ruby"` |
| `SHELL` | `"shell"` |
| `MARKDOWN` | `"markdown"` |
| `YAML` | `"yaml"` |
| `JSON` | `"json"` |
| `TOML` | `"toml"` |
| `OTHER` | `"other"` |

**Related function:**

#### `detect_language`

```python
def detect_language(filepath: str) -> Language
```

| Parameter | Type | Description |
|---|---|---|
| `filepath` | `str` | File path (only the extension is inspected). |

**Returns:** `Language` — The detected language enum. Falls back to `Language.OTHER`.

```python
from github_guru.models.codebase import detect_language

detect_language("src/main.py")      # Language.PYTHON
detect_language("config.yaml")      # Language.YAML
detect_language("Makefile")         # Language.OTHER
```

---

### `ParameterInfo`

```python
@dataclass
class ParameterInfo:
    name: str
    type_annotation: str | None = None
    default_value: str | None = None
```

Represents a single function/method parameter.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Parameter name. |
| `type_annotation` | `str \| None` | Type annotation string (e.g. `"int"`, `"list[str]"`). |
| `default_value` | `str \| None` | Default value as unparsed source (e.g. `"False"`, `"None"`). |

**Methods:** `to_dict() -> dict`, `from_dict(cls, data) -> ParameterInfo`

---

### `FunctionInfo`

```python
@dataclass
class FunctionInfo:
    name: str
    filepath: str
    line_start: int
    line_end: int
    parameters: list[ParameterInfo] = field(default_factory=list)
    return_type: str | None = None
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None
    calls: list[str] = field(default_factory=list)
    is_method: bool = False
    is_async: bool = False
    class_name: str | None = None
```

Complete metadata for a function or method extracted via AST parsing.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Function name (e.g. `"analyze"`, `"__init__"`). |
| `filepath` | `str` | Relative path to the containing file. |
| `line_start` | `int` | Starting line number (1-indexed). |
| `line_end` | `int` | Ending line number (1-indexed). |
| `parameters` | `list[ParameterInfo]` | Ordered list of parameters. |
| `return_type` | `str \| None` | Return type annotation string. |
| `decorators` | `list[str]` | Decorator strings (e.g. `["staticmethod"]`). |
| `docstring` | `str \| None` | First string literal in the function body. |
| `calls` | `list[str]` | Deduplicated list of function/method names called within the body. |
| `is_method` | `bool` | `True` if this function is a class method. |
| `is_async` | `bool` | `True` if declared with `async def`. |
| `class_name` | `str \| None` | Name of the enclosing class, if a method. |

**Methods:** `to_dict() -> dict`, `from_dict(cls, data) -> FunctionInfo`

---

### `ClassInfo`

```python
@dataclass
class ClassInfo:
    name: str
    filepath: str
    line_start: int
    line_end: int
    bases: list[str] = field(default_factory=list)
    methods: list[FunctionInfo] = field(default_factory=list)
    class_variables: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None
```

Complete metadata for a class definition.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Class name. |
| `filepath` | `str` | Relative file path. |
| `line_start` / `line_end` | `int` | Line range (1-indexed). |
| `bases` | `list[str]` | Base class names (e.g. `["str", "Enum"]`). |
| `methods` | `list[FunctionInfo]` | Methods defined in the class body. |
| `class_variables` | `list[str]` | Class-level variable names. |
| `decorators` | `list[str]` | Class decorators. |
| `docstring` | `str \| None` | Class docstring. |

**Methods:** `to_dict() -> dict`, `from_dict(cls, data) -> ClassInfo`

---

### `ImportInfo`

```python
@dataclass
class ImportInfo:
    module: str
    names: list[str] = field(default_factory=list)
    alias: str | None = None
    is_relative: bool = False
    level: int = 0
```

Represents an `import` or `from ... import` statement.

| Field | Type | Description |
|---|---|---|
| `module` | `str` | Module path (e.g. `"os.path"`, `"github_guru.models"`). |
| `names` | `list[str]` | Imported names for `from` imports (e.g. `["Path", "PurePosixPath"]`). |
| `alias` | `str \| None` | Alias for `import X as Y` statements. |
| `is_relative` | `bool` | `True` for relative imports (e.g. `from . import foo`). |
| `level` | `int` | Number of dots in relative import (0 for absolute). |

**Methods:** `to_dict() -> dict`, `from_dict(cls, data) -> ImportInfo`

---

### `FileInfo`

```python
@dataclass
class FileInfo:
    filepath: str
    language: Language
    size_bytes: int
    line_count: int
    imports: list[ImportInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    docstring: str | None = None
```

Structural analysis of a single file.

| Field | Type | Description |
|---|---|---|
| `filepath` | `str` | Path relative to repo root. |
| `language` | `Language` | Detected language. |
| `size_bytes` | `int` | File size in bytes. |
| `line_count` | `int` | Total number of lines. |
| `imports` | `list[ImportInfo]` | All import statements (Python files only). |
| `functions` | `list[FunctionInfo]` | Top-level functions (Python files only). |
| `classes` | `list[ClassInfo]` | Class definitions (Python files only). |
| `docstring` | `str \| None` | Module-level docstring. |

**Methods:** `to_dict() -> dict`, `from_dict(cls, data) -> FileInfo`

---

### `RepoInfo`

```python
@dataclass
class RepoInfo:
    name: str
    root_path: str
    remote_url: str | None = None
    default_branch: str | None = None
    description: str | None = None
```

Repository-level metadata.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Repository name (directory name). |
| `root_path` | `str` | Absolute path to the repository root. |
| `remote_url` | `str \| None` | GitHub remote URL, if applicable. |
| `default_branch` | `str \| None` | Default branch name. |
| `description` | `str \| None` | Repository description. |

**Methods:** `to_dict() -> dict`, `from_dict(cls, data) -> RepoInfo`

---

### `CodebaseAnalysis`

```python
@dataclass
class CodebaseAnalysis:
    repo: RepoInfo
    files: list[FileInfo] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0
    languages: dict[str, int] = field(default_factory=dict)
```

Top-level analysis result encompassing the entire repository.

| Field | Type | Description |
|---|---|---|
| `repo` | `RepoInfo` | Repository metadata. |
| `files` | `list[FileInfo]` | Per-file structural data. |
| `total_files` | `int` | Number of analyzed files. |
| `total_lines` | `int` | Total line count across all files. |
| `languages` | `dict[str, int]` | Language → file count mapping. |

**Methods:** `to_dict() -> dict`, `from_dict(cls, data) -> CodebaseAnalysis`

**Example:**

```python
analysis = agent.analyze(".")
for fi in analysis.files:
    if fi.language == Language.PYTHON:
        print(f"{fi.filepath}: {len(fi.classes)} classes, {len(fi.functions)} functions")
```

---

## 3. Graph Models — `github_guru.models.graph`

**File:** `src/github_guru/models/graph.py`

### `RelationType`

```python
class RelationType(str, Enum):
    IMPORTS   = "imports"
    CALLS     = "calls"
    INHERITS  = "inherits"
    CONTAINS  = "contains"
```

Edge relationship types in the dependency graph.

---

### `NodeType`

```python
class NodeType(str, Enum):
    FILE     = "file"
    CLASS    = "class"
    FUNCTION = "function"
    MODULE   = "module"
```

Node categories in the dependency graph.

---

### `GraphNode`

```python
@dataclass
class GraphNode:
    id: str
    node_type: NodeType
    name: str
    filepath: str
    metadata: dict[str, Any] = field(default_factory=dict)
```

A single node in the dependency graph.

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique identifier. Format: `file:<path>`, `class:<path>:<name>`, `func:<path>:<name>`, or `method:<path>:<Class.method>`. |
| `node_type` | `NodeType` | Category of this node. |
| `name` | `str` | Human-readable name. |
| `filepath` | `str` | Source file path. |
| `metadata` | `dict` | Additional info (e.g. `{"language": "python", "lines": 42}`). |

**Methods:** `to_dict() -> dict`, `from_dict(cls, data) -> GraphNode`

---

### `GraphEdge`

```python
@dataclass
class GraphEdge:
    source: str
    target: str
    relation: RelationType
    metadata: dict[str, Any] = field(default_factory=dict)
```

A directed edge between two graph nodes.

| Field | Type | Description |
|---|---|---|
| `source` | `str` | Source node ID. |
| `target` | `str` | Target node ID. |
| `relation` | `RelationType` | Edge type (`IMPORTS`, `CALLS`, `INHERITS`, `CONTAINS`). |
| `metadata` | `dict` | Additional info (e.g. `{"names": ["Path", "PurePosixPath"]}`). |

**Methods:** `to_dict() -> dict`, `from_dict(cls, data) -> GraphEdge`

---

### `DependencyGraph`

```python
@dataclass
class DependencyGraph:
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)
```

The full dependency graph — nodes and directed edges.

#### `add_node`

```python
def add_node(self, node: GraphNode) -> None
```

Add a node to the graph, keyed by `node.id`.

#### `add_edge`

```python
def add_edge(self, edge: GraphEdge) -> None
```

Append an edge to the graph.

#### `get_dependents`

```python
def get_dependents(self, node_id: str) -> list[GraphNode]
```

Get nodes that **depend on** the given node (i.e., nodes with incoming edges pointing to `node_id`).

| Parameter | Type | Description |
|---|---|---|
| `node_id` | `str` | Target node identifier. |

**Returns:** `list[GraphNode]`

#### `get_dependencies`

```python
def get_dependencies(self, node_id: str) -> list[GraphNode]
```

Get nodes that the given node **depends on** (i.e., outgoing edges from `node_id`).

| Parameter | Type | Description |
|---|---|---|
| `node_id` | `str` | Source node identifier. |

**Returns:** `list[GraphNode]`

#### `get_edges_for`

```python
def get_edges_for(self, node_id: str) -> list[GraphEdge]
```

Get all edges (both incoming and outgoing) involving the given node.

| Parameter | Type | Description |
|---|---|---|
| `node_id` | `str` | Node identifier. |

**Returns:** `list[GraphEdge]`

#### `find_path`

```python
def find_path(self, start_id: str, end_id: str) -> list[str] | None
```

BFS shortest-path search between two nodes. Traverses edges bidirectionally.

| Parameter | Type | Description |
|---|---|---|
| `start_id` | `str` | Starting node ID. |
| `end_id` | `str` | Destination node ID. |

**Returns:** `list[str] | None` — Ordered list of node IDs forming the path, or `None` if no path exists.

#### `get_summary`

```python
def get_summary(self) -> dict[str, Any]
```

**Returns:** Summary dictionary with keys: `total_nodes`, `total_edges`, `node_types`, `relation_types`.

**Example:**

```python
graph = build_dependency_graph(analysis)

# Find what depends on a file
dependents = graph.get_dependents("file:src/github_guru/state.py")
for node in dependents:
    print(f"  {node.name} ({node.node_type.value})")

# Find path between two nodes
path = graph.find_path("file:src/github_guru/cli.py", "file:src/github_guru/models/codebase.py")
```

**Methods (serialization):** `to_dict() -> dict`, `from_dict(cls, data) -> DependencyGraph`

---

## 4. Cache — `github_guru.models.cache`

**File:** `src/github_guru/models/cache.py`

### `AnalysisCache`

```python
class AnalysisCache:
    """Save and load analysis results from a .github-guru/ cache directory."""
```

Persists analysis artifacts to `<repo_root>/.github-guru/`.

#### `__init__`

```python
def __init__(self, repo_root: str | Path) -> None
```

| Parameter | Type | Description |
|---|---|---|
| `repo_root` | `str \| Path` | Repository root path. The `.github-guru/` directory will be created inside it. |

#### Properties

| Property | Type | Description |
|---|---|---|
| `analysis_path` | `Path` | `.github-guru/analysis.json` |
| `graph_path` | `Path` | `.github-guru/graph.json` |
| `embeddings_path` | `Path` | `.github-guru/embeddings.npz` |
| `chunks_path` | `Path` | `.github-guru/chunks.json` |

#### `has_cache`

```python
def has_cache(self) -> bool
```

**Returns:** `True` if `analysis.json` exists in the cache directory.

#### `save_analysis` / `load_analysis`

```python
def save_analysis(self, analysis: CodebaseAnalysis) -> None
def load_analysis(self) -> CodebaseAnalysis | None
```

Serialize/deserialize the full [`CodebaseAnalysis`](#codebaseanalysis) to/from `analysis.json`.

#### `save_graph` / `load_graph`

```python
def save_graph(self, graph: DependencyGraph) -> None
def load_graph(self) -> DependencyGraph | None
```

Serialize/deserialize the [`DependencyGraph`](#dependencygraph) to/from `graph.json`.

#### `save_embeddings` / `load_embeddings`

```python
def save_embeddings(self, embeddings: np.ndarray, chunks: list[dict[str, Any]]) -> None
def load_embeddings(self) -> tuple[np.ndarray, list[dict[str, Any]]] | None
```

Save/load the NumPy embedding matrix (`embeddings.npz`) and chunk metadata (`chunks.json`).

**Example:**

```python
cache = AnalysisCache("/path/to/repo")

if cache.has_cache():
    analysis = cache.load_analysis()
    graph = cache.load_graph()
```

---

## 5. Analysis Engine — `github_guru.analysis`

### Ingestion — `analysis.ingestion`

**File:** `src/github_guru/analysis/ingestion.py`

#### `is_github_url`

```python
def is_github_url(source: str) -> bool
```

Test whether a string matches the `https://github.com/owner/repo` pattern.

---

#### `clone_repo`

```python
def clone_repo(url: str) -> str
```

Shallow-clone (`--depth 1`) a GitHub repo to a temporary directory.

| Parameter | Type | Description |
|---|---|---|
| `url` | `str` | GitHub HTTPS URL. |

**Returns:** `str` — Path to the cloned directory.

---

#### `collect_files`

```python
def collect_files(repo_root: str | Path) -> list[str]
```

Walk the repository and collect eligible file paths. Automatically ignores:

- **Directories:** `.git`, `node_modules`, `__pycache__`, `.venv`, `dist`, `build`, `.github-guru`, etc.
- **Extensions:** `.pyc`, `.so`, `.png`, `.zip`, `.lock`, etc.
- **Files larger than** 500 KB.

| Parameter | Type | Description |
|---|---|---|
| `repo_root` | `str \| Path` | Repository root path. |

**Returns:** `list[str]` — Sorted list of relative file paths.

---

#### `ingest_repo`

```python
def ingest_repo(source: str) -> tuple[str, list[str]]
```

Entry point for repository ingestion. Handles both local paths and GitHub URLs.

| Parameter | Type | Description |
|---|---|---|
| `source` | `str` | Local path or GitHub URL. |

**Returns:** `(repo_root, file_list)` — Absolute repo root and list of relative file paths.

**Raises:** `ValueError` if the local path does not exist.

**Example:**

```python
from github_guru.analysis.ingestion import ingest_repo

repo_root, files = ingest_repo("https://github.com/owner/repo")
print(f"Cloned to {repo_root}, found {len(files)} files")
```

---

### AST Parser — `analysis.ast_parser`

**File:** `src/github_guru/analysis/ast_parser.py`

#### `PythonASTVisitor`

```python
class PythonASTVisitor(ast.NodeVisitor):
    """Extract functions, classes, and imports from a Python AST."""
```

An `ast.NodeVisitor` subclass that walks a Python AST and populates:

| Attribute | Type | Description |
|---|---|---|
| `imports` | `list[ImportInfo]` | All import statements found. |
| `functions` | `list[FunctionInfo]` | Top-level functions (not methods). |
| `classes` | `list[ClassInfo]` | Class definitions with their methods. |
| `module_docstring` | `str \| None` | Module-level docstring. |

**Constructor:**

```python
def __init__(self, filepath: str) -> None
```

---

#### `parse_python_file`

```python
def parse_python_file(filepath: str, content: str) -> FileInfo
```

Parse a Python source file using `ast.parse` and extract full structural info.

| Parameter | Type | Description |
|---|---|---|
| `filepath` | `str` | Relative file path (used for metadata). |
| `content` | `str` | Raw file content. |

**Returns:** [`FileInfo`](#fileinfo) — Populated with imports, functions, classes, and docstring. Returns basic metadata on `SyntaxError`.

---

#### `parse_file`

```python
def parse_file(filepath: str, content: str) -> FileInfo
```

Parse any file. Delegates to `parse_python_file` for `.py` files; returns basic metadata (language, size, line count) for all other file types.

| Parameter | Type | Description |
|---|---|---|
| `filepath` | `str` | Relative file path. |
| `content` | `str` | Raw file content. |

**Returns:** [`FileInfo`](#fileinfo)

**Example:**

```python
from github_guru.analysis.ast_parser import parse_file

fi = parse_file("src/main.py", open("src/main.py").read())
print(f"Functions: {[f.name for f in fi.functions]}")
print(f"Classes: {[c.name for c in fi.classes]}")
```

---

### Chunker — `analysis.chunker`

**File:** `src/github_guru/analysis/chunker.py`

**Constants:**

| Name | Value | Description |
|---|---|---|
| `MAX_CHUNK_LINES` | `100` | Classes with more lines are split into method-level chunks. |
| `WINDOW_SIZE` | `60` | Sliding window size for non-Python files. |
| `WINDOW_OVERLAP` | `10` | Overlap between consecutive windows. |

#### `CodeChunk`

```python
@dataclass
class CodeChunk:
    content: str        # Raw code content
    filepath: str       # Relative file path
    chunk_type: str     # "function", "class", "module_header", or "window"
    name: str           # Human-readable chunk name
    line_start: int     # Start line (1-indexed)
    line_end: int       # End line (1-indexed)
```

A single embeddable code fragment.

##### `to_embedding_text`

```python
def to_embedding_text(self) -> str
```

Format the chunk for embedding input: `"{chunk_type}: {name}\n{filepath}\n{content}"`.

**Methods:** `to_dict() -> dict`, `from_dict(cls, data) -> CodeChunk`

---

#### `chunk_file`

```python
def chunk_file(fi: FileInfo, content: str) -> list[CodeChunk]
```

Split a single file into structure-aware chunks. Uses AST-based splitting for Python; sliding window for other languages.

| Parameter | Type | Description |
|---|---|---|
| `fi` | `FileInfo` | Parsed file metadata. |
| `content` | `str` | Raw file content. |

**Returns:** `list[CodeChunk]`

---

#### `chunk_codebase`

```python
def chunk_codebase(analysis: CodebaseAnalysis, repo_root: str) -> list[CodeChunk]
```

Chunk every file in the analysis. Reads each file from disk and applies `chunk_file`.

| Parameter | Type | Description |
|---|---|---|
| `analysis` | `CodebaseAnalysis` | The full analysis result. |
| `repo_root` | `str` | Absolute path to the repository root. |

**Returns:** `list[CodeChunk]` — All chunks across all files.

**Example:**

```python
from github_guru.analysis.chunker import chunk_codebase

chunks = chunk_codebase(analysis, "/path/to/repo")
print(f"Total chunks: {len(chunks)}")
for chunk in chunks[:3]:
    print(f"  [{chunk.chunk_type}] {chunk.name} ({chunk.filepath}:{chunk.line_start}-{chunk.line_end})")
```

---

### Embeddings — `analysis.embeddings`

**File:** `src/github_guru/analysis/embeddings.py`

**Model:** `all-MiniLM-L6-v2` (via `sentence-transformers`)

#### `CodeEmbeddingIndex`

```python
class CodeEmbeddingIndex:
    """Build and query a semantic embedding index over code chunks."""
```

##### `__init__`

```python
def __init__(self) -> None
```

Creates an empty index. The sentence-transformer model is lazy-loaded on first use.

##### `build`

```python
def build(self, chunks: list[CodeChunk]) -> None
```

Compute embeddings for all chunks using the `all-MiniLM-L6-v2` model.

| Parameter | Type | Description |
|---|---|---|
| `chunks` | `list[CodeChunk]` | Code chunks to embed. |

##### `load`

```python
def load(self, embeddings: np.ndarray, chunks: list[dict[str, Any]]) -> None
```

Load pre-computed embeddings and chunk metadata (from cache).

| Parameter | Type | Description |
|---|---|---|
| `embeddings` | `np.ndarray` | Embedding matrix of shape `(n_chunks, embed_dim)`. |
| `chunks` | `list[dict]` | Serialized chunk metadata dicts. |

##### `search`

```python
def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]
```

Semantic search via cosine similarity.

| Parameter | Type | Description |
|---|---|---|
| `query` | `str` | Natural language search query. |
| `top_k` | `int` | Number of results to return. Default `10`. |

**Returns:** `list[dict]` — Each dict contains: `content`, `filepath`, `chunk_type`, `name`, `line_start`, `line_end`, `similarity`.

##### `get_embeddings`

```python
def get_embeddings(self) -> np.ndarray | None
```

**Returns:** Raw embedding matrix, or `None` if not yet built/loaded.

##### `get_chunks_metadata`

```python
def get_chunks_metadata(self) -> list[dict[str, Any]]
```

**Returns:** Serialized chunk metadata for all indexed chunks.

**Example:**

```python
from github_guru.analysis.embeddings import CodeEmbeddingIndex

index = CodeEmbeddingIndex()
index.build(chunks)

results = index.search("error handling logic", top_k=5)
for r in results:
    print(f"  [{r['similarity']:.3f}] {r['name']} — {r['filepath']}:{r['line_start']}")
```

---

### Dependency Graph Builder — `analysis.dependency_graph`

**File:** `src/github_guru/analysis/dependency_graph.py`

#### `build_dependency_graph`

```python
def build_dependency_graph(analysis: CodebaseAnalysis) -> DependencyGraph
```

Build a complete dependency graph from the codebase analysis. Creates nodes for files, classes, and functions, and edges for imports, containment, and inheritance.

| Parameter | Type | Description |
|---|---|---|
| `analysis` | `CodebaseAnalysis` | The parsed codebase analysis. |

**Returns:** [`DependencyGraph`](#dependencygraph)

**Node ID formats:**

| Type | Format | Example |
|---|---|---|
| File | `file:<filepath>` | `file:src/github_guru/agent.py` |
| Class | `class:<filepath>:<name>` | `class:src/github_guru/agent.py:GitHubGuruAgent` |
| Function | `func:<filepath>:<name>` | `func:src/github_guru/cli.py:analyze` |
| Method | `method:<filepath>:<Class.method>` | `method:src/github_guru/agent.py:GitHubGuruAgent.ask` |

**Example:**

```python
from github_guru.analysis.dependency_graph import build_dependency_graph

graph = build_dependency_graph(analysis)
summary = graph.get_summary()
print(f"Nodes: {summary['total_nodes']}, Edges: {summary['total_edges']}")
```

---

## 6. GitHub Client — `github_guru.github.client`

**File:** `src/github_guru/github/client.py`

### `GitHubClient`

```python
class GitHubClient:
    """Thin wrapper around PyGithub for repo metadata and cloning."""
```

#### `__init__`

```python
def __init__(self, token: str | None = None) -> None
```

| Parameter | Type | Description |
|---|---|---|
| `token` | `str \| None` | GitHub personal access token. Falls back to `GITHUB_TOKEN` env var. Unauthenticated if neither is set. |

#### `get_repo_metadata`

```python
def get_repo_metadata(self, owner: str, repo: str) -> dict[str, Any]
```

Fetch repository metadata from the GitHub API.

**Returns:** Dict with keys: `name`, `full_name`, `description`, `language`, `stars`, `forks`, `open_issues`, `default_branch`, `created_at`, `updated_at`, `topics`.

#### `get_recent_commits`

```python
def get_recent_commits(self, owner: str, repo: str, limit: int = 10) -> list[dict[str, Any]]
```

**Returns:** List of dicts with keys: `sha`, `message`, `author`, `date`.

#### `get_issues`

```python
def get_issues(self, owner: str, repo: str, state: str = "open", limit: int = 10) -> list[dict[str, Any]]
```

| Parameter | Type | Description |
|---|---|---|
| `state` | `str` | Filter by state: `"open"`, `"closed"`, or `"all"`. Default `"open"`. |

**Returns:** List of dicts with keys: `number`, `title`, `state`, `author`, `labels`, `created_at`.

#### `clone_repo` *(static)*

```python
@staticmethod
def clone_repo(url: str, target_dir: str | None = None) -> str
```

Shallow-clone a repository using `git` subprocess.

| Parameter | Type | Description |
|---|---|---|
| `url` | `str` | Repository URL. |
| `target_dir` | `str \| None` | Target directory. Auto-generated temp dir if `None`. |

**Returns:** `str` — Path to the cloned directory.

---

## 7. MCP Tools — `github_guru.tools`

All tools are `async` functions decorated with `@tool(name, description, params)` from the Claude Agent SDK. They follow the MCP return format:

```python
{"content": [{"type": "text", "text": "<JSON string>"}]}
```

On errors, they include `"is_error": True`.

---

### `list_files`

**File:** `src/github_guru/tools/list_files.py`

```python
@tool("list_files", ..., {"pattern": str, "include_metadata": bool})
async def list_files(args: dict[str, Any]) -> dict[str, Any]
```

List files in the analyzed repository, optionally filtered by glob pattern.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `pattern` | `str` | `"*"` | Glob pattern (e.g. `"*.py"`, `"src/**/*.ts"`). |
| `include_metadata` | `bool` | `False` | If `True`, returns objects with `path`, `language`, `size_bytes`, `line_count`. |

---

### `read_file`

**File:** `src/github_guru/tools/read_file.py`

```python
@tool("read_file", ..., {"filepath": str, "start_line": int, "end_line": int})
async def read_file(args: dict[str, Any]) -> dict[str, Any]
```

Read file contents with line numbers. Truncates at **30,000 characters**.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `filepath` | `str` | *(required)* | Relative file path within the repo. |
| `start_line` | `int` | `None` | Start line (1-indexed). |
| `end_line` | `int` | `None` | End line (1-indexed). |

---

### `search_code`

**File:** `src/github_guru/tools/search_code.py`

```python
@tool("search_code", ..., {"pattern": str, "file_glob": str, "max_results": int})
async def search_code(args: dict[str, Any]) -> dict[str, Any]
```

Regex search across all repository files with 2-line context.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `pattern` | `str` | *(required)* | Regex pattern (case-insensitive). |
| `file_glob` | `str` | `"*"` | Glob to filter which files to search. |
| `max_results` | `int` | `50` | Maximum number of matches returned. |

**Returns:** JSON with `summary` string and `matches` array (each with `file`, `line`, `match`, `context`).

---

### `query_structure`

**File:** `src/github_guru/tools/query_structure.py`

```python
@tool("query_structure", ..., {"query_type": str, "name_filter": str, "filepath": str})
async def query_structure(args: dict[str, Any]) -> dict[str, Any]
```

Query AST-extracted structural data.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query_type` | `str` | `"overview"` | One of: `"overview"`, `"classes"`, `"functions"`, `"imports"`, `"file_summary"`. |
| `name_filter` | `str` | `None` | Wildcard filter for names (e.g. `"*Agent*"`). Applies to `classes` and `functions`. |
| `filepath` | `str` | `None` | Required for `file_summary`; optional filter for `imports`. |

---

### `query_graph` (tool)

**File:** `src/github_guru/tools/query_graph.py`

```python
@tool("query_graph", ..., {"action": str, "node_id": str, "target_id": str})
async def query_graph(args: dict[str, Any]) -> dict[str, Any]
```

Query the dependency graph.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `action` | `str` | `"summary"` | One of: `"summary"`, `"dependents"`, `"dependencies"`, `"path"`. |
| `node_id` | `str` | `None` | Node identifier (supports partial matching). Required for all actions except `summary`. |
| `target_id` | `str` | `None` | Second node identifier. Required for `"path"`. |

**Node ID formats:** `file:<path>`, `class:<path>:<name>`, `func:<path>:<name>`

---

### `semantic_search`

**File:** `src/github_guru/tools/semantic_search.py`

```python
@tool("semantic_search", ..., {"query": str, "top_k": int})
async def semantic_search(args: dict[str, Any]) -> dict[str, Any]
```

Search code by meaning using semantic embeddings.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | `str` | *(required)* | Natural language search query. |
| `top_k` | `int` | `10` | Number of results. |

**Returns:** JSON with `query`, `results` (each with `content`, `filepath`, `chunk_type`, `name`, `line_start`, `line_end`, `similarity`), and `count`.

---

### `get_git_info`

**File:** `src/github_guru/tools/get_git_info.py`

```python
@tool("get_git_info", ..., {"info_type": str, "filepath": str, "limit": int})
async def get_git_info(args: dict[str, Any]) -> dict[str, Any]
```

Get git metadata via subprocess.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `info_type` | `str` | `"commits"` | One of: `"commits"`, `"contributors"`, `"branches"`, `"file_history"`. |
| `filepath` | `str` | `None` | Required for `"file_history"`. Optional filter for `"commits"`. |
| `limit` | `int` | `20` | Maximum results. |

---

## 8. State Management — `github_guru.state`

**File:** `src/github_guru/state.py`

Module-level globals that bridge the agent and MCP tools. Avoids circular imports by using `TYPE_CHECKING` guards.

#### `set_state`

```python
def set_state(
    analysis: CodebaseAnalysis,
    graph: DependencyGraph,
    embedding_index: CodeEmbeddingIndex,
    repo_root: str,
) -> None
```

Set all global state variables. Called by `GitHubGuruAgent` after analysis or cache load.

#### `get_analysis`

```python
def get_analysis() -> CodebaseAnalysis
```

**Returns:** The loaded analysis. **Raises** `RuntimeError` if not initialized.

#### `get_graph`

```python
def get_graph() -> DependencyGraph
```

**Returns:** The loaded dependency graph. **Raises** `RuntimeError` if not initialized.

#### `get_embedding_index`

```python
def get_embedding_index() -> CodeEmbeddingIndex
```

**Returns:** The loaded embedding index. **Raises** `RuntimeError` if not initialized.

#### `get_repo_root`

```python
def get_repo_root() -> str
```

**Returns:** The repository root path. **Raises** `RuntimeError` if not initialized.

---

## 9. CLI — `github_guru.cli`

**File:** `src/github_guru/cli.py`

The CLI is built with [Typer](https://typer.tiangolo.com/) and uses [Rich](https://rich.readthedocs.io/) for terminal output.

**Entry point:** `github-guru` (configured in `pyproject.toml`)

### `analyze` command

```
github-guru analyze <SOURCE> [--no-embeddings]
```

| Argument/Option | Description |
|---|---|
| `SOURCE` | Local path or GitHub URL. |
| `--no-embeddings` | Skip embedding generation for faster analysis. |

Runs the full pipeline and displays a summary table.

### `ask` command

```
github-guru ask <QUESTION> [--repo PATH]
```

| Argument/Option | Default | Description |
|---|---|---|
| `QUESTION` | *(required)* | Natural language question. |
| `--repo`, `-r` | `"."` | Path to an analyzed repository. |

Loads from cache (or runs analysis first), then queries Claude.

### `docs` command

```
github-guru docs <SOURCE> [-o DIR] [-t TYPE]...
```

| Argument/Option | Default | Description |
|---|---|---|
| `SOURCE` | *(required)* | Local path or GitHub URL. |
| `-o`, `--output` | `"./docs"` | Output directory for generated Markdown. |
| `-t`, `--type` | all types | Doc types to generate: `overview`, `architecture`, `files`, `api`. |

**Example:**

```bash
# Full analysis
github-guru analyze /path/to/project

# Ask a question
github-guru ask "How does authentication work?" --repo /path/to/project

# Generate specific docs
github-guru docs /path/to/project -o ./docs -t overview -t api
```