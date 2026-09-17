"""
Compiler transforming structured PolicyConfig into OPA data documents.
"""

from typing import Any

from app.domain.exceptions import PolicyCompilationError
from app.domain.models.policy import PolicyConfig


class RegoCompiler:
    """
    Compiles validated PolicyConfig domain models into OPA-compatible data structures.
    """

    @staticmethod
    def compile_data_document(config: PolicyConfig) -> dict[str, Any]:
        """
        Transform a PolicyConfig into an OPA data document payload.

        Returns:
            A dictionary ready to be pushed to OPA at /v1/data/policy.
        """
        try:
            return {
                "version": config.version,
                "capabilities": {
                    "allow": list(config.capabilities.allow),
                    "approval": list(config.capabilities.approval),
                    "deny": list(config.capabilities.deny),
                },
                "filesystem": {
                    "read": list(config.filesystem.read),
                    "write": list(config.filesystem.write),
                },
                "commands": {
                    "allow": list(config.commands.allow),
                    "deny": list(config.commands.deny),
                },
                "network": {
                    "allowed_domains": list(config.network.allowed_domains),
                },
                "resources": {
                    "max_execution_time_seconds": config.resources.max_execution_time_seconds,
                    "max_files_modified": config.resources.max_files_modified,
                },
                "risk_weights": dict(config.risk_weights),
                "risk_thresholds": {
                    "require_approval": config.risk_thresholds.require_approval,
                    "deny": config.risk_thresholds.deny,
                },
                "budget": {
                    "max_tokens_per_run": config.budget.max_tokens_per_run,
                    "max_cost_usd_per_run": config.budget.max_cost_usd_per_run,
                },
                "sensitive_actions": [
                    {
                        "name": rule.name,
                        "trigger": rule.trigger.value,
                        "pattern": rule.pattern,
                        "description": rule.description,
                    }
                    for rule in config.sensitive_actions
                ],
            }
        except Exception as err:
            raise PolicyCompilationError(
                f"Failed to compile PolicyConfig to OPA data document: {err}",
                details={"error": str(err)},
            ) from err
