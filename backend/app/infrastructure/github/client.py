"""
HTTP client for GitHub REST API implementing GitHubClient protocol.
"""

import time
from typing import Any

import httpx
import jwt

from app.domain.protocols.github_client import GitHubClient


class AsyncGitHubClient(GitHubClient):
    """
    Asynchronous GitHub API client supporting GitHub App JWT authentication
    and direct Personal Access Token (PAT) authentication for testing.
    """

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        app_id: str | None = None,
        private_key: str | None = None,
        token: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.app_id = app_id
        self.private_key = private_key
        self.token = token
        self._client = http_client or httpx.AsyncClient(base_url=self.BASE_URL, timeout=30.0)

    def _get_headers(self, accept: str = "application/vnd.github.v3+json") -> dict[str, str]:
        """Construct standard GitHub API headers with authorization."""
        headers = {
            "Accept": accept,
            "User-Agent": "AgentGuard-Bot/1.0",
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.app_id and self.private_key:
            jwt_token = self._generate_jwt()
            headers["Authorization"] = f"Bearer {jwt_token}"

        return headers

    def _generate_jwt(self) -> str:
        """Generate a short-lived RS256 JWT for GitHub App authentication."""
        if not self.app_id or not self.private_key:
            raise ValueError("App ID and Private Key are required for GitHub App JWT generation")

        now = int(time.time())
        payload = {
            "iat": now - 60,  # 60 seconds clock drift allowance
            "exp": now + (10 * 60),  # Valid for 10 minutes
            "iss": self.app_id,
        }
        token = jwt.encode(payload, self.private_key, algorithm="RS256")
        return token if isinstance(token, str) else token.decode("utf-8")

    async def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """Fetch unified git diff for a pull request."""
        headers = self._get_headers(accept="application/vnd.github.v3.diff")
        response = await self._client.get(f"/repos/{repo}/pulls/{pr_number}", headers=headers)
        response.raise_for_status()
        return response.text

    async def get_pr_files(self, repo: str, pr_number: int) -> list[str]:
        """Fetch list of changed file paths in a pull request."""
        headers = self._get_headers()
        response = await self._client.get(
            f"/repos/{repo}/pulls/{pr_number}/files", headers=headers
        )
        response.raise_for_status()
        data: list[dict[str, Any]] = response.json()
        return [item["filename"] for item in data if "filename" in item]

    async def get_file_content(self, repo: str, file_path: str, ref: str) -> str:
        """Fetch raw content of a repository file at a specific git ref/SHA."""
        headers = self._get_headers(accept="application/vnd.github.v3.raw")
        response = await self._client.get(
            f"/repos/{repo}/contents/{file_path}",
            params={"ref": ref},
            headers=headers,
        )
        response.raise_for_status()
        return response.text

    async def post_comment(self, repo: str, pr_number: int, body: str) -> int:
        """Post a comment to a PR (issue comment endpoint). Returns the comment ID."""
        headers = self._get_headers()
        response = await self._client.post(
            f"/repos/{repo}/issues/{pr_number}/comments",
            json={"body": body},
            headers=headers,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return int(data["id"])

    async def get_latest_pr_sha(self, repo: str, pr_number: int) -> str:
        """Fetch the current head commit SHA of a PR to verify staleness."""
        headers = self._get_headers()
        response = await self._client.get(f"/repos/{repo}/pulls/{pr_number}", headers=headers)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return str(data["head"]["sha"])

    async def aclose(self) -> None:
        """Gracefully close the underlying HTTP client session."""
        await self._client.aclose()

