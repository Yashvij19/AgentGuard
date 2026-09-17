"""
Budget Engine for tracking and enforcing token and cost limits per run.
"""

from typing import NamedTuple
from uuid import UUID

from app.domain.models.policy import Policy
from app.domain.models.policy_decision import Decision
from app.infrastructure.database.repositories.run_repository import RunRepository


class BudgetAssessment(NamedTuple):
    """Result of budget limit verification."""

    decision: Decision
    reason: str


class BudgetEngine:
    """
    Enforces token and USD cost ceilings defined in repository policies.
    """

    def __init__(self, run_repository: RunRepository) -> None:
        self._run_repo = run_repository

    async def evaluate(self, run_id: UUID, policy: Policy) -> BudgetAssessment:
        """
        Check if the current run is within token and cost limits.
        """
        run = await self._run_repo.get_by_id(run_id)
        if not run:
            return BudgetAssessment(
                decision=Decision.DENY,
                reason=f"Run {run_id} not found during budget check",
            )

        budget_config = policy.parsed_content.budget

        # 1. Token check
        if run.total_tokens >= budget_config.max_tokens_per_run:
            return BudgetAssessment(
                decision=Decision.DENY,
                reason=f"Run consumed {run.total_tokens} tokens, exceeding budget limit of {budget_config.max_tokens_per_run}",
            )

        # 2. Cost check
        if float(run.total_cost_usd) >= budget_config.max_cost_usd_per_run:
            return BudgetAssessment(
                decision=Decision.DENY,
                reason=f"Run accrued ${run.total_cost_usd:.4f} cost, exceeding budget limit of ${budget_config.max_cost_usd_per_run:.2f}",
            )

        return BudgetAssessment(
            decision=Decision.ALLOW,
            reason="Run usage is within token and financial budget limits",
        )
