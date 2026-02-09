"""Structure-aware code chunking for embedding."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from github_guru.models.codebase import CodebaseAnalysis, FileInfo, Language


@dataclass
class CodeChunk:
    content: str
    filepath: str
    chunk_type: str  # "function", "class", "module_header", "window"
    name: str
    line_start: int
    line_end: int

    def to_embedding_text(self) -> str:
        """Format chunk for embedding: type + name + path + content."""
        return f"{self.chunk_type}: {self.name}\n{self.filepath}\n{self.content}"

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "filepath": self.filepath,
            "chunk_type": self.chunk_type,
            "name": self.name,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CodeChunk:
        return cls(**data)


MAX_CHUNK_LINES = 100
WINDOW_SIZE = 60
WINDOW_OVERLAP = 10


def chunk_file(fi: FileInfo, content: str) -> list[CodeChunk]:
    """Split a file into structure-aware chunks."""
    if fi.language == Language.PYTHON:
        return _chunk_python(fi, content)
    return _chunk_sliding_window(fi, content)


def _chunk_python(fi: FileInfo, content: str) -> list[CodeChunk]:
    """Chunk a Python file by functions and classes."""
    lines = content.split("\n")
    chunks: list[CodeChunk] = []
    used_lines: set[int] = set()

    # Chunk each class
    for cls in fi.classes:
        start = cls.line_start - 1  # 1-indexed to 0-indexed
        end = cls.line_end
        cls_lines = lines[start:end]
        cls_content = "\n".join(cls_lines)

        if len(cls_lines) > MAX_CHUNK_LINES:
            # Split large classes into method-level chunks
            # First: class header (up to first method or MAX_CHUNK_LINES)
            first_method_line = None
            for method in cls.methods:
                if first_method_line is None or method.line_start < first_method_line:
                    first_method_line = method.line_start

            if first_method_line is not None:
                header_end = first_method_line - 1
                header = "\n".join(lines[start:header_end - 1])
                if header.strip():
                    chunks.append(CodeChunk(
                        content=header,
                        filepath=fi.filepath,
                        chunk_type="class",
                        name=f"{cls.name} (header)",
                        line_start=cls.line_start,
                        line_end=header_end,
                    ))

                for method in cls.methods:
                    m_start = method.line_start - 1
                    m_end = method.line_end
                    method_content = "\n".join(lines[m_start:m_end])
                    chunks.append(CodeChunk(
                        content=method_content,
                        filepath=fi.filepath,
                        chunk_type="function",
                        name=f"{cls.name}.{method.name}",
                        line_start=method.line_start,
                        line_end=method.line_end,
                    ))
                    used_lines.update(range(m_start, m_end))
            else:
                chunks.append(CodeChunk(
                    content=cls_content,
                    filepath=fi.filepath,
                    chunk_type="class",
                    name=cls.name,
                    line_start=cls.line_start,
                    line_end=cls.line_end,
                ))
        else:
            chunks.append(CodeChunk(
                content=cls_content,
                filepath=fi.filepath,
                chunk_type="class",
                name=cls.name,
                line_start=cls.line_start,
                line_end=cls.line_end,
            ))

        used_lines.update(range(start, end))

    # Chunk standalone functions
    for func in fi.functions:
        start = func.line_start - 1
        end = func.line_end
        func_content = "\n".join(lines[start:end])
        chunks.append(CodeChunk(
            content=func_content,
            filepath=fi.filepath,
            chunk_type="function",
            name=func.name,
            line_start=func.line_start,
            line_end=func.line_end,
        ))
        used_lines.update(range(start, end))

    # Module header: imports + globals (lines not covered by functions/classes)
    header_lines = []
    for i, line in enumerate(lines):
        if i not in used_lines:
            header_lines.append((i, line))

    if header_lines:
        header_content = "\n".join(line for _, line in header_lines)
        if header_content.strip():
            chunks.append(CodeChunk(
                content=header_content,
                filepath=fi.filepath,
                chunk_type="module_header",
                name=Path(fi.filepath).stem,
                line_start=header_lines[0][0] + 1,
                line_end=header_lines[-1][0] + 1,
            ))

    return chunks


def _chunk_sliding_window(fi: FileInfo, content: str) -> list[CodeChunk]:
    """Chunk non-Python files using a sliding window."""
    lines = content.split("\n")
    if not lines or not content.strip():
        return []

    chunks: list[CodeChunk] = []
    i = 0
    while i < len(lines):
        end = min(i + WINDOW_SIZE, len(lines))
        window = "\n".join(lines[i:end])
        if window.strip():
            chunks.append(CodeChunk(
                content=window,
                filepath=fi.filepath,
                chunk_type="window",
                name=f"{Path(fi.filepath).name}:{i + 1}-{end}",
                line_start=i + 1,
                line_end=end,
            ))
        if end >= len(lines):
            break
        i += WINDOW_SIZE - WINDOW_OVERLAP

    return chunks


def chunk_codebase(analysis: CodebaseAnalysis, repo_root: str) -> list[CodeChunk]:
    """Chunk all files in a codebase analysis."""
    all_chunks: list[CodeChunk] = []
    root = Path(repo_root)

    for fi in analysis.files:
        try:
            content = (root / fi.filepath).read_text(errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        chunks = chunk_file(fi, content)
        all_chunks.extend(chunks)

    return all_chunks
