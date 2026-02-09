"""Build dependency graph from codebase analysis."""

from __future__ import annotations

from pathlib import PurePosixPath

from github_guru.models.codebase import CodebaseAnalysis, FileInfo, Language
from github_guru.models.graph import (
    DependencyGraph,
    GraphEdge,
    GraphNode,
    NodeType,
    RelationType,
)


def _file_node_id(filepath: str) -> str:
    return f"file:{filepath}"


def _class_node_id(filepath: str, class_name: str) -> str:
    return f"class:{filepath}:{class_name}"


def _func_node_id(filepath: str, func_name: str, class_name: str | None = None) -> str:
    if class_name:
        return f"method:{filepath}:{class_name}.{func_name}"
    return f"func:{filepath}:{func_name}"


def _resolve_import_to_file(
    module: str,
    level: int,
    source_filepath: str,
    file_index: dict[str, str],
) -> str | None:
    """Try to resolve an import module string to a file path in the repo.

    file_index maps module-style paths (e.g. 'github_guru.models.codebase')
    to actual filepaths.
    """
    if level > 0:
        # Relative import — resolve from source file's package
        parts = PurePosixPath(source_filepath).parts
        # Go up `level` directories from the source file's parent
        package_parts = list(parts[:-1])  # drop filename
        for _ in range(level - 1):
            if package_parts:
                package_parts.pop()
        if module:
            package_parts.extend(module.split("."))
        module_path = ".".join(package_parts)
    else:
        module_path = module

    # Try as package (directory/__init__.py) or module (.py file)
    if module_path in file_index:
        return file_index[module_path]

    return None


def _build_file_index(analysis: CodebaseAnalysis) -> dict[str, str]:
    """Build a mapping from dotted module paths to file paths.

    For example:
        'src.github_guru.models.codebase' -> 'src/github_guru/models/codebase.py'
        'src.github_guru.models' -> 'src/github_guru/models/__init__.py'
    """
    index: dict[str, str] = {}
    for fi in analysis.files:
        if fi.language != Language.PYTHON:
            continue
        path = PurePosixPath(fi.filepath)
        # Module path: replace / with . and strip .py
        if path.name == "__init__.py":
            module_parts = list(path.parts[:-1])
        else:
            module_parts = list(path.parts[:-1]) + [path.stem]
        dotted = ".".join(module_parts)
        index[dotted] = fi.filepath
    return index


def build_dependency_graph(analysis: CodebaseAnalysis) -> DependencyGraph:
    """Build a dependency graph from the codebase analysis."""
    graph = DependencyGraph()
    file_index = _build_file_index(analysis)

    for fi in analysis.files:
        # Add file node
        file_id = _file_node_id(fi.filepath)
        graph.add_node(GraphNode(
            id=file_id,
            node_type=NodeType.FILE,
            name=fi.filepath,
            filepath=fi.filepath,
            metadata={"language": fi.language.value, "lines": fi.line_count},
        ))

        # Add class nodes
        for cls in fi.classes:
            cls_id = _class_node_id(fi.filepath, cls.name)
            graph.add_node(GraphNode(
                id=cls_id,
                node_type=NodeType.CLASS,
                name=cls.name,
                filepath=fi.filepath,
                metadata={"bases": cls.bases, "line_start": cls.line_start},
            ))
            # Containment edge: file -> class
            graph.add_edge(GraphEdge(
                source=file_id,
                target=cls_id,
                relation=RelationType.CONTAINS,
            ))

            # Inheritance edges
            for base in cls.bases:
                _add_inheritance_edge(graph, cls_id, base, analysis)

            # Add method nodes
            for method in cls.methods:
                method_id = _func_node_id(fi.filepath, method.name, cls.name)
                graph.add_node(GraphNode(
                    id=method_id,
                    node_type=NodeType.FUNCTION,
                    name=f"{cls.name}.{method.name}",
                    filepath=fi.filepath,
                    metadata={"is_method": True, "line_start": method.line_start},
                ))
                graph.add_edge(GraphEdge(
                    source=cls_id,
                    target=method_id,
                    relation=RelationType.CONTAINS,
                ))

        # Add standalone function nodes
        for func in fi.functions:
            func_id = _func_node_id(fi.filepath, func.name)
            graph.add_node(GraphNode(
                id=func_id,
                node_type=NodeType.FUNCTION,
                name=func.name,
                filepath=fi.filepath,
                metadata={"line_start": func.line_start},
            ))
            graph.add_edge(GraphEdge(
                source=file_id,
                target=func_id,
                relation=RelationType.CONTAINS,
            ))

        # Import edges
        _add_import_edges(graph, fi, file_index)

    return graph


def _add_import_edges(
    graph: DependencyGraph,
    fi: FileInfo,
    file_index: dict[str, str],
) -> None:
    """Add import edges from a file to its imported modules."""
    file_id = _file_node_id(fi.filepath)
    for imp in fi.imports:
        target_path = _resolve_import_to_file(
            imp.module, imp.level, fi.filepath, file_index
        )
        if target_path:
            target_id = _file_node_id(target_path)
            if target_id in graph.nodes:
                graph.add_edge(GraphEdge(
                    source=file_id,
                    target=target_id,
                    relation=RelationType.IMPORTS,
                    metadata={"names": imp.names},
                ))


def _add_inheritance_edge(
    graph: DependencyGraph,
    cls_id: str,
    base_name: str,
    analysis: CodebaseAnalysis,
) -> None:
    """Try to find the base class node and add an inheritance edge."""
    # Simple name resolution: search all classes for matching name
    simple_name = base_name.split(".")[-1]
    for fi in analysis.files:
        for cls in fi.classes:
            if cls.name == simple_name:
                target_id = _class_node_id(fi.filepath, cls.name)
                if target_id in graph.nodes:
                    graph.add_edge(GraphEdge(
                        source=cls_id,
                        target=target_id,
                        relation=RelationType.INHERITS,
                    ))
                return
