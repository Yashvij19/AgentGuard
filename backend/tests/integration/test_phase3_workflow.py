"""
Integration test for Phase 3 Governed Workflow.
Simulates a complete PR review run executing the 6-node LangGraph state machine:
Plan -> Investigate -> Sandbox Reproduce -> LLM Patch -> Sandbox Verify -> ToolGateway Report.
"""

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agent.workflow import create_phase3_graph
from app.domain.models.action_intent import ActionType
from app.domain.models.llm_config import LLMProviderName, LLMResponse
from app.domain.models.policy_decision import Decision, PolicyDecision
from app.domain.protocols.github_client import GitHubClient
from app.domain.protocols.sandbox_runner import SandboxResult, SandboxRunner
from app.services.llm_gateway import LLMGateway
from app.services.policy_gateway import PolicyGateway
from app.services.tool_gateway import ToolGateway


@pytest.fixture
def mock_github() -> AsyncMock:
    client = AsyncMock(spec=GitHubClient)
    client.get_pr_diff = AsyncMock(
        return_value="--- a/src/calc.py\n+++ b/src/calc.py\n@@ -1,2 +1,2 @@\n-def add(a, b): return a - b\n+def add(a, b): return a + b\n"
    )
    client.get_pr_files = AsyncMock(return_value=["src/calc.py", "tests/test_calc.py"])
    client.get_file_content = AsyncMock(return_value="def add(a, b): return a - b\n")
    client.post_comment = AsyncMock(return_value=101)
    return client


@pytest.fixture
def mock_sandbox() -> AsyncMock:
    runner = AsyncMock(spec=SandboxRunner)
    runner.run_command = AsyncMock(
        return_value=SandboxResult(
            exit_code=0,
            stdout="pytest: 2 passed in 0.08s",
            stderr="",
            duration_ms=80,
            timed_out=False,
        )
    )
    return runner


@pytest.fixture
def mock_llm() -> AsyncMock:
    gw = AsyncMock(spec=LLMGateway)
    gw.generate = AsyncMock(
        return_value=LLMResponse(
            content="--- a/src/calc.py\n+++ b/src/calc.py\n@@ -1,2 +1,2 @@\n-def add(a, b): return a - b\n+def add(a, b): return a + b\n",
            model="gemini-2.0-flash",
            provider=LLMProviderName.GEMINI,
            prompt_tokens=150,
            completion_tokens=45,
            total_tokens=195,
            latency_ms=120,
            estimated_cost_usd=Decimal("0.0"),
        )
    )
    return gw


@pytest.fixture
def mock_policy() -> AsyncMock:
    gw = AsyncMock(spec=PolicyGateway)

    # Dynamically bind the verdict to the specific incoming ActionIntent
    async def _mock_evaluate(intent, repo):
        return PolicyDecision(
            run_id=intent.run_id,
            action_intent_id=intent.id,
            decision=Decision.ALLOW,
            rule_matched="rules/safe_dev",
            reason="Action permitted by development policy",
        )

    gw.evaluate_intent = AsyncMock(side_effect=_mock_evaluate)
    return gw


@pytest.fixture
def tool_gw(mock_github: AsyncMock, mock_sandbox: AsyncMock, mock_llm: AsyncMock) -> ToolGateway:
    return ToolGateway(
        github_client=mock_github,
        sandbox_runner=mock_sandbox,
        llm_gateway=mock_llm,
    )


@pytest.mark.asyncio
async def test_full_phase3_governed_workflow(
    mock_github: AsyncMock,
    mock_sandbox: AsyncMock,
    mock_llm: AsyncMock,
    mock_policy: AsyncMock,
    tool_gw: ToolGateway,
) -> None:
    """
    Execute the entire 6-node state machine and verify governance and sandbox execution.
    """
    app = create_phase3_graph(
        github_client=mock_github,
        policy_gateway=mock_policy,
        tool_gateway=tool_gw,
        llm_gateway=mock_llm,
    )

    initial_state = {
        "run_id": uuid4(),
        "repo": "octocat/Hello-World",
        "pr_number": 42,
        "head_sha": "abc1234567890",
        "changed_files": [],
        "action_intents": [],
        "policy_decisions": [],
        "decision_traces": [],
        "halted": False,
        "error": None,
    }

    # Execute workflow
    final_state = await app.ainvoke(initial_state)

    # 1. Workflow completed without halting
    assert not final_state.get("halted")
    assert final_state.get("error") is None

    # 2. Verify all 6 nodes executed and recorded ActionIntents
    intents = final_state.get("action_intents", [])
    assert len(intents) >= 5

    action_types = [i["action"] for i in intents]
    assert ActionType.FILE_READ.value in action_types
    assert ActionType.COMMAND_EXEC.value in action_types
    assert ActionType.FILE_WRITE.value in action_types
    assert ActionType.GITHUB_API.value in action_types

    # 3. Verify Sandbox was executed for reproduce and verify
    assert mock_sandbox.run_command.call_count >= 2

    # 4. Verify LLM Gateway was called for patch generation
    assert mock_llm.generate.call_count >= 1

    # 5. Verify ToolGateway posted PR comment
    assert final_state.get("comment_id") == 101
    assert "AgentGuard Governance Review" in final_state.get("summary_report", "")
