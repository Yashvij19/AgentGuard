"""
Unit tests for OPAEvaluator.
"""

from unittest.mock import AsyncMock

import pytest

from app.domain.exceptions import OPAEvaluationError
from app.domain.models.policy_decision import Decision
from app.infrastructure.policy.opa_client import OPAClient
from app.infrastructure.policy.opa_evaluator import OPAEvaluator
from tests.factories import create_test_action_intent, create_test_policy


@pytest.mark.asyncio
async def test_opa_evaluator_successful_allow() -> None:
    """When OPA returns ALLOW, evaluator must return structured PolicyDecision."""
    mock_client = AsyncMock(spec=OPAClient)
    mock_client.query_policy.return_value = {
        "decision": "ALLOW",
        "rule_matched": "policy_allow",
        "reason": "Permitted by repository policy",
    }

    evaluator = OPAEvaluator(opa_client=mock_client)
    intent = create_test_action_intent()
    policy = create_test_policy()

    decision = await evaluator.evaluate(intent, policy)

    assert decision.decision == Decision.ALLOW
    assert decision.rule_matched == "policy_allow"
    assert decision.risk_score == 0
    assert decision.policy_version == policy.version
    mock_client.upload_data.assert_awaited_once()
    mock_client.query_policy.assert_awaited_once()


@pytest.mark.asyncio
async def test_opa_evaluator_successful_deny() -> None:
    """When OPA returns DENY, evaluator must parse decision properly."""
    mock_client = AsyncMock(spec=OPAClient)
    mock_client.query_policy.return_value = {
        "decision": "DENY",
        "rule_matched": "capability_denied",
        "reason": "Capability is forbidden",
    }

    evaluator = OPAEvaluator(opa_client=mock_client)
    intent = create_test_action_intent()
    policy = create_test_policy()

    decision = await evaluator.evaluate(intent, policy)

    assert decision.decision == Decision.DENY
    assert decision.rule_matched == "capability_denied"


@pytest.mark.asyncio
async def test_opa_evaluator_fail_closed_on_network_error() -> None:
    """
    CRITICAL SECURITY TEST:
    If OPA is unreachable or times out, the evaluator MUST fail closed and return DENY.
    """
    mock_client = AsyncMock(spec=OPAClient)
    mock_client.upload_data.side_effect = OPAEvaluationError("Connection refused to OPA at :8181")

    evaluator = OPAEvaluator(opa_client=mock_client)
    intent = create_test_action_intent()
    policy = create_test_policy()

    decision = await evaluator.evaluate(intent, policy)

    # Must FAIL CLOSED
    assert decision.decision == Decision.DENY
    assert decision.rule_matched == "opa_unreachable_fail_closed"
    assert decision.risk_score == 100
    assert "Connection refused" in decision.reason
