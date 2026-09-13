"""
Pydantic schemas for GitHub webhook payloads and API responses.
"""

from pydantic import BaseModel, ConfigDict, Field


class GitHubUser(BaseModel):
    """GitHub user summary."""

    model_config = ConfigDict(extra="ignore")

    login: str
    id: int = 0


class GitHubRepo(BaseModel):
    """Target repository information."""

    model_config = ConfigDict(extra="ignore")

    id: int = 0
    name: str
    full_name: str = Field(..., description="Full name in owner/repo format")
    private: bool = False


class GitHubCommitRef(BaseModel):
    """Git commit reference (head or base of a PR)."""

    model_config = ConfigDict(extra="ignore")

    sha: str
    ref: str


class GitHubPullRequest(BaseModel):
    """Pull request object from webhook payload."""

    model_config = ConfigDict(extra="ignore")

    id: int = 0
    number: int
    title: str = ""
    state: str = "open"
    head: GitHubCommitRef
    base: GitHubCommitRef


class GitHubInstallation(BaseModel):
    """GitHub App installation identifier."""

    model_config = ConfigDict(extra="ignore")

    id: int = 0


class GitHubWebhookPayload(BaseModel):
    """
    Typed representation of incoming GitHub webhook event payload.
    Supports pull_request, check_suite, ping, and other webhook events.
    """

    model_config = ConfigDict(extra="ignore")

    action: str = ""
    number: int | None = None
    pull_request: GitHubPullRequest | None = None
    repository: GitHubRepo | None = None
    installation: GitHubInstallation | None = None
    sender: GitHubUser | None = None

    @property
    def pr_number(self) -> int | None:
        """Extract PR number whether at top-level or inside pull_request object."""
        if self.number is not None:
            return self.number
        if self.pull_request is not None:
            return self.pull_request.number
        return None

    @property
    def head_sha(self) -> str | None:
        """Extract head commit SHA if pull request payload."""
        if self.pull_request is not None:
            return self.pull_request.head.sha
        return None
