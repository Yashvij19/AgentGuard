"""
Budget Engine for tracking and enforcing token, financial cost, and invocation limits per run.
Supports preemptive checking before executing costly actions.
"""

from typing import NamedTuple
from uuid import UUID

from app.domain.models.policy import Policy
from app.domain.models.policy_decision import Decision
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.run_repository import RunRepository


class BudgetAssessment(NamedTuple):
    """Result of budget limit verification."""

    decision: Decision
    reason: str


class BudgetEngine:
    """
    Enforces token, financial cost, and call ceilings defined in repository policies.
    """

    def __init__(
        self,
        run_repository: RunRepository,
        event_repository: EventRepository | None = None,
    ) -> None:
        self._run_repo = run_repository
        self._event_repo = event_repository

    async def evaluate(
        self,
        run_id: UUID,
        policy: Policy,
        estimated_tokens: int = 0,
        estimated_cost: float = 0.0,
    ) -> BudgetAssessment:
        """
        Check if the current run is within token, cost, and call bounds.
        Applies preemptive evaluation if estimated consumption is provided.
        """
        run = await self._run_repo.get_by_id(run_id)
        if not run:
            return BudgetAssessment(
                decision=Decision.DENY,
                reason=f"Run {run_id} not found during budget check",
            )

        budget_config = policy.parsed_content.budget

        # 1. Preemptive / Cumulative Token Check
        projected_tokens = run.total_tokens + max(0, estimated_tokens)
        if projected_tokens > budget_config.max_tokens_per_run:
            return BudgetAssessment(
                decision=Decision.DENY,
                reason=(
                    f"Projected tokens ({projected_tokens}) exceed budget limit of "
                    f"{budget_config.max_tokens_per_run} (current: {run.total_tokens}, "
                    f"estimated: {estimated_tokens})"
                ),
            )

        # 2. Preemptive / Cumulative Cost Check
        projected_cost = float(run.total_cost_usd) + max(0.0, estimated_cost)
        if projected_cost > budget_config.max_cost_usd_per_run:
            return BudgetAssessment(
                decision=Decision.DENY,
                reason=(
                    f"Projected cost (${projected_cost:.4f}) exceeds budget limit of "
                    f"${budget_config.max_cost_usd_per_run:.2f} (current: ${run.total_cost_usd:.4f}, "
                    f"estimated: ${estimated_cost:.4f})"
                ),
            )

        # 3. LLM API Invocation Count Check (if event repository is available)
        if self._event_repo:
            if hasattr(self._event_repo, "get_events_for_run"):
                events = await self._event_repo.get_events_for_run(run_id)
            else:
                events = await self._event_repo.get_by_run_id(run_id)
            llm_call_count = sum(1 for e in events if e.event_type.value == "llm_call")
            if llm_call_count >= budget_config.max_llm_calls_per_run:
                return BudgetAssessment(
                    decision=Decision.DENY,
                    reason=(
                        f"Run has made {llm_call_count} LLM calls, exceeding limit of "
                        f"{budget_config.max_llm_calls_per_run}"
                    ),
                )

        return BudgetAssessment(
            decision=Decision.ALLOW,
            reason="Run usage is within token, financial, and invocation budget limits",
        )
