"""get_git_info MCP tool — get git metadata via subprocess."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from claude_agent_sdk import tool

from github_guru.state import get_repo_root


@tool(
    "get_git_info",
    "Get git information for the repository. "
    "Types: 'commits' (recent commits), 'contributors' (top contributors), "
    "'branches' (all branches), 'file_history' (history for a specific file). "
    "Optional 'limit' for number of results.",
    {"info_type": str, "filepath": str, "limit": int},
)
async def get_git_info(args: dict[str, Any]) -> dict[str, Any]:
    repo_root = get_repo_root()
    info_type = args.get("info_type", "commits")
    filepath = args.get("filepath")
    limit = args.get("limit", 20)

    try:
        if info_type == "commits":
            result = _get_commits(repo_root, limit, filepath)
        elif info_type == "contributors":
            result = _get_contributors(repo_root, limit)
        elif info_type == "branches":
            result = _get_branches(repo_root)
        elif info_type == "file_history":
            if not filepath:
                return _error("filepath required for 'file_history'")
            result = _get_file_history(repo_root, filepath, limit)
        else:
            return _error(f"Unknown info_type: {info_type}")
    except subprocess.CalledProcessError as e:
        return _error(f"Git error: {e.stderr}")
    except FileNotFoundError:
        return _error("Git not found. Ensure git is installed.")

    return {
        "content": [{
            "type": "text",
            "text": json.dumps(result, indent=2),
        }]
    }


def _run_git(repo_root: str, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", repo_root] + args,
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _get_commits(repo_root: str, limit: int, filepath: str | None = None) -> dict:
    cmd = ["log", f"--max-count={limit}", "--format=%H|%an|%ae|%ad|%s", "--date=iso"]
    if filepath:
        cmd.extend(["--", filepath])
    output = _run_git(repo_root, cmd)
    if not output:
        return {"commits": [], "count": 0}

    commits = []
    for line in output.split("\n"):
        parts = line.split("|", 4)
        if len(parts) == 5:
            commits.append({
                "hash": parts[0][:8],
                "author": parts[1],
                "email": parts[2],
                "date": parts[3],
                "message": parts[4],
            })
    return {"commits": commits, "count": len(commits)}


def _get_contributors(repo_root: str, limit: int) -> dict:
    output = _run_git(repo_root, ["shortlog", "-sne", "HEAD"])
    if not output:
        return {"contributors": [], "count": 0}

    contributors = []
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Format: "  123\tAuthor Name <email>"
        parts = line.split("\t", 1)
        if len(parts) == 2:
            count = parts[0].strip()
            name_email = parts[1].strip()
            contributors.append({"commits": int(count), "author": name_email})

    contributors.sort(key=lambda x: x["commits"], reverse=True)
    return {"contributors": contributors[:limit], "count": len(contributors)}


def _get_branches(repo_root: str) -> dict:
    output = _run_git(repo_root, ["branch", "-a", "--format=%(refname:short)|%(objectname:short)|%(upstream:short)"])
    if not output:
        return {"branches": [], "count": 0}

    branches = []
    for line in output.split("\n"):
        parts = line.split("|")
        branches.append({
            "name": parts[0] if parts else "",
            "commit": parts[1] if len(parts) > 1 else "",
            "upstream": parts[2] if len(parts) > 2 else "",
        })
    return {"branches": branches, "count": len(branches)}


def _get_file_history(repo_root: str, filepath: str, limit: int) -> dict:
    output = _run_git(repo_root, [
        "log", f"--max-count={limit}", "--format=%H|%an|%ad|%s",
        "--date=iso", "--", filepath,
    ])
    if not output:
        return {"file": filepath, "history": [], "count": 0}

    history = []
    for line in output.split("\n"):
        parts = line.split("|", 3)
        if len(parts) == 4:
            history.append({
                "hash": parts[0][:8],
                "author": parts[1],
                "date": parts[2],
                "message": parts[3],
            })
    return {"file": filepath, "history": history, "count": len(history)}


def _error(msg: str) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": msg}],
        "is_error": True,
    }
