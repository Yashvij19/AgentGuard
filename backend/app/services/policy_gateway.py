"""
Policy Gateway service.
The single authoritative entry point for evaluating agent ActionIntents.
"""

from typing import Any
from uuid import uuid4

import structlog

from app.domain.models.action_intent import ActionIntent
from app.domain.models.policy import Policy, PolicyConfig
from app.domain.models.policy_decision import Decision, PolicyDecision
from app.domain.models.run_event import EventType, RunEvent
from app.domain.protocols.policy_evaluator import PolicyEvaluator
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.policy_repository import PolicyRepository
from app.services.budget_engine import BudgetEngine
from app.services.risk_engine import RiskEngine

logger = structlog.get_logger(__name__)


class PolicyGateway:
    """
    Central gatekeeper enforcing policy compliance, risk scoring, and budget bounds.
    """

    def __init__(
        self,
        policy_repository: PolicyRepository,
        event_repository: EventRepository,
        policy_evaluator: PolicyEvaluator,
        risk_engine: RiskEngine,
        budget_engine: BudgetEngine,
    ) -> None:
        self._policy_repo = policy_repository
        self._event_repo = event_repository
        self._evaluator = policy_evaluator
        self._risk_engine = risk_engine
        self._budget_engine = budget_engine

    async def evaluate_intent(
        self,
        action_intent: ActionIntent,
        repo: str,
        run_context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """
        Evaluate an ActionIntent across OPA, Risk, and Budget engines.
        Returns the combined most-restrictive decision and records it to the ledger.
        """
        # 1. Fetch policy for repo, or create a default policy in memory
        policy = await self._policy_repo.get_by_repo(repo)
        if not policy:
            logger.info("policy_not_found_using_default", repo=repo)
            policy = Policy(
                repo=repo,
                yaml_content="# Default Fallback Policy",
                parsed_content=PolicyConfig(),
                version=1,
            )

        # 2. Evaluate OPA policy rules
        opa_decision = await self._evaluator.evaluate(
            action_intent=action_intent,
            policy=policy,
            run_context=run_context,
        )

        # Short-circuit: if OPA explicitly DENIES, do not proceed with further checks
        if opa_decision.decision == Decision.DENY:
            return await self._finalize_decision(opa_decision, action_intent)

        # 3. Evaluate Risk Engine
        risk_assessment = self._risk_engine.evaluate(action_intent, policy)

        # 4. Evaluate Budget Engine
        budget_assessment = await self._budget_engine.evaluate(action_intent.run_id, policy)

        # 5. Calculate most restrictive verdict
        final_verdict = self._resolve_precedence(
            opa_decision.decision,
            risk_assessment.decision,
            budget_assessment.decision,
        )

        # Determine matched rule and composite reason
        matched_rule = opa_decision.rule_matched
        reasons = [opa_decision.reason]

        if final_verdict == Decision.DENY:
            if budget_assessment.decision == Decision.DENY:
                matched_rule = "budget_exceeded"
                reasons.append(budget_assessment.reason)
            elif risk_assessment.decision == Decision.DENY:
                matched_rule = "risk_threshold_exceeded"
                reasons.append(risk_assessment.reason)
        elif final_verdict == Decision.REQUIRE_APPROVAL:
            if risk_assessment.decision == Decision.REQUIRE_APPROVAL:
                matched_rule = "risk_requires_approval"
                reasons.append(risk_assessment.reason)

        consolidated_decision = PolicyDecision(
            id=opa_decision.id,
            run_id=action_intent.run_id,
            action_intent_id=action_intent.id,
            decision=final_verdict,
            rule_matched=matched_rule,
            risk_score=risk_assessment.score,
            policy_version=policy.version,
            opa_query_id=opa_decision.opa_query_id,
            reason=" | ".join(filter(None, reasons)),
            details={
                "opa": opa_decision.details,
                "risk": {"score": risk_assessment.score, "reason": risk_assessment.reason},
                "budget": {"reason": budget_assessment.reason},
            },
        )

        return await self._finalize_decision(consolidated_decision, action_intent)

    async def _finalize_decision(
        self,
        decision: PolicyDecision,
        action_intent: ActionIntent,
    ) -> PolicyDecision:
        """
        Atomically persist the decision to the policy_decisions table
        and record an audit event into the Action Ledger (run_events).
        """
        # Record in policy_decisions table
        persisted = await self._policy_repo.record_decision(
            decision=decision,
            action_requested=action_intent.model_dump(mode="json"),
        )

        # Emit to append-only Action Ledger
        await self._event_repo.append(
            RunEvent(
                id=uuid4(),
                run_id=decision.run_id,
                step_name="policy_gateway",
                event_type=EventType.POLICY_DECISION,
                content={
                    "decision_id": str(persisted.id),
                    "action_intent_id": str(action_intent.id),
                    "action": action_intent.action.value,
                    "target": action_intent.target,
                    "capability": action_intent.capability,
                    "decision": persisted.decision.value,
                    "rule_matched": persisted.rule_matched,
                    "risk_score": persisted.risk_score,
                    "reason": persisted.reason,
                },
            )
        )

        logger.info(
            "policy_decision_recorded",
            run_id=str(decision.run_id),
            action=action_intent.action.value,
            target=action_intent.target,
            verdict=persisted.decision.value,
            rule_matched=persisted.rule_matched,
            risk_score=persisted.risk_score,
        )

        return persisted

    @staticmethod
    def _resolve_precedence(d1: Decision, d2: Decision, d3: Decision) -> Decision:
        """
        Resolve tri-state decision precedence:
        DENY > REQUIRE_APPROVAL > ALLOW
        """
        decisions = (d1, d2, d3)
        if Decision.DENY in decisions:
            return Decision.DENY
        if Decision.REQUIRE_APPROVAL in decisions:
            return Decision.REQUIRE_APPROVAL
        return Decision.ALLOW
