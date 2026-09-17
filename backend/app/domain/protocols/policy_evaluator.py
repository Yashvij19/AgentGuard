"""
Policy Evaluator protocol interface.
"""

from typing import Any, Protocol, runtime_checkable

from app.domain.models.action_intent import ActionIntent
from app.domain.models.policy import Policy
from app.domain.models.policy_decision import PolicyDecision


@runtime_checkable
class PolicyEvaluator(Protocol):
    """
    Interface for policy evaluation engines (e.g. OPA sidecar, embedded evaluator).
    """

    async def evaluate(
        self,
        action_intent: ActionIntent,
        policy: Policy,
        run_context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """
        Evaluate an ActionIntent against a repository's Policy.

        Args:
            action_intent: The proposed action.
            policy: The repository's active governance policy.
            run_context: Auxiliary context (e.g. repo, PR number, commit SHA).

        Returns:
            PolicyDecision containing verdict, rule matched, and reason.
        """
        ...
