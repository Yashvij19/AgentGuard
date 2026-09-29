"""
Unit tests for ToolGateway.
Verifies capability enforcement, action dispatching, sandbox execution, and audit trail logging.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.policy import CapabilityConfig, Policy, PolicyConfig
from app.domain.models.run_event import EventType
from app.domain.protocols.github_client import GitHubClient
from app.domain.protocols.sandbox_runner import SandboxResult, SandboxRunner
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.policy_repository import PolicyRepository
from app.services.tool_gateway import ToolGateway


@pytest.fixture
def mock_github_client() -> AsyncMock:
    client = AsyncMock(spec=GitHubClient)
    client.post_comment = AsyncMock(return_value=999)
    client.get_file_content = AsyncMock(return_value="print('hello world')")
    return client


@pytest.fixture
def mock_sandbox_runner() -> AsyncMock:
    runner = AsyncMock(spec=SandboxRunner)
    runner.run_command = AsyncMock(
        return_value=SandboxResult(
            exit_code=0,
            stdout="1 passed in 0.05s",
            stderr="",
            duration_ms=50,
            timed_out=False,
        )
    )
    return runner


@pytest.fixture
def mock_policy_repo() -> AsyncMock:
    repo = AsyncMock(spec=PolicyRepository)
    config = PolicyConfig(
        version="1.0",
        capabilities=CapabilityConfig(
            allow=["github.read_file", "github.comment_pr", "commands.exec"],
            approval=["github.create_commit"],
            deny=["github.delete_repository"],
        ),
    )
    policy = Policy(
        repo="octocat/Hello-World",
        yaml_content="",
        parsed_content=config,
    )
    repo.get_by_repo = AsyncMock(return_value=policy)
    return repo


@pytest.fixture
def mock_event_repo() -> AsyncMock:
    repo = AsyncMock(spec=EventRepository)
    repo.append = AsyncMock(side_effect=lambda e: e)
    return repo


@pytest.fixture
def tool_gateway(
    mock_github_client: AsyncMock,
    mock_sandbox_runner: AsyncMock,
    mock_policy_repo: AsyncMock,
    mock_event_repo: AsyncMock,
) -> ToolGateway:
    return ToolGateway(
        github_client=mock_github_client,
        sandbox_runner=mock_sandbox_runner,
        policy_repository=mock_policy_repo,
        event_repository=mock_event_repo,
    )


@pytest.mark.asyncio
async def test_tool_gateway_denies_forbidden_capability(
    tool_gateway: ToolGateway,
    mock_sandbox_runner: AsyncMock,
) -> None:
    """Action with capability in deny list must be rejected with defense-in-depth."""
    intent = ActionIntent(
        run_id=uuid4(),
        action=ActionType.GITHUB_API,
        target="repos/octocat/Hello-World",
        operation="delete",
        capability="github.delete_repository",
        reason="Malicious attempt to delete repo",
    )

    result = await tool_gateway.execute(intent, repo="octocat/Hello-World")

    assert not result.success
    assert "strictly forbidden" in (result.error or "")
    # Verify sandbox was never invoked
    mock_sandbox_runner.run_command.assert_not_called()


@pytest.mark.asyncio
async def test_tool_gateway_enforces_approval_gate(
    tool_gateway: ToolGateway,
) -> None:
    """Sensitive action requiring approval must fail if is_approved=False."""
    intent = ActionIntent(
        run_id=uuid4(),
        action=ActionType.FILE_WRITE,
        target="src/main.py",
        operation="modify",
        capability="github.create_commit",
        reason="Apply patch",
    )

    result = await tool_gateway.execute(intent, repo="octocat/Hello-World", is_approved=False)

    assert not result.success
    assert "requires explicit human approval" in (result.error or "")


@pytest.mark.asyncio
async def test_tool_gateway_dispatches_command_to_sandbox(
    tool_gateway: ToolGateway,
    mock_sandbox_runner: AsyncMock,
    mock_event_repo: AsyncMock,
) -> None:
    """Command exec intent must route directly to the isolated SandboxRunner."""
    run_id = uuid4()
    intent = ActionIntent(
        run_id=run_id,
        action=ActionType.COMMAND_EXEC,
        target="pytest tests/unit",
        operation="execute",
        capability="commands.exec",
        reason="Run unit test suite",
        metadata={"timeout_seconds": 30},
    )

    result = await tool_gateway.execute(intent, repo="octocat/Hello-World")

    assert result.success
    assert result.output["stdout"] == "1 passed in 0.05s"
    mock_sandbox_runner.run_command.assert_called_once_with(
        command="pytest tests/unit",
        files=None,
        timeout_seconds=30,
    )

    # Verify audit event was logged
    mock_event_repo.append.assert_called_once()
    event = mock_event_repo.append.call_args[0][0]
    assert event.event_type == EventType.TOOL_CALL
    assert event.run_id == run_id


@pytest.mark.asyncio
async def test_tool_gateway_dispatches_github_comment(
    tool_gateway: ToolGateway,
    mock_github_client: AsyncMock,
) -> None:
    """PR comment intent must route to GitHubClient.post_comment."""
    intent = ActionIntent(
        run_id=uuid4(),
        action=ActionType.GITHUB_API,
        target="pull_requests/42/comments",
        operation="comment",
        capability="github.comment_pr",
        reason="Post audit review",
        metadata={"body": "LGTM!", "pr_number": 42},
    )

    result = await tool_gateway.execute(intent, repo="octocat/Hello-World")

    assert result.success
    assert result.output["comment_id"] == 999
    mock_github_client.post_comment.assert_called_once_with(
        "octocat/Hello-World", 42, "LGTM!"
    )
