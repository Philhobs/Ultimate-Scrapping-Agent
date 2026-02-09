"""Repository ingestion — local and remote (GitHub URL)."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".env", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", ".egg-info", ".eggs", ".github-guru",
}

IGNORE_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".o", ".a", ".dylib", ".dll",
    ".exe", ".bin", ".class", ".jar", ".war",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".mp3", ".mp4", ".avi", ".mov", ".wav",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
    ".woff", ".woff2", ".ttf", ".eot",
    ".db", ".sqlite", ".sqlite3",
    ".lock",
}

MAX_FILE_SIZE = 500 * 1024  # 500KB

GITHUB_URL_PATTERN = re.compile(
    r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$"
)


def is_github_url(source: str) -> bool:
    return bool(GITHUB_URL_PATTERN.match(source))


def clone_repo(url: str) -> str:
    """Clone a GitHub repo to a temp directory, return the path."""
    tmp_dir = tempfile.mkdtemp(prefix="github-guru-")
    subprocess.run(
        ["git", "clone", "--depth", "1", url, tmp_dir],
        check=True,
        capture_output=True,
        text=True,
    )
    return tmp_dir


def _should_ignore_dir(name: str) -> bool:
    return name in IGNORE_DIRS or name.startswith(".")


def _should_ignore_file(path: Path) -> bool:
    if path.suffix.lower() in IGNORE_EXTENSIONS:
        return True
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return True
    except OSError:
        return True
    return False


def collect_files(repo_root: str | Path) -> list[str]:
    """Walk the repo and collect eligible file paths (relative to root)."""
    root = Path(repo_root).resolve()
    files: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored directories in-place
        dirnames[:] = [
            d for d in dirnames
            if not _should_ignore_dir(d)
        ]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if not _should_ignore_file(fpath):
                rel = str(fpath.relative_to(root))
                files.append(rel)

    files.sort()
    return files


def ingest_repo(source: str) -> tuple[str, list[str]]:
    """Ingest a repository from a local path or GitHub URL.

    Returns (repo_root, file_list) where file_list contains paths relative to repo_root.
    """
    if is_github_url(source):
        repo_root = clone_repo(source)
    else:
        repo_root = str(Path(source).resolve())
        if not Path(repo_root).is_dir():
            raise ValueError(f"Source path does not exist: {source}")

    file_list = collect_files(repo_root)
    return repo_root, file_list
