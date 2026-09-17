"""
Deterministic Risk Engine for scoring ActionIntents against policy thresholds.
"""

from typing import NamedTuple

from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.policy import Policy
from app.domain.models.policy_decision import Decision


class RiskAssessment(NamedTuple):
    """Result of a risk scoring evaluation."""

    score: int
    decision: Decision
    reason: str


class RiskEngine:
    """
    Computes deterministic risk scores based on action severity and target patterns.
    """

    def evaluate(self, action_intent: ActionIntent, policy: Policy) -> RiskAssessment:
        """
        Score an action intent and map it to a policy decision based on thresholds.
        """
        weights = policy.parsed_content.risk_weights
        thresholds = policy.parsed_content.risk_thresholds

        score = 0
        reasons: list[str] = []

        # 1. Base score by action type
        if action_intent.action == ActionType.COMMAND_EXEC:
            cost = weights.get("command_exec", 25)
            score += cost
            reasons.append(f"Command execution (+{cost})")
        elif action_intent.action == ActionType.FILE_WRITE:
            if action_intent.operation == "create":
                cost = weights.get("file_create", 5)
            else:
                cost = weights.get("file_modify", 10)
            score += cost
            reasons.append(f"File {action_intent.operation} (+{cost})")

        # 2. Check for sensitive target keywords
        target_lower = action_intent.target.lower()
        if any(term in target_lower for term in ("auth", "token", "secret", "payment", "key")):
            cost = weights.get("sensitive_path", 50)
            score += cost
            reasons.append(f"Sensitive keyword match in path (+{cost})")

        # Clamp score between 0 and 100
        score = min(100, max(0, score))

        # 3. Map score to decision
        if score >= thresholds.deny:
            verdict = Decision.DENY
            summary = f"Risk score {score} exceeds deny threshold ({thresholds.deny}): {', '.join(reasons)}"
        elif score >= thresholds.require_approval:
            verdict = Decision.REQUIRE_APPROVAL
            summary = f"Risk score {score} requires approval ({thresholds.require_approval}): {', '.join(reasons)}"
        else:
            verdict = Decision.ALLOW
            summary = f"Risk score {score} within acceptable threshold ({', '.join(reasons) if reasons else 'Normal operation'})"

        return RiskAssessment(score=score, decision=verdict, reason=summary)
