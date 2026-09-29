"""
Deterministic Risk Engine for scoring ActionIntents against policy thresholds.
Evaluates action type, path glob patterns, destructive commands, and metadata.
"""

import fnmatch
from typing import NamedTuple

from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.policy import Policy
from app.domain.models.policy_decision import Decision


class RiskAssessment(NamedTuple):
    """Result of a risk scoring evaluation."""

    score: int
    decision: Decision
    reason: str
    factors: list[str] = []


class RiskEngine:
    """
    Computes deterministic risk scores based on action severity, path globs,
    destructive commands, and intent metadata.
    """

    # Default pattern definitions if not overridden by policy risk_weights
    PRODUCTION_GLOBS: tuple[str, ...] = (
        "*config/prod/*",
        "*prod/*",
        "*production/*",
        "*helm/*prod*",
        "*k8s/*prod*",
    )
    WORKFLOW_GLOBS: tuple[str, ...] = (
        "*.github/workflows/*",
        "*.circleci/*",
        "*Jenkinsfile*",
        "*.gitlab-ci.yml",
    )
    SECRET_GLOBS: tuple[str, ...] = (
        "*.env*",
        "*secret*",
        "*credential*",
        "*token*",
        "*password*",
        "*id_rsa*",
        "*.pem",
        "*.key",
    )
    DESTRUCTIVE_COMMANDS: tuple[str, ...] = (
        "rm -rf",
        "mkfs",
        "dd if=",
        "drop database",
        "drop table",
        "sudo ",
        ":(){ :|:& };:",
        "chmod 777",
    )

    def evaluate(self, action_intent: ActionIntent, policy: Policy) -> RiskAssessment:
        """
        Score an action intent and map it to a policy decision based on thresholds.
        """
        weights = policy.parsed_content.risk_weights
        thresholds = policy.parsed_content.risk_thresholds

        score = 0
        factors: list[str] = []

        # 1. Base score by action type
        if action_intent.action == ActionType.COMMAND_EXEC:
            cost = weights.get("command_exec", 25)
            score += cost
            factors.append(f"Command execution (+{cost})")
        elif action_intent.action == ActionType.FILE_WRITE:
            cost = weights.get("filesystem_write", 20)
            score += cost
            factors.append(f"Filesystem write (+{cost})")
        elif action_intent.action == ActionType.NETWORK_REQUEST:
            cost = weights.get("network_request", 10)
            score += cost
            factors.append(f"Outbound network request (+{cost})")

        # 2. Target Path Pattern Matching (fnmatch)
        target = action_intent.target.lower().strip()

        # Production path check
        if any(fnmatch.fnmatch(target, pat) for pat in self.PRODUCTION_GLOBS):
            cost = weights.get("production_path", 40)
            score += cost
            factors.append(f"Production path target match (+{cost})")

        # CI/CD Workflow modification check
        if any(fnmatch.fnmatch(target, pat) for pat in self.WORKFLOW_GLOBS):
            cost = weights.get("workflow_modification", 30)
            score += cost
            factors.append(f"CI/CD workflow file modification (+{cost})")

        # Secret / credential target check
        if any(fnmatch.fnmatch(target, pat) for pat in self.SECRET_GLOBS):
            cost = weights.get("secret_access", 60)
            score += cost
            factors.append(f"Sensitive secret or key pattern match (+{cost})")

        # 3. Shell Command Safety Inspection
        if action_intent.action == ActionType.COMMAND_EXEC:
            cmd = action_intent.target.lower()
            if any(bad_cmd in cmd for bad_cmd in self.DESTRUCTIVE_COMMANDS):
                cost = weights.get("destructive_command", 60)
                score += cost
                factors.append(f"Destructive shell command heuristic match (+{cost})")

        # 4. Metadata Risk Flags
        metadata = action_intent.metadata or {}
        if metadata.get("force_push"):
            cost = weights.get("force_push", 50)
            score += cost
            factors.append(f"Force-push action requested (+{cost})")

        if metadata.get("elevated_privileges"):
            cost = weights.get("elevated_privileges", 40)
            score += cost
            factors.append(f"Elevated privileges requested (+{cost})")

        # Clamp final score between 0 and 100
        score = min(100, max(0, score))

        # 5. Map score to decision
        if score >= thresholds.deny:
            verdict = Decision.DENY
            summary = (
                f"Risk score {score} exceeds deny threshold ({thresholds.deny}): "
                f"{', '.join(factors)}"
            )
        elif score >= thresholds.require_approval:
            verdict = Decision.REQUIRE_APPROVAL
            summary = (
                f"Risk score {score} requires human approval ({thresholds.require_approval}): "
                f"{', '.join(factors)}"
            )
        else:
            verdict = Decision.ALLOW
            summary = (
                f"Risk score {score} within acceptable threshold "
                f"({', '.join(factors) if factors else 'Standard operation'})"
            )

        return RiskAssessment(
            score=score,
            decision=verdict,
            reason=summary,
            factors=factors,
        )
