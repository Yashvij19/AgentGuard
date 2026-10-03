"""
Pytest configuration and shared async fixtures.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.protocols.github_client import GitHubClient
from app.main import app


@pytest.fixture
def mock_github_client() -> GitHubClient:
    """Mock implementation of the GitHubClient protocol."""
    client = MagicMock(spec=GitHubClient)
    client.get_pr_diff = AsyncMock(
        return_value="diff --git a/app/service.py b/app/service.py\n+def new_feature(): pass"
    )
    client.get_pr_files = AsyncMock(return_value=["app/service.py"])
    client.get_file_content = AsyncMock(return_value="# file content")
    client.post_comment = AsyncMock(return_value=987654)
    client.get_latest_pr_sha = AsyncMock(return_value="6dcb09b5b57875f334f61aebed695e2e4193db5e")
    return client


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock SQLAlchemy AsyncSession for unit tests."""
    session = AsyncMock()
    # Mock advisory lock query returning True (lock successfully acquired)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = True
    mock_result.scalar.return_value = True
    session.execute.return_value = mock_result
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    # Mock nested transaction (savepoint)
    mock_nested = AsyncMock()
    mock_nested.__aenter__.return_value = mock_nested
    mock_nested.__aexit__.return_value = None
    session.begin_nested.return_value = mock_nested

    return session


@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous HTTP test client bound directly to the FastAPI app."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
