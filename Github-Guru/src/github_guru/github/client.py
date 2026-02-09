"""GitHub API client wrapping PyGithub."""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Any

from github import Auth, Github


class GitHubClient:
    """Thin wrapper around PyGithub for repo metadata and cloning."""

    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if self.token:
            auth = Auth.Token(self.token)
            self.gh = Github(auth=auth)
        else:
            self.gh = Github()

    def get_repo_metadata(self, owner: str, repo: str) -> dict[str, Any]:
        """Get repository metadata."""
        r = self.gh.get_repo(f"{owner}/{repo}")
        return {
            "name": r.name,
            "full_name": r.full_name,
            "description": r.description,
            "language": r.language,
            "stars": r.stargazers_count,
            "forks": r.forks_count,
            "open_issues": r.open_issues_count,
            "default_branch": r.default_branch,
            "created_at": str(r.created_at),
            "updated_at": str(r.updated_at),
            "topics": r.get_topics(),
        }

    def get_recent_commits(self, owner: str, repo: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent commits."""
        r = self.gh.get_repo(f"{owner}/{repo}")
        commits = []
        for c in r.get_commits()[:limit]:
            commits.append({
                "sha": c.sha[:8],
                "message": c.commit.message.split("\n")[0],
                "author": c.commit.author.name if c.commit.author else "unknown",
                "date": str(c.commit.author.date) if c.commit.author else "",
            })
        return commits

    def get_issues(self, owner: str, repo: str, state: str = "open", limit: int = 10) -> list[dict[str, Any]]:
        """Get repository issues."""
        r = self.gh.get_repo(f"{owner}/{repo}")
        issues = []
        for issue in r.get_issues(state=state)[:limit]:
            issues.append({
                "number": issue.number,
                "title": issue.title,
                "state": issue.state,
                "author": issue.user.login if issue.user else "unknown",
                "labels": [l.name for l in issue.labels],
                "created_at": str(issue.created_at),
            })
        return issues

    @staticmethod
    def clone_repo(url: str, target_dir: str | None = None) -> str:
        """Clone a repository using git subprocess."""
        if target_dir is None:
            target_dir = tempfile.mkdtemp(prefix="github-guru-")
        subprocess.run(
            ["git", "clone", "--depth", "1", url, target_dir],
            check=True,
            capture_output=True,
            text=True,
        )
        return target_dir
