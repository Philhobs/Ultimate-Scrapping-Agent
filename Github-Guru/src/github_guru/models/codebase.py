"""Data models for codebase analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    C = "c"
    CPP = "cpp"
    RUBY = "ruby"
    SHELL = "shell"
    MARKDOWN = "markdown"
    YAML = "yaml"
    JSON = "json"
    TOML = "toml"
    OTHER = "other"


EXTENSION_MAP: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
    ".java": Language.JAVA,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".c": Language.C,
    ".h": Language.C,
    ".cpp": Language.CPP,
    ".hpp": Language.CPP,
    ".cc": Language.CPP,
    ".rb": Language.RUBY,
    ".sh": Language.SHELL,
    ".bash": Language.SHELL,
    ".md": Language.MARKDOWN,
    ".yaml": Language.YAML,
    ".yml": Language.YAML,
    ".json": Language.JSON,
    ".toml": Language.TOML,
}


def detect_language(filepath: str) -> Language:
    """Detect language from file extension."""
    from pathlib import Path

    ext = Path(filepath).suffix.lower()
    return EXTENSION_MAP.get(ext, Language.OTHER)


@dataclass
class ParameterInfo:
    name: str
    type_annotation: str | None = None
    default_value: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type_annotation": self.type_annotation,
            "default_value": self.default_value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParameterInfo:
        return cls(**data)


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "filepath": self.filepath,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_type": self.return_type,
            "decorators": self.decorators,
            "docstring": self.docstring,
            "calls": self.calls,
            "is_method": self.is_method,
            "is_async": self.is_async,
            "class_name": self.class_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FunctionInfo:
        data = dict(data)
        data["parameters"] = [ParameterInfo.from_dict(p) for p in data.get("parameters", [])]
        return cls(**data)


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "filepath": self.filepath,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "bases": self.bases,
            "methods": [m.to_dict() for m in self.methods],
            "class_variables": self.class_variables,
            "decorators": self.decorators,
            "docstring": self.docstring,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClassInfo:
        data = dict(data)
        data["methods"] = [FunctionInfo.from_dict(m) for m in data.get("methods", [])]
        return cls(**data)


@dataclass
class ImportInfo:
    module: str
    names: list[str] = field(default_factory=list)
    alias: str | None = None
    is_relative: bool = False
    level: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "names": self.names,
            "alias": self.alias,
            "is_relative": self.is_relative,
            "level": self.level,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImportInfo:
        return cls(**data)


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "filepath": self.filepath,
            "language": self.language.value,
            "size_bytes": self.size_bytes,
            "line_count": self.line_count,
            "imports": [i.to_dict() for i in self.imports],
            "functions": [f.to_dict() for f in self.functions],
            "classes": [c.to_dict() for c in self.classes],
            "docstring": self.docstring,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileInfo:
        data = dict(data)
        data["language"] = Language(data["language"])
        data["imports"] = [ImportInfo.from_dict(i) for i in data.get("imports", [])]
        data["functions"] = [FunctionInfo.from_dict(f) for f in data.get("functions", [])]
        data["classes"] = [ClassInfo.from_dict(c) for c in data.get("classes", [])]
        return cls(**data)


@dataclass
class RepoInfo:
    name: str
    root_path: str
    remote_url: str | None = None
    default_branch: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "root_path": self.root_path,
            "remote_url": self.remote_url,
            "default_branch": self.default_branch,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepoInfo:
        return cls(**data)


@dataclass
class CodebaseAnalysis:
    repo: RepoInfo
    files: list[FileInfo] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0
    languages: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo.to_dict(),
            "files": [f.to_dict() for f in self.files],
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "languages": self.languages,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodebaseAnalysis:
        data = dict(data)
        data["repo"] = RepoInfo.from_dict(data["repo"])
        data["files"] = [FileInfo.from_dict(f) for f in data.get("files", [])]
        return cls(**data)
