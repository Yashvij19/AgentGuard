"""
Domain exception hierarchy for AgentGuard.
All domain errors inherit from AgentGuardError to allow clean exception handling.
"""

from typing import Any


class AgentGuardError(Exception):
    """Base exception for all AgentGuard domain errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# Webhook & Ingestion Errors
class WebhookValidationError(AgentGuardError):
    """Raised when an incoming webhook signature fails cryptographic verification."""


class DuplicateDeliveryError(AgentGuardError):
    """Raised when a webhook delivery ID has already been recorded (idempotency hit)."""


# Run & Concurrency Errors
class RunNotFoundError(AgentGuardError):
    """Raised when a requested Run ID does not exist."""


class ConcurrentRunError(AgentGuardError):
    """Raised when a run cannot proceed because another run holds the lock on the PR."""


class StaleRunError(AgentGuardError):
    """Raised when a run's commit-SHA does not match the latest PR head commit."""


# Policy & Security Errors
class PolicyViolationError(AgentGuardError):
    """Raised when an action violates security policy and is denied."""


class BudgetExceededError(AgentGuardError):
    """Raised when an action or run exceeds token/cost budget."""


class OPAEvaluationError(AgentGuardError):
    """Raised when OPA policy evaluation fails or is unreachable (fail-closed)."""


class PolicyCompilationError(AgentGuardError):
    """Raised when a YAML policy cannot be compiled into Rego rules."""


# LLM Gateway Errors
class LLMProviderError(AgentGuardError):
    """Base error for LLM provider failures."""


class LLMOutputValidationError(LLMProviderError):
    """Raised when LLM output fails schema validation."""


class LLMCircuitBreakerOpenError(LLMProviderError):
    """Raised when a provider's circuit breaker has tripped due to error thresholds."""


class LLMAllProvidersFailedError(LLMProviderError):
    """Raised when all configured LLM providers fail or are unavailable."""


# Execution Errors
class SandboxExecutionError(AgentGuardError):
    """Raised when execution in E2B or GitHub Actions sandbox fails."""


# Approval Errors
class ApprovalNotFoundError(AgentGuardError):
    """Raised when a requested approval does not exist."""


class InvalidApprovalStateError(AgentGuardError):
    """Raised when attempting an invalid status transition on an approval."""
