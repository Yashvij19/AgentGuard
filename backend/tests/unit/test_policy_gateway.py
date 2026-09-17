"""
Unit tests for PolicyGateway orchestration.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.models.policy_decision import Decision, PolicyDecision
from app.services.budget_engine import BudgetAssessment
from app.services.policy_gateway import PolicyGateway
from app.services.risk_engine import RiskAssessment
from tests.factories import create_test_action_intent, create_test_policy


def _mock_record_decision(decision: PolicyDecision, *args: Any, **kwargs: Any) -> PolicyDecision:
    """Explicitly typed side_effect helper for PolicyRepository.record_decision."""
    return decision

@pytest.mark.asyncio
async def test_policy_gateway_all_pass_returns_allow() -> None:
    """When OPA, Risk, and Budget all approve, final decision is ALLOW."""
    intent = create_test_action_intent()
    policy = create_test_policy()

    mock_policy_repo = AsyncMock()
    mock_policy_repo.get_by_repo.return_value = policy
    mock_policy_repo.record_decision.side_effect = _mock_record_decision

    mock_event_repo = AsyncMock()

    mock_evaluator = AsyncMock()
    mock_evaluator.evaluate.return_value = PolicyDecision(
        run_id=intent.run_id,
        action_intent_id=intent.id,
        decision=Decision.ALLOW,
        rule_matched="policy_allow",
    )

    mock_risk_engine = MagicMock()
    mock_risk_engine.evaluate.return_value = RiskAssessment(
        score=10, decision=Decision.ALLOW, reason="Normal risk"
    )

    mock_budget_engine = AsyncMock()
    mock_budget_engine.evaluate.return_value = BudgetAssessment(
        decision=Decision.ALLOW, reason="Within budget"
    )

    gateway = PolicyGateway(
        policy_repository=mock_policy_repo,
        event_repository=mock_event_repo,
        policy_evaluator=mock_evaluator,
        risk_engine=mock_risk_engine,
        budget_engine=mock_budget_engine,
    )

    result = await gateway.evaluate_intent(intent, "octocat/Hello-World")

    assert result.decision == Decision.ALLOW
    mock_policy_repo.record_decision.assert_awaited_once()
    mock_event_repo.append.assert_awaited_once()


@pytest.mark.asyncio
async def test_policy_gateway_opa_deny_short_circuits() -> None:
    """When OPA returns DENY, gateway short-circuits without evaluating risk or budget."""
    intent = create_test_action_intent()
    policy = create_test_policy()

    mock_policy_repo = AsyncMock()
    mock_policy_repo.get_by_repo.return_value = policy
    mock_policy_repo.record_decision.side_effect = _mock_record_decision

    mock_event_repo = AsyncMock()

    mock_evaluator = AsyncMock()
    mock_evaluator.evaluate.return_value = PolicyDecision(
        run_id=intent.run_id,
        action_intent_id=intent.id,
        decision=Decision.DENY,
        rule_matched="capability_denied",
        reason="Forbidden capability",
    )

    mock_risk_engine = MagicMock()
    mock_budget_engine = AsyncMock()

    gateway = PolicyGateway(
        policy_repository=mock_policy_repo,
        event_repository=mock_event_repo,
        policy_evaluator=mock_evaluator,
        risk_engine=mock_risk_engine,
        budget_engine=mock_budget_engine,
    )

    result = await gateway.evaluate_intent(intent, "octocat/Hello-World")

    assert result.decision == Decision.DENY
    assert result.rule_matched == "capability_denied"
    # Proves short-circuit optimization:
    mock_risk_engine.evaluate.assert_not_called()
    mock_budget_engine.evaluate.assert_not_called()


@pytest.mark.asyncio
async def test_policy_gateway_risk_require_approval_overrides_opa_allow() -> None:
    """When OPA allows but Risk requires approval, final decision is REQUIRE_APPROVAL."""
    intent = create_test_action_intent()
    policy = create_test_policy()

    mock_policy_repo = AsyncMock()
    mock_policy_repo.get_by_repo.return_value = policy
    mock_policy_repo.record_decision.side_effect = _mock_record_decision

    mock_event_repo = AsyncMock()

    mock_evaluator = AsyncMock()
    mock_evaluator.evaluate.return_value = PolicyDecision(
        run_id=intent.run_id,
        action_intent_id=intent.id,
        decision=Decision.ALLOW,
        rule_matched="policy_allow",
    )

    mock_risk_engine = MagicMock()
    mock_risk_engine.evaluate.return_value = RiskAssessment(
        score=75,
        decision=Decision.REQUIRE_APPROVAL,
        reason="High sensitive path score",
    )

    mock_budget_engine = AsyncMock()
    mock_budget_engine.evaluate.return_value = BudgetAssessment(
        decision=Decision.ALLOW, reason="OK"
    )

    gateway = PolicyGateway(
        policy_repository=mock_policy_repo,
        event_repository=mock_event_repo,
        policy_evaluator=mock_evaluator,
        risk_engine=mock_risk_engine,
        budget_engine=mock_budget_engine,
    )

    result = await gateway.evaluate_intent(intent, "octocat/Hello-World")

    # Most-restrictive precedence: REQUIRE_APPROVAL beats ALLOW
    assert result.decision == Decision.REQUIRE_APPROVAL
    assert result.risk_score == 75
