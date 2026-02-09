"""Chunker — split documents into overlapping chunks for embedding and search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from knowledge_connector.indexing.scanner import DocumentInfo


@dataclass
class Chunk:
    """A chunk of text with source metadata."""
    chunk_id: int
    doc_filepath: str
    doc_title: str
    heading: str          # Nearest heading context
    text: str
    start_line: int
    end_line: int
    file_type: str


def chunk_document(
    doc: DocumentInfo,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[Chunk]:
    """Split a document into overlapping chunks.

    For markdown files, tries to split on heading boundaries first.
    For other files, splits by line count with overlap.
    """
    lines = doc.content.split("\n")

    # For markdown, split on headings to keep sections together
    if doc.file_type == "markdown":
        return _chunk_by_headings(doc, lines, chunk_size)

    return _chunk_by_lines(doc, lines, chunk_size, overlap)


def _chunk_by_headings(doc: DocumentInfo, lines: list[str], max_chars: int) -> list[Chunk]:
    """Split markdown by heading sections, further splitting large sections."""
    sections: list[tuple[str, int, list[str]]] = []
    current_heading = doc.title
    current_start = 0
    current_lines: list[str] = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and not stripped.startswith("#!"):
            if current_lines:
                sections.append((current_heading, current_start, current_lines))
            current_heading = stripped.lstrip("#").strip()
            current_start = i
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, current_start, current_lines))

    chunks: list[Chunk] = []
    chunk_id = 0

    for heading, start_line, section_lines in sections:
        text = "\n".join(section_lines)
        if len(text) <= max_chars:
            chunks.append(Chunk(
                chunk_id=chunk_id,
                doc_filepath=doc.filepath,
                doc_title=doc.title,
                heading=heading,
                text=text,
                start_line=start_line,
                end_line=start_line + len(section_lines),
                file_type=doc.file_type,
            ))
            chunk_id += 1
        else:
            # Split large section into sub-chunks
            sub = _chunk_by_lines(doc, section_lines, max_chars, overlap=80)
            for s in sub:
                s.chunk_id = chunk_id
                s.heading = heading
                s.start_line += start_line
                s.end_line += start_line
                chunks.append(s)
                chunk_id += 1

    return chunks


def _chunk_by_lines(
    doc: DocumentInfo,
    lines: list[str],
    max_chars: int,
    overlap: int,
) -> list[Chunk]:
    """Split by accumulating lines until max_chars, with overlap."""
    chunks: list[Chunk] = []
    chunk_id = 0
    i = 0

    while i < len(lines):
        chunk_lines: list[str] = []
        char_count = 0
        start = i

        while i < len(lines) and char_count < max_chars:
            chunk_lines.append(lines[i])
            char_count += len(lines[i]) + 1
            i += 1

        text = "\n".join(chunk_lines)
        if text.strip():
            chunks.append(Chunk(
                chunk_id=chunk_id,
                doc_filepath=doc.filepath,
                doc_title=doc.title,
                heading=doc.title,
                text=text,
                start_line=start,
                end_line=start + len(chunk_lines),
                file_type=doc.file_type,
            ))
            chunk_id += 1

        # Move back for overlap
        if i < len(lines):
            overlap_lines = max(1, overlap // 40)  # ~40 chars per line
            i = max(start + 1, i - overlap_lines)

    return chunks


def chunk_all(
    documents: list[DocumentInfo],
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[Chunk]:
    """Chunk all documents and return a flat list."""
    all_chunks: list[Chunk] = []
    global_id = 0
    for doc in documents:
        doc_chunks = chunk_document(doc, chunk_size, overlap)
        for c in doc_chunks:
            c.chunk_id = global_id
            global_id += 1
            all_chunks.append(c)
    return all_chunks
