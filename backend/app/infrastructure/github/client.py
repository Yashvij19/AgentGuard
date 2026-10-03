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
        self._installation_tokens: dict[str, tuple[str, float]] = {}

    async def _get_headers(
        self,
        accept: str = "application/vnd.github.v3+json",
        repo: str | None = None,
    ) -> dict[str, str]:
        """Construct standard GitHub API headers with authorization."""
        headers = {
            "Accept": accept,
            "User-Agent": "AgentGuard-Bot/1.0",
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.app_id and self.private_key:
            if repo:
                try:
                    token = await self._get_or_create_installation_token(repo)
                    headers["Authorization"] = f"Bearer {token}"
                    return headers
                except Exception:
                    pass
            jwt_token = self._generate_jwt()
            headers["Authorization"] = f"Bearer {jwt_token}"

        return headers

    async def _get_or_create_installation_token(self, repo: str) -> str:
        """Exchange GitHub App JWT for a scoped Installation Access Token."""
        now = time.time()
        cached = self._installation_tokens.get(repo)
        if cached and cached[1] > now + 60:
            return cached[0]

        jwt_token = self._generate_jwt()
        jwt_headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {jwt_token}",
            "User-Agent": "AgentGuard-Bot/1.0",
        }

        # 1. Fetch installation ID for this repo
        resp = await self._client.get(f"/repos/{repo}/installation", headers=jwt_headers)
        resp.raise_for_status()
        installation_id = resp.json()["id"]

        # 2. Exchange for installation access token
        token_resp = await self._client.post(
            f"/app/installations/{installation_id}/access_tokens",
            headers=jwt_headers,
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        token = str(token_data["token"])
        token_perms = token_data.get("permissions", {})

        # If token does not have contents: write, invalidate immediately and warn
        if token_perms.get("contents") != "write":
            # Don't cache stale token lacking contents write permission
            self._installation_tokens.pop(repo, None)
        else:
            self._installation_tokens[repo] = (token, now + 3300)

        return token

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
        raw_key = self.private_key.strip()
        if not raw_key.startswith("-----BEGIN"):
            raise ValueError(
                f"GitHub private key is invalid. Expected PEM header '-----BEGIN ...', but received: '{raw_key[:40]}...'. "
                "If using a file path, ensure the file is mounted with -v $(pwd)/github_key.pem:/app/github_key.pem:ro."
            )
        token = jwt.encode(payload, raw_key, algorithm="RS256")
        return token if isinstance(token, str) else token.decode("utf-8")

    async def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """Fetch unified git diff for a pull request."""
        headers = await self._get_headers(accept="application/vnd.github.v3.diff", repo=repo)
        response = await self._client.get(f"/repos/{repo}/pulls/{pr_number}", headers=headers)
        response.raise_for_status()
        return response.text

    async def get_pr_files(self, repo: str, pr_number: int) -> list[str]:
        """Fetch list of changed file paths in a pull request."""
        headers = await self._get_headers(repo=repo)
        response = await self._client.get(f"/repos/{repo}/pulls/{pr_number}/files", headers=headers)
        response.raise_for_status()
        data: list[dict[str, Any]] = response.json()
        return [item["filename"] for item in data if "filename" in item]

    async def get_file_content(self, repo: str, file_path: str, ref: str) -> str:
        """Fetch raw content of a repository file at a specific git ref/SHA."""
        headers = await self._get_headers(accept="application/vnd.github.v3.raw", repo=repo)
        response = await self._client.get(
            f"/repos/{repo}/contents/{file_path}",
            params={"ref": ref},
            headers=headers,
        )
        response.raise_for_status()
        return response.text

    async def post_comment(self, repo: str, pr_number: int, body: str) -> int:
        """Post a comment to a PR (issue comment endpoint). Returns the comment ID."""
        headers = await self._get_headers(repo=repo)
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
        headers = await self._get_headers(repo=repo)
        response = await self._client.get(f"/repos/{repo}/pulls/{pr_number}", headers=headers)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return str(data["head"]["sha"])

    async def get_pr(self, repo: str, pr_number: int) -> dict[str, Any]:
        """Fetch full metadata for a pull request."""
        headers = await self._get_headers(repo=repo)
        response = await self._client.get(f"/repos/{repo}/pulls/{pr_number}", headers=headers)
        response.raise_for_status()
        return response.json()

    async def create_or_update_file(
        self,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> dict[str, Any]:
        """
        Create or update a file in the target repository using the GitHub Contents API.
        Automatically base64 encodes the provided content.
        """
        import base64

        headers = await self._get_headers(repo=repo)
        payload: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        try:
            response = await self._client.put(
                f"/repos/{repo}/contents/{path}",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            # Force refresh of token on next attempt
            self._installation_tokens.pop(repo, None)
            raise

    async def create_commit_status(
        self,
        repo: str,
        sha: str,
        state: str,
        description: str,
        context: str = "AgentGuard/governance",
        target_url: str | None = None,
    ) -> None:
        """
        Publish a commit status check (pending, success, failure, error) to GitHub.
        Requires 'Commit statuses: Read and write' permission on the GitHub App.
        """
        headers = await self._get_headers(repo=repo)
        payload: dict[str, Any] = {
            "state": state,
            "description": description[:140],
            "context": context,
        }
        if target_url:
            payload["target_url"] = target_url

        try:
            response = await self._client.post(
                f"/repos/{repo}/statuses/{sha}",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        except Exception:
            # If the GitHub App lacks status permissions, do not crash the workflow
            pass

    async def aclose(self) -> None:
        """Gracefully close the underlying HTTP client session."""
        await self._client.aclose()

