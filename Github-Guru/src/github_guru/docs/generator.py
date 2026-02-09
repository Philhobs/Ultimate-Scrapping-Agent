"""Documentation generation prompts and orchestration."""

from __future__ import annotations

DOC_PROMPTS: dict[str, str] = {
    "overview": (
        "Generate a comprehensive project overview document in Markdown. "
        "Use the available tools to analyze the repository. Include:\n"
        "1. Project name and description\n"
        "2. Technology stack and key dependencies\n"
        "3. Project structure (directory tree)\n"
        "4. Getting started / installation instructions\n"
        "5. High-level description of what the project does\n\n"
        "Use query_structure with 'overview' first, then list_files to understand the layout. "
        "Output ONLY the Markdown document, no preamble."
    ),
    "architecture": (
        "Generate an architecture document in Markdown. "
        "Use the available tools to deeply analyze the codebase. Include:\n"
        "1. System architecture overview\n"
        "2. Component diagram (as ASCII/text art)\n"
        "3. Data flow description\n"
        "4. Key design patterns used\n"
        "5. Module responsibilities\n"
        "6. Inter-module dependencies (use query_graph)\n\n"
        "Use query_structure, query_graph, and semantic_search to gather information. "
        "Output ONLY the Markdown document."
    ),
    "files": (
        "Generate a file reference document in Markdown. "
        "For each file in the project, provide:\n"
        "1. File path\n"
        "2. Purpose/description\n"
        "3. Key classes and functions defined\n"
        "4. Dependencies (imports)\n\n"
        "Use list_files, query_structure with 'file_summary' for each key file. "
        "Focus on source code files, skip config/data files. "
        "Output ONLY the Markdown document."
    ),
    "api": (
        "Generate an API reference document in Markdown. "
        "Document all public classes and functions with:\n"
        "1. Class/function name and signature\n"
        "2. Parameters with types and descriptions\n"
        "3. Return values\n"
        "4. Usage examples (inferred from the code)\n"
        "5. Related classes/functions\n\n"
        "Use query_structure with 'classes' and 'functions', then read_file for details. "
        "Output ONLY the Markdown document."
    ),
}
