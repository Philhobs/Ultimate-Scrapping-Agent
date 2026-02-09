"""query_structure MCP tool — query AST-extracted structural data."""

from __future__ import annotations

import fnmatch
import json
from typing import Any

from claude_agent_sdk import tool

from github_guru.state import get_analysis


@tool(
    "query_structure",
    "Query the structural analysis of the codebase. "
    "Types: 'overview' (repo summary), 'classes' (all classes), "
    "'functions' (all functions), 'imports' (all imports), "
    "'file_summary' (details for a specific file). "
    "Optional 'name_filter' supports wildcards.",
    {"query_type": str, "name_filter": str, "filepath": str},
)
async def query_structure(args: dict[str, Any]) -> dict[str, Any]:
    analysis = get_analysis()
    query_type = args.get("query_type", "overview")
    name_filter = args.get("name_filter")
    filepath = args.get("filepath")

    if query_type == "overview":
        result = _overview(analysis)
    elif query_type == "classes":
        result = _classes(analysis, name_filter)
    elif query_type == "functions":
        result = _functions(analysis, name_filter)
    elif query_type == "imports":
        result = _imports(analysis, filepath)
    elif query_type == "file_summary":
        if not filepath:
            return {
                "content": [{"type": "text", "text": "filepath required for file_summary"}],
                "is_error": True,
            }
        result = _file_summary(analysis, filepath)
    else:
        return {
            "content": [{"type": "text", "text": f"Unknown query_type: {query_type}"}],
            "is_error": True,
        }

    return {
        "content": [{
            "type": "text",
            "text": json.dumps(result, indent=2),
        }]
    }


def _overview(analysis):
    return {
        "repo": analysis.repo.to_dict(),
        "total_files": analysis.total_files,
        "total_lines": analysis.total_lines,
        "languages": analysis.languages,
        "total_classes": sum(len(f.classes) for f in analysis.files),
        "total_functions": sum(
            len(f.functions) + sum(len(c.methods) for c in f.classes)
            for f in analysis.files
        ),
    }


def _classes(analysis, name_filter):
    classes = []
    for fi in analysis.files:
        for cls in fi.classes:
            if name_filter and not fnmatch.fnmatch(cls.name, name_filter):
                continue
            classes.append({
                "name": cls.name,
                "filepath": fi.filepath,
                "bases": cls.bases,
                "methods": [m.name for m in cls.methods],
                "line_start": cls.line_start,
                "docstring": cls.docstring,
            })
    return {"classes": classes, "count": len(classes)}


def _functions(analysis, name_filter):
    functions = []
    for fi in analysis.files:
        for func in fi.functions:
            if name_filter and not fnmatch.fnmatch(func.name, name_filter):
                continue
            functions.append({
                "name": func.name,
                "filepath": fi.filepath,
                "parameters": [p.name for p in func.parameters],
                "return_type": func.return_type,
                "is_async": func.is_async,
                "line_start": func.line_start,
                "docstring": func.docstring,
            })
        for cls in fi.classes:
            for method in cls.methods:
                full_name = f"{cls.name}.{method.name}"
                if name_filter and not fnmatch.fnmatch(full_name, name_filter):
                    continue
                functions.append({
                    "name": full_name,
                    "filepath": fi.filepath,
                    "parameters": [p.name for p in method.parameters],
                    "return_type": method.return_type,
                    "is_async": method.is_async,
                    "line_start": method.line_start,
                    "docstring": method.docstring,
                })
    return {"functions": functions, "count": len(functions)}


def _imports(analysis, filepath):
    imports = []
    for fi in analysis.files:
        if filepath and fi.filepath != filepath:
            continue
        for imp in fi.imports:
            imports.append({
                "filepath": fi.filepath,
                "module": imp.module,
                "names": imp.names,
                "is_relative": imp.is_relative,
            })
    return {"imports": imports, "count": len(imports)}


def _file_summary(analysis, filepath):
    for fi in analysis.files:
        if fi.filepath == filepath:
            return {
                "filepath": fi.filepath,
                "language": fi.language.value,
                "line_count": fi.line_count,
                "size_bytes": fi.size_bytes,
                "docstring": fi.docstring,
                "imports": [i.to_dict() for i in fi.imports],
                "classes": [
                    {"name": c.name, "bases": c.bases, "methods": [m.name for m in c.methods]}
                    for c in fi.classes
                ],
                "functions": [
                    {"name": f.name, "params": [p.name for p in f.parameters]}
                    for f in fi.functions
                ],
            }
    return {"error": f"File not found in analysis: {filepath}"}
