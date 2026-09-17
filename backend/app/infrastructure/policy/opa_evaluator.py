"""
OPA Policy Evaluator implementation.
Evaluates ActionIntents against Rego policies via OPA REST sidecar with fail-closed security.
"""

from typing import Any
from uuid import uuid4

import structlog

from app.domain.exceptions import OPAEvaluationError
from app.domain.models.action_intent import ActionIntent
from app.domain.models.policy import Policy
from app.domain.models.policy_decision import Decision, PolicyDecision
from app.domain.protocols.policy_evaluator import PolicyEvaluator
from app.infrastructure.policy.opa_client import OPAClient
from app.infrastructure.policy.rego_compiler import RegoCompiler

logger = structlog.get_logger(__name__)


class OPAEvaluator(PolicyEvaluator):
    """
    Evaluates ActionIntents through Open Policy Agent with strict fail-closed defaults.
    """

    def __init__(
        self,
        opa_client: OPAClient,
        rego_compiler: RegoCompiler | None = None,
        policy_package: str = "agentguard.policy",
    ) -> None:
        self._client = opa_client
        self._compiler = rego_compiler or RegoCompiler()
        self._package = policy_package
        self._synced_policies: dict[str, int] = {}  # repo -> version cache

    async def evaluate(
        self,
        action_intent: ActionIntent,
        policy: Policy,
        run_context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """
        Evaluate an ActionIntent using OPA.
        Guarantees FAIL-CLOSED behavior if OPA is unreachable.
        """
        opa_query_id = str(uuid4())

        # 1. Format input document
        input_doc: dict[str, Any] = {
            "action_intent": {
                "id": str(action_intent.id),
                "run_id": str(action_intent.run_id),
                "action": action_intent.action.value,
                "target": action_intent.target,
                "operation": action_intent.operation,
                "capability": action_intent.capability,
                "reason": action_intent.reason,
                "metadata": action_intent.metadata,
            },
            "run_context": run_context or {},
        }

        try:
            # 2. Sync policy data to OPA if version changed or not yet synced
            cached_version = self._synced_policies.get(policy.repo)
            if cached_version != policy.version:
                data_doc = self._compiler.compile_data_document(policy.parsed_content)
                await self._client.upload_data("policy", data_doc)
                self._synced_policies[policy.repo] = policy.version

            # 3. Query OPA policy
            response_data = await self._client.query_policy(self._package, input_doc)

            # 4. Extract result with fail-closed fallback
            # The result from main.rego is at response_data['result'] or response_data directly
            evaluation_result = response_data.get("result", response_data)

            raw_decision = evaluation_result.get("decision", Decision.DENY.value)
            try:
                verdict = Decision(raw_decision)
            except ValueError:
                verdict = Decision.DENY

            rule_matched = evaluation_result.get("rule_matched", "default_deny")
            reason = evaluation_result.get("reason", "No reason provided by policy engine")

            return PolicyDecision(
                run_id=action_intent.run_id,
                action_intent_id=action_intent.id,
                decision=verdict,
                rule_matched=rule_matched,
                risk_score=0,
                policy_version=policy.version,
                opa_query_id=opa_query_id,
                reason=reason,
                details={"opa_evaluation": evaluation_result},
            )

        except (OPAEvaluationError, Exception) as err:
            # STRICT FAIL-CLOSED SECURITY GUARANTEE:
            # If OPA is down, timing out, or errored, NEVER allow the action!
            logger.error(
                "opa_evaluation_failed_failing_closed",
                error=str(err),
                run_id=str(action_intent.run_id),
                action_intent_id=str(action_intent.id),
                target=action_intent.target,
            )
            return PolicyDecision(
                run_id=action_intent.run_id,
                action_intent_id=action_intent.id,
                decision=Decision.DENY,
                rule_matched="opa_unreachable_fail_closed",
                risk_score=100,
                policy_version=policy.version,
                opa_query_id=opa_query_id,
                reason=f"Security evaluation failed due to OPA error: {err}. Action denied by default.",
                details={"error": str(err)},
            )
