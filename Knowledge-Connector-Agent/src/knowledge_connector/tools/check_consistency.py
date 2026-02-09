"""check_consistency MCP tool — detect inconsistencies across documents."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from claude_agent_sdk import tool

from knowledge_connector.state import get_documents, get_knowledge_graph


@tool(
    "check_consistency",
    "Detect inconsistencies across indexed documents. Checks for: "
    "version mismatches, conflicting definitions, terminology divergence, "
    "and broken internal references. Optional 'focus' to narrow the check "
    "(e.g., 'versions', 'definitions', 'references', 'terminology').",
    {"focus": str},
)
async def check_consistency(args: dict[str, Any]) -> dict[str, Any]:
    focus = args.get("focus", "all")
    documents = get_documents()
    issues: list[dict[str, Any]] = []

    if focus in ("all", "versions"):
        issues.extend(_check_versions(documents))

    if focus in ("all", "definitions"):
        issues.extend(_check_definitions(documents))

    if focus in ("all", "references"):
        issues.extend(_check_references(documents))

    if focus in ("all", "terminology"):
        issues.extend(_check_terminology(documents))

    result = {
        "total_issues": len(issues),
        "issues": issues,
        "documents_checked": len(documents),
    }

    if not issues:
        result["message"] = "No inconsistencies detected."

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _check_versions(documents: list) -> list[dict[str, Any]]:
    """Find version number mismatches across documents."""
    # Collect all version mentions with context
    version_pattern = re.compile(r'(?:version|v|ver\.?)\s*([\d]+\.[\d]+(?:\.[\d]+)?)', re.IGNORECASE)
    named_version = re.compile(r'(\w[\w\s-]{2,30}?)\s+(?:version|v)\s*([\d]+\.[\d]+(?:\.[\d]+)?)', re.IGNORECASE)

    version_mentions: dict[str, list[tuple[str, str, int]]] = defaultdict(list)

    for doc in documents:
        for i, line in enumerate(doc.content.split("\n")):
            for match in named_version.finditer(line):
                name = match.group(1).strip().lower()
                ver = match.group(2)
                version_mentions[name].append((doc.filepath, ver, i + 1))

    issues = []
    for name, mentions in version_mentions.items():
        versions_found = set(v for _, v, _ in mentions)
        if len(versions_found) > 1:
            issues.append({
                "type": "version_mismatch",
                "severity": "high",
                "subject": name,
                "versions_found": list(versions_found),
                "locations": [
                    {"file": fp, "version": ver, "line": line}
                    for fp, ver, line in mentions
                ],
            })

    return issues


def _check_definitions(documents: list) -> list[dict[str, Any]]:
    """Find the same term defined differently in multiple places."""
    # Look for definition patterns
    def_patterns = [
        re.compile(r'^\*\*(\w[\w\s]+?)\*\*\s*[-:—]\s*(.{10,200})', re.MULTILINE),
        re.compile(r'^#+\s+(.{3,50})\s*$', re.MULTILINE),
    ]

    definitions: dict[str, list[tuple[str, str, int]]] = defaultdict(list)

    for doc in documents:
        if doc.file_type != "markdown":
            continue
        for pattern in def_patterns:
            for match in pattern.finditer(doc.content):
                term = match.group(1).strip().lower()
                context = match.group(0)[:150]
                line = doc.content[:match.start()].count("\n") + 1
                definitions[term].append((doc.filepath, context, line))

    issues = []
    for term, defs in definitions.items():
        if len(defs) > 1:
            # Only flag if defined in different files
            files = set(fp for fp, _, _ in defs)
            if len(files) > 1:
                issues.append({
                    "type": "duplicate_definition",
                    "severity": "medium",
                    "term": term,
                    "defined_in": [
                        {"file": fp, "line": line, "context": ctx}
                        for fp, ctx, line in defs
                    ],
                })

    return issues


def _check_references(documents: list) -> list[dict[str, Any]]:
    """Find broken internal file references."""
    # Look for markdown links and file references
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    file_ref_pattern = re.compile(r'`([^`]*\.\w{1,5})`')

    known_files = {doc.filepath for doc in documents}
    issues = []

    for doc in documents:
        if doc.file_type != "markdown":
            continue

        for i, line in enumerate(doc.content.split("\n")):
            # Check markdown links
            for match in link_pattern.finditer(line):
                target = match.group(2)
                # Skip external URLs and anchors
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                # Normalize path
                clean = target.split("#")[0].split("?")[0]
                if clean and clean not in known_files:
                    # Check with common path adjustments
                    variants = [clean, clean.lstrip("./"), f"./{clean}"]
                    if not any(v in known_files for v in variants):
                        issues.append({
                            "type": "broken_reference",
                            "severity": "medium",
                            "file": doc.filepath,
                            "line": i + 1,
                            "target": target,
                            "context": line.strip()[:120],
                        })

    return issues


def _check_terminology(documents: list) -> list[dict[str, Any]]:
    """Find inconsistent terminology (same concept, different names)."""
    # Common equivalences to check
    term_groups = [
        ({"api", "endpoint", "route"}, "API terminology"),
        ({"user", "account", "profile"}, "user terminology"),
        ({"database", "db", "datastore", "data store"}, "database terminology"),
        ({"config", "configuration", "settings", "preferences"}, "configuration terminology"),
        ({"auth", "authentication", "login", "sign-in", "signin"}, "auth terminology"),
    ]

    issues = []

    for terms, group_name in term_groups:
        term_usage: dict[str, set[str]] = defaultdict(set)  # term -> files using it

        for doc in documents:
            content_lower = doc.content.lower()
            for term in terms:
                if re.search(r'\b' + re.escape(term) + r'\b', content_lower):
                    term_usage[term].add(doc.filepath)

        # Flag if different terms from the same group appear in different docs
        used_terms = {t for t, files in term_usage.items() if files}
        if len(used_terms) > 1:
            issues.append({
                "type": "terminology_divergence",
                "severity": "low",
                "group": group_name,
                "terms_used": {
                    term: list(files)
                    for term, files in term_usage.items() if files
                },
                "suggestion": f"Consider standardizing on one term for {group_name}.",
            })

    return issues
