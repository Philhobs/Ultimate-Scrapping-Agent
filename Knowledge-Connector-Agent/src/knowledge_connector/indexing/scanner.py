"""Scanner — walk directories, detect file types, and extract text content."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# File extensions grouped by type
TEXT_EXTENSIONS = {
    "markdown": {".md", ".mdx", ".markdown"},
    "text": {".txt", ".text", ".rst", ".adoc"},
    "code": {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
             ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift",
             ".kt", ".scala", ".sh", ".bash", ".zsh", ".fish"},
    "config": {".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".json"},
    "web": {".html", ".htm", ".css", ".scss", ".xml", ".svg"},
    "docs": {".tex", ".bib", ".org"},
}

ALL_EXTENSIONS = set()
for exts in TEXT_EXTENSIONS.values():
    ALL_EXTENSIONS |= exts

# Directories to skip
SKIP_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", "node_modules", ".venv", "venv",
    "env", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", ".egg-info", ".next", ".nuxt", "target",
    ".knowledge-connector",
}

SKIP_PATTERNS = {"*.pyc", "*.pyo", "*.so", "*.dylib", "*.exe", "*.min.js", "*.min.css"}


@dataclass
class DocumentInfo:
    """Metadata about an indexed document."""
    filepath: str          # Relative to root
    abs_path: str          # Absolute path
    file_type: str         # "markdown", "code", "config", etc.
    extension: str
    title: str             # Extracted title or filename
    content: str           # Raw text content
    line_count: int
    size_bytes: int
    headings: list[str] = field(default_factory=list)  # Extracted headings (markdown)


def detect_file_type(ext: str) -> str:
    """Classify a file extension into a type category."""
    for ftype, exts in TEXT_EXTENSIONS.items():
        if ext in exts:
            return ftype
    return "unknown"


def extract_title(content: str, filepath: str, ext: str) -> str:
    """Extract a title from the document content."""
    if ext in TEXT_EXTENSIONS["markdown"]:
        for line in content.split("\n")[:10]:
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("##"):
                return stripped[2:].strip()
    return Path(filepath).stem


def extract_headings(content: str, ext: str) -> list[str]:
    """Extract section headings from markdown content."""
    if ext not in TEXT_EXTENSIONS["markdown"]:
        return []
    headings = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            # Count level and extract text
            level = 0
            for ch in stripped:
                if ch == "#":
                    level += 1
                else:
                    break
            text = stripped[level:].strip()
            if text:
                headings.append(f"{'#' * level} {text}")
    return headings


def scan_directory(
    root: str,
    extensions: set[str] | None = None,
    ignore_patterns: list[str] | None = None,
) -> list[DocumentInfo]:
    """Scan a directory tree and return DocumentInfo for each text file."""
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {root}")

    allowed_ext = extensions or ALL_EXTENSIONS
    extra_ignore = ignore_patterns or []
    documents: list[DocumentInfo] = []

    for path in sorted(root_path.rglob("*")):
        # Skip directories in the ignore list
        if any(part in SKIP_DIRS for part in path.parts):
            continue

        if not path.is_file():
            continue

        # Check extension
        ext = path.suffix.lower()
        if ext not in allowed_ext:
            continue

        # Check skip patterns
        if any(fnmatch.fnmatch(path.name, p) for p in SKIP_PATTERNS):
            continue

        # Check user ignore patterns
        rel = str(path.relative_to(root_path))
        if any(fnmatch.fnmatch(rel, p) for p in extra_ignore):
            continue

        # Read content
        try:
            content = path.read_text(errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        file_type = detect_file_type(ext)
        title = extract_title(content, rel, ext)
        headings = extract_headings(content, ext)

        documents.append(DocumentInfo(
            filepath=rel,
            abs_path=str(path),
            file_type=file_type,
            extension=ext,
            title=title,
            content=content,
            line_count=content.count("\n") + 1,
            size_bytes=path.stat().st_size,
            headings=headings,
        ))

    return documents
