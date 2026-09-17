"""
Async HTTP client for Open Policy Agent (OPA) REST API.
"""

from typing import Any

import httpx
import structlog

from app.domain.exceptions import OPAEvaluationError

logger = structlog.get_logger(__name__)


class OPAClient:
    """
    Client for interacting with OPA sidecar or cluster endpoints.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8181",
        timeout_seconds: float = 3.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def health_check(self) -> bool:
        """Probe OPA health check endpoint."""
        url = f"{self._base_url}/health"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception as err:
            logger.warning("opa_health_check_failed", error=str(err), url=url)
            return False

    async def upload_data(self, path: str, data: dict[str, Any]) -> None:
        """
        Upload JSON data to OPA document store (e.g. path='policy').
        Target endpoint: PUT /v1/data/{path}
        """
        clean_path = path.strip("/")
        url = f"{self._base_url}/v1/data/{clean_path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.put(url, json=data)
                if response.status_code not in (200, 204):
                    raise OPAEvaluationError(
                        f"OPA data upload returned status {response.status_code}: {response.text}",
                        details={"status_code": response.status_code, "body": response.text},
                    )
        except httpx.RequestError as err:
            raise OPAEvaluationError(
                f"Failed to communicate with OPA at {url}: {err}",
                details={"error": str(err)},
            ) from err

    async def query_policy(
        self,
        package_path: str,
        input_document: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Query an OPA rule package with an input document.
        Target endpoint: POST /v1/data/{package_path}
        """
        clean_path = package_path.replace(".", "/").strip("/")
        url = f"{self._base_url}/v1/data/{clean_path}"
        payload = {"input": input_document}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    raise OPAEvaluationError(
                        f"OPA query failed with status {response.status_code}: {response.text}",
                        details={"status_code": response.status_code, "body": response.text},
                    )
                data = response.json()
                result: dict[str, Any] = data.get("result", {})
                return result
        except httpx.RequestError as err:
            raise OPAEvaluationError(
                f"OPA query network failure at {url}: {err}",
                details={"error": str(err)},
            ) from err
