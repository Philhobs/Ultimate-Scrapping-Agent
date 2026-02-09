"""Code parser — extract functions, classes, and project structure from source files."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FunctionInfo:
    """Extracted function/method metadata."""
    name: str
    file: str
    line: int
    end_line: int | None
    params: list[str]
    return_type: str | None
    docstring: str | None
    is_method: bool
    class_name: str | None
    decorators: list[str]
    is_async: bool

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "file": self.file,
            "line": self.line,
            "end_line": self.end_line,
            "params": self.params,
            "return_type": self.return_type,
            "docstring": self.docstring,
            "is_method": self.is_method,
            "class_name": self.class_name,
            "decorators": self.decorators,
            "is_async": self.is_async,
        }


@dataclass
class CodebaseProfile:
    """Full project analysis result."""
    root: str
    name: str
    language: str
    test_framework: str | None
    source_files: list[str]
    test_files: list[str]
    functions: list[FunctionInfo]
    total_functions: int
    total_files: int
    total_lines: int
    has_tests: bool
    existing_configs: list[str] = field(default_factory=list)


# -- File extension to language mapping --

SOURCE_EXTS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
}

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".mypy_cache", ".ruff_cache",
    ".pytest_cache", "venv", ".venv", "env", ".env", "dist", "build",
    ".tox", ".eggs", "*.egg-info", "vendor", "target",
}

TEST_PATTERNS = [
    re.compile(r"test_.*\.py$"),
    re.compile(r".*_test\.py$"),
    re.compile(r".*\.test\.[jt]sx?$"),
    re.compile(r".*\.spec\.[jt]sx?$"),
    re.compile(r".*_test\.go$"),
    re.compile(r"test_.*\.rb$"),
    re.compile(r".*_test\.rb$"),
    re.compile(r".*Test\.java$"),
    re.compile(r".*_test\.rs$"),
]


def scan_codebase(root: str) -> CodebaseProfile:
    """Scan a project directory and extract full structure."""
    root_path = Path(root).resolve()
    name = root_path.name

    source_files: list[str] = []
    test_files: list[str] = []
    functions: list[FunctionInfo] = []
    total_lines = 0
    language_counts: dict[str, int] = {}
    configs: list[str] = []

    # Detect config files
    for config in ("pytest.ini", "setup.cfg", "pyproject.toml", "jest.config.js",
                   "jest.config.ts", "vitest.config.ts", "go.mod", "Cargo.toml",
                   "pom.xml", "build.gradle", ".rspec", "Gemfile"):
        if (root_path / config).exists():
            configs.append(config)

    # Walk source files
    for file_path in root_path.rglob("*"):
        if any(skip in file_path.parts for skip in SKIP_DIRS):
            continue
        if not file_path.is_file():
            continue

        suffix = file_path.suffix
        if suffix not in SOURCE_EXTS:
            continue

        lang = SOURCE_EXTS[suffix]
        rel = str(file_path.relative_to(root_path))

        # Count lines
        try:
            content = file_path.read_text(errors="replace")
            lines = content.count("\n") + 1
            total_lines += lines
        except OSError:
            continue

        language_counts[lang] = language_counts.get(lang, 0) + lines

        # Classify as test or source
        is_test = any(p.search(file_path.name) for p in TEST_PATTERNS)
        if is_test or "test" in file_path.parts or "tests" in file_path.parts:
            test_files.append(rel)
        else:
            source_files.append(rel)

        # Extract functions
        if lang == "python":
            functions.extend(_parse_python(content, rel))
        elif lang in ("javascript", "typescript"):
            functions.extend(_parse_js_ts(content, rel))
        elif lang == "go":
            functions.extend(_parse_go(content, rel))

    # Determine primary language
    language = max(language_counts, key=language_counts.get) if language_counts else "unknown"

    # Detect test framework
    test_framework = _detect_test_framework(root_path, language, configs)

    return CodebaseProfile(
        root=str(root_path),
        name=name,
        language=language,
        test_framework=test_framework,
        source_files=sorted(source_files),
        test_files=sorted(test_files),
        functions=functions,
        total_functions=len(functions),
        total_files=len(source_files) + len(test_files),
        total_lines=total_lines,
        has_tests=len(test_files) > 0,
        existing_configs=configs,
    )


def _detect_test_framework(root: Path, language: str, configs: list[str]) -> str | None:
    """Detect the test framework based on language and config files."""
    if language == "python":
        if "pytest.ini" in configs:
            return "pytest"
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(errors="replace")
            if "pytest" in content:
                return "pytest"
        # Check if pytest or unittest is used in test files
        for tf in root.rglob("test_*.py"):
            try:
                content = tf.read_text(errors="replace")
                if "import pytest" in content or "from pytest" in content:
                    return "pytest"
                if "import unittest" in content:
                    return "unittest"
            except OSError:
                continue
        return "pytest"  # default for Python

    elif language in ("javascript", "typescript"):
        if any("jest" in c for c in configs):
            return "jest"
        if any("vitest" in c for c in configs):
            return "vitest"
        pkg_json = root / "package.json"
        if pkg_json.exists():
            content = pkg_json.read_text(errors="replace")
            if "jest" in content:
                return "jest"
            if "vitest" in content:
                return "vitest"
            if "mocha" in content:
                return "mocha"
        return "jest"

    elif language == "go":
        return "go_test"

    elif language == "rust":
        return "cargo_test"

    elif language == "java":
        return "junit"

    elif language == "ruby":
        if ".rspec" in configs:
            return "rspec"
        return "minitest"

    return None


def _parse_python(content: str, filepath: str) -> list[FunctionInfo]:
    """Parse Python file using the ast module."""
    functions: list[FunctionInfo] = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return functions

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Get params
            params = []
            for arg in node.args.args:
                if arg.arg != "self" and arg.arg != "cls":
                    params.append(arg.arg)

            # Get return type annotation
            return_type = None
            if node.returns:
                try:
                    return_type = ast.unparse(node.returns)
                except Exception:
                    pass

            # Get docstring
            docstring = ast.get_docstring(node)

            # Determine if method
            class_name = None
            is_method = False
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    if node in ast.iter_child_nodes(parent):
                        class_name = parent.name
                        is_method = True
                        break

            # Get decorators
            decorators = []
            for dec in node.decorator_list:
                try:
                    decorators.append(ast.unparse(dec))
                except Exception:
                    pass

            functions.append(FunctionInfo(
                name=node.name,
                file=filepath,
                line=node.lineno,
                end_line=node.end_lineno,
                params=params,
                return_type=return_type,
                docstring=docstring,
                is_method=is_method,
                class_name=class_name,
                decorators=decorators,
                is_async=isinstance(node, ast.AsyncFunctionDef),
            ))

    return functions


def _parse_js_ts(content: str, filepath: str) -> list[FunctionInfo]:
    """Parse JS/TS files using regex (best-effort)."""
    functions: list[FunctionInfo] = []

    # Match: function name(params) { ... }
    # Match: const name = (params) => { ... }
    # Match: async function name(params) { ... }
    # Match: name(params) { ... }  (method shorthand)
    patterns = [
        re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE),
        re.compile(r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*(?::\s*\w+)?\s*=>", re.MULTILINE),
        re.compile(r"^\s+(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*(?::\s*\w+)?\s*\{", re.MULTILINE),
    ]

    lines = content.split("\n")
    for pattern in patterns:
        for match in pattern.finditer(content):
            name = match.group(1)
            params_str = match.group(2).strip()
            params = [p.strip().split(":")[0].strip() for p in params_str.split(",") if p.strip()] if params_str else []

            # Find line number
            pos = match.start()
            line_num = content[:pos].count("\n") + 1

            is_async = "async" in match.group(0)

            functions.append(FunctionInfo(
                name=name,
                file=filepath,
                line=line_num,
                end_line=None,
                params=params,
                return_type=None,
                docstring=None,
                is_method=False,
                class_name=None,
                decorators=[],
                is_async=is_async,
            ))

    return functions


def _parse_go(content: str, filepath: str) -> list[FunctionInfo]:
    """Parse Go files using regex."""
    functions: list[FunctionInfo] = []

    # Match: func Name(params) returnType { ... }
    # Match: func (r *Receiver) Name(params) returnType { ... }
    pattern = re.compile(
        r"func\s+(?:\((\w+)\s+\*?(\w+)\)\s+)?(\w+)\s*\(([^)]*)\)\s*([^{]*?)\s*\{",
        re.MULTILINE,
    )

    for match in pattern.finditer(content):
        receiver_var = match.group(1)
        receiver_type = match.group(2)
        name = match.group(3)
        params_str = match.group(4).strip()
        return_str = match.group(5).strip()

        params = []
        if params_str:
            for p in params_str.split(","):
                parts = p.strip().split()
                if parts:
                    params.append(parts[0])

        pos = match.start()
        line_num = content[:pos].count("\n") + 1

        functions.append(FunctionInfo(
            name=name,
            file=filepath,
            line=line_num,
            end_line=None,
            params=params,
            return_type=return_str if return_str else None,
            docstring=None,
            is_method=receiver_type is not None,
            class_name=receiver_type,
            decorators=[],
            is_async=False,
        ))

    return functions
