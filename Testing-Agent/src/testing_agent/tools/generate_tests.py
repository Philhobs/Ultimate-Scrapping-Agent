"""generate_tests MCP tool — generate test cases for source files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from testing_agent.state import get_profile, get_output_dir


@tool(
    "generate_tests",
    "Generate test cases for a source file or specific functions. "
    "Creates test file with stubs for all detected functions. "
    "Provide 'file' (source file to test), optional 'functions' (list of names), "
    "optional 'test_content' (if you want to write specific test code).",
    {"file": str, "functions": list, "test_content": str},
)
async def generate_tests(args: dict[str, Any]) -> dict[str, Any]:
    try:
        profile = get_profile()
    except RuntimeError:
        return {
            "content": [{"type": "text", "text": "Error: Run analyze_codebase first."}],
            "is_error": True,
        }

    source_file = args.get("file", "")
    target_functions = args.get("functions", [])
    custom_content = args.get("test_content")

    if not source_file:
        return {
            "content": [{"type": "text", "text": "Error: Provide 'file' parameter."}],
            "is_error": True,
        }

    # Get functions from this file
    file_functions = [f for f in profile.functions if f.file == source_file]
    if target_functions:
        file_functions = [f for f in file_functions if f.name in target_functions]

    # If custom content provided, write it directly
    if custom_content:
        test_filename = _make_test_filename(source_file, profile.language)
        out = Path(get_output_dir())
        out.mkdir(parents=True, exist_ok=True)
        test_path = out / test_filename
        test_path.write_text(custom_content)
        return {"content": [{"type": "text", "text": json.dumps({
            "test_file": test_filename,
            "output_dir": str(out),
            "type": "custom",
        }, indent=2)}]}

    # Generate test template based on language
    if profile.language == "python":
        content = _python_tests(source_file, file_functions, profile)
    elif profile.language in ("javascript", "typescript"):
        content = _js_tests(source_file, file_functions, profile)
    elif profile.language == "go":
        content = _go_tests(source_file, file_functions, profile)
    else:
        content = _python_tests(source_file, file_functions, profile)

    test_filename = _make_test_filename(source_file, profile.language)
    out = Path(get_output_dir())
    out.mkdir(parents=True, exist_ok=True)
    test_path = out / test_filename
    test_path.write_text(content)

    result = {
        "test_file": test_filename,
        "output_dir": str(out),
        "functions_covered": [f.name for f in file_functions],
        "total_test_stubs": len(file_functions),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _make_test_filename(source_file: str, language: str) -> str:
    """Generate test filename from source filename."""
    name = Path(source_file).stem
    if language == "python":
        return f"test_{name}.py"
    elif language in ("javascript", "typescript"):
        ext = Path(source_file).suffix
        return f"{name}.test{ext}"
    elif language == "go":
        return f"{name}_test.go"
    return f"test_{name}.py"


def _python_tests(source_file: str, functions: list, profile) -> str:
    """Generate pytest test template."""
    module_path = source_file.replace("/", ".").replace(".py", "")
    lines = [
        f'"""Tests for {source_file}."""',
        "",
        "import pytest",
        "",
        f"# Source: {source_file}",
        f"# Import: from {module_path} import ...",
        "",
        "",
    ]

    for fn in functions:
        params_str = ", ".join(fn.params) if fn.params else ""
        test_name = f"test_{fn.name}"
        if fn.class_name:
            test_name = f"test_{fn.class_name.lower()}_{fn.name}"

        lines.append(f"class Test{fn.class_name or fn.name.title().replace('_', '')}:")
        lines.append(f'    """Tests for {fn.class_name + "." if fn.class_name else ""}{fn.name}."""')
        lines.append("")

        # Happy path test
        lines.append(f"    def {test_name}_happy_path(self):")
        if fn.docstring:
            lines.append(f'        """{fn.docstring[:100]}."""')
        lines.append(f"        # Arrange")
        for p in fn.params:
            lines.append(f"        {p} = None  # TODO: provide test value")
        lines.append(f"        # Act")
        lines.append(f"        # result = {fn.name}({params_str})")
        lines.append(f"        # Assert")
        lines.append(f"        # assert result == expected")
        lines.append(f"        pass  # TODO: implement")
        lines.append("")

        # Edge case test
        lines.append(f"    def {test_name}_edge_case(self):")
        lines.append(f'        """Test edge cases: empty input, None, boundary values."""')
        lines.append(f"        pass  # TODO: implement")
        lines.append("")

        # Error case test
        lines.append(f"    def {test_name}_error_handling(self):")
        lines.append(f'        """Test error handling and invalid inputs."""')
        lines.append(f"        # with pytest.raises(ValueError):")
        lines.append(f"        #     {fn.name}(invalid_input)")
        lines.append(f"        pass  # TODO: implement")
        lines.append("")
        lines.append("")

    return "\n".join(lines)


def _js_tests(source_file: str, functions: list, profile) -> str:
    """Generate Jest test template."""
    module = Path(source_file).stem
    ext = Path(source_file).suffix
    lines = [
        f"// Tests for {source_file}",
        f"// const {{ ... }} = require('./{module}');",
        "",
    ]

    for fn in functions:
        params_str = ", ".join(fn.params) if fn.params else ""
        lines.append(f"describe('{fn.name}', () => {{")

        # Happy path
        lines.append(f"  it('should handle valid input correctly', () => {{")
        lines.append(f"    // Arrange")
        for p in fn.params:
            lines.append(f"    // const {p} = ;")
        lines.append(f"    // Act")
        lines.append(f"    // const result = {fn.name}({params_str});")
        lines.append(f"    // Assert")
        lines.append(f"    // expect(result).toBe(expected);")
        lines.append(f"  }});")
        lines.append("")

        # Edge case
        lines.append(f"  it('should handle edge cases', () => {{")
        lines.append(f"    // Test with null, undefined, empty values")
        lines.append(f"  }});")
        lines.append("")

        # Error case
        lines.append(f"  it('should throw on invalid input', () => {{")
        lines.append(f"    // expect(() => {fn.name}(invalid)).toThrow();")
        lines.append(f"  }});")

        lines.append(f"}});")
        lines.append("")

    return "\n".join(lines)


def _go_tests(source_file: str, functions: list, profile) -> str:
    """Generate Go test template."""
    lines = [
        f"// Tests for {source_file}",
        "",
        'package main',
        '',
        'import (',
        '\t"testing"',
        ')',
        "",
    ]

    for fn in functions:
        name = fn.name
        if fn.class_name:
            name = f"{fn.class_name}_{fn.name}"

        lines.append(f"func Test{name}(t *testing.T) {{")
        lines.append(f"\tt.Run(\"happy path\", func(t *testing.T) {{")
        lines.append(f"\t\t// Arrange")
        lines.append(f"\t\t// Act")
        lines.append(f"\t\t// Assert")
        lines.append(f"\t\tt.Skip(\"TODO: implement\")")
        lines.append(f"\t}})")
        lines.append("")
        lines.append(f"\tt.Run(\"edge case\", func(t *testing.T) {{")
        lines.append(f"\t\tt.Skip(\"TODO: implement\")")
        lines.append(f"\t}})")
        lines.append(f"}}")
        lines.append("")

    return "\n".join(lines)
