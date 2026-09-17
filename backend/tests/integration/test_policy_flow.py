"""
Integration tests for Policy Management API endpoints.
"""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_policy_repository
from app.infrastructure.database.repositories.policy_repository import PolicyRepository
from app.main import app
from tests.factories import create_test_policy


@pytest.mark.asyncio
async def test_get_policy_not_found(test_client: AsyncClient) -> None:
    """Querying an unregistered repository policy must return 404."""
    mock_repo = AsyncMock(spec=PolicyRepository)
    mock_repo.get_by_repo.return_value = None

    app.dependency_overrides[get_policy_repository] = lambda: mock_repo

    try:
        response = await test_client.get("/api/policies/unknown/repo")
        assert response.status_code == 404
        assert "No policy registered" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_policy_success(test_client: AsyncClient) -> None:
    """Querying an existing policy must return 200 with structured JSON."""
    test_policy = create_test_policy(repo="octocat/Hello-World", version=1)

    mock_repo = AsyncMock(spec=PolicyRepository)
    mock_repo.get_by_repo.return_value = test_policy

    app.dependency_overrides[get_policy_repository] = lambda: mock_repo

    try:
        response = await test_client.get("/api/policies/octocat/Hello-World")
        assert response.status_code == 200
        data = response.json()
        assert data["repo"] == "octocat/Hello-World"
        assert data["version"] == 1
        assert "github.read_file" in data["parsed_content"]["capabilities"]["allow"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_validate_policy_endpoint(test_client: AsyncClient) -> None:
    """POST /api/policies/validate dry-run endpoint must validate syntax without saving."""
    valid_yaml = """
version: 1
capabilities:
  allow: ["github.read_file"]
  approval: []
  deny: []
filesystem:
  read: ["**/*"]
  write: []
commands:
  allow: []
  deny: []
network:
  allowed_domains: []
"""
    response = await test_client.post(
        "/api/policies/validate",
        json={"yaml_content": valid_yaml},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["rego_data_preview"] is not None


@pytest.mark.asyncio
async def test_validate_policy_endpoint_invalid_yaml(test_client: AsyncClient) -> None:
    """POST /api/policies/validate must catch invalid syntax and report errors."""
    bad_yaml = "capabilities: [unclosed list"
    response = await test_client.post(
        "/api/policies/validate",
        json={"yaml_content": bad_yaml},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0
