"""
Decision Trace domain model.
Captures the agent's chain of reasoning, proposed intent, and policy verdict for each step.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.action_intent import ActionIntent
from app.domain.models.policy_decision import PolicyDecision


class DecisionTrace(BaseModel):
    """
    Comprehensive record of an agent reasoning step.
    Provides observability into why an action was proposed and how it was evaluated.
    """

    model_config = ConfigDict(frozen=True)

    step_name: str = Field(
        description="Name of the agent graph step (e.g. plan, investigate, patch)",
    )
    decision: str = Field(
        description="Summary of the agent's conclusion or next move",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Supporting data points considered by the agent",
    )
    proposed_action: ActionIntent | None = Field(
        default=None,
        description="ActionIntent proposed by the agent, if any",
    )
    policy_decision: PolicyDecision | None = Field(
        default=None,
        description="Outcome from Policy Gateway evaluation, if evaluated",
    )
    execution_result: dict[str, Any] | None = Field(
        default=None,
        description="Result of executing the action if ALLOWed",
    )
