"""
Protocol defining the GitHub API integration interface.
"""

from typing import Any, Protocol, runtime_checkable



@runtime_checkable
class GitHubClient(Protocol):
    """Interface for interacting with the GitHub API."""

    async def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """Fetch the unified git diff of a pull request."""
        ...  # "implementation comes later"

    async def get_pr_files(self, repo: str, pr_number: int) -> list[str]:
        """Fetch list of changed file paths in a pull request."""
        ...

    async def get_file_content(self, repo: str, file_path: str, ref: str) -> str:
        """Fetch raw content of a file at a specific git ref/SHA."""
        ...

    async def post_comment(self, repo: str, pr_number: int, body: str) -> int:
        """Post a comment on a pull request. Returns the comment ID."""
        ...

    async def get_latest_pr_sha(self, repo: str, pr_number: int) -> str:
        """Fetch current head commit SHA of a pull request (for staleness check)."""
        ...

    async def get_pr(self, repo: str, pr_number: int) -> dict[str, Any]:
        """Fetch metadata for a pull request including head branch and commit SHA."""
        ...

    async def create_or_update_file(
        self,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> dict[str, Any]:
        """Commit new or updated file contents directly to a branch."""
        ...

    async def create_commit_status(
        self,
        repo: str,
        sha: str,
        state: str,
        description: str,
        context: str = "AgentGuard/governance",
        target_url: str | None = None,
    ) -> None:
        """Publish a commit status check to GitHub to enforce branch protection."""
        ...
