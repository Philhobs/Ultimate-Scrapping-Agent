"""Python AST parser for extracting structural information."""

from __future__ import annotations

import ast
from pathlib import Path

from github_guru.models.codebase import (
    ClassInfo,
    FileInfo,
    FunctionInfo,
    ImportInfo,
    Language,
    ParameterInfo,
    detect_language,
)


class PythonASTVisitor(ast.NodeVisitor):
    """Extract functions, classes, and imports from a Python AST."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.imports: list[ImportInfo] = []
        self.functions: list[FunctionInfo] = []
        self.classes: list[ClassInfo] = []
        self.module_docstring: str | None = None
        self._current_class: str | None = None

    def visit_Module(self, node: ast.Module) -> None:
        self.module_docstring = ast.get_docstring(node)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(ImportInfo(
                module=alias.name,
                names=[],
                alias=alias.asname,
            ))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        names = [alias.name for alias in node.names]
        self.imports.append(ImportInfo(
            module=module,
            names=names,
            is_relative=node.level > 0,
            level=node.level,
        ))

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._extract_function(node, is_async=isinstance(node, ast.AsyncFunctionDef))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._extract_function(node, is_async=True)

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        params = []
        for arg in node.args.args:
            annotation = None
            if arg.annotation:
                annotation = ast.unparse(arg.annotation)
            params.append(ParameterInfo(
                name=arg.arg,
                type_annotation=annotation,
            ))

        # Extract default values
        defaults = node.args.defaults
        if defaults:
            offset = len(params) - len(defaults)
            for i, default in enumerate(defaults):
                params[offset + i].default_value = ast.unparse(default)

        return_type = ast.unparse(node.returns) if node.returns else None
        decorators = [ast.unparse(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)

        # Extract function calls within the body
        calls = _extract_calls(node)

        func_info = FunctionInfo(
            name=node.name,
            filepath=self.filepath,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            parameters=params,
            return_type=return_type,
            decorators=decorators,
            docstring=docstring,
            calls=calls,
            is_method=self._current_class is not None,
            is_async=is_async,
            class_name=self._current_class,
        )

        if self._current_class is not None:
            # Will be added to the class by visit_ClassDef
            self._current_methods.append(func_info)
        else:
            self.functions.append(func_info)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = [ast.unparse(b) for b in node.bases]
        decorators = [ast.unparse(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)

        # Extract class variables
        class_vars = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                class_vars.append(item.target.id)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_vars.append(target.id)

        # Visit methods
        prev_class = self._current_class
        self._current_class = node.name
        self._current_methods: list[FunctionInfo] = []
        self.generic_visit(node)

        class_info = ClassInfo(
            name=node.name,
            filepath=self.filepath,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            bases=bases,
            methods=self._current_methods,
            class_variables=class_vars,
            decorators=decorators,
            docstring=docstring,
        )
        self.classes.append(class_info)
        self._current_class = prev_class


def _extract_calls(node: ast.AST) -> list[str]:
    """Extract function/method call names from an AST subtree."""
    calls: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                calls.append(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)
    return list(dict.fromkeys(calls))  # deduplicate preserving order


def parse_python_file(filepath: str, content: str) -> FileInfo:
    """Parse a Python file and extract structural info."""
    try:
        tree = ast.parse(content, filename=filepath)
    except SyntaxError:
        # Return basic info for unparseable files
        lines = content.count("\n") + 1
        return FileInfo(
            filepath=filepath,
            language=Language.PYTHON,
            size_bytes=len(content.encode()),
            line_count=lines,
        )

    visitor = PythonASTVisitor(filepath)
    visitor.visit(tree)

    lines = content.count("\n") + 1
    return FileInfo(
        filepath=filepath,
        language=Language.PYTHON,
        size_bytes=len(content.encode()),
        line_count=lines,
        imports=visitor.imports,
        functions=visitor.functions,
        classes=visitor.classes,
        docstring=visitor.module_docstring,
    )


def parse_file(filepath: str, content: str) -> FileInfo:
    """Parse a file and extract structural information.

    Full AST parsing for Python files; basic metadata for others.
    """
    language = detect_language(filepath)

    if language == Language.PYTHON:
        return parse_python_file(filepath, content)

    # Basic metadata for non-Python files
    lines = content.count("\n") + 1
    return FileInfo(
        filepath=filepath,
        language=language,
        size_bytes=len(content.encode()),
        line_count=lines,
    )
