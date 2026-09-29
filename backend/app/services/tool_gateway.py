"""
Tool Gateway service.
The single execution choke point for all approved ActionIntents.
Enforces defense-in-depth capability verification, credential scoping, and audit logging.
"""

import time
from typing import Any

import structlog

from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.llm_config import TaskType
from app.domain.models.run_event import EventType, RunEvent
from app.domain.protocols.github_client import GitHubClient
from app.domain.protocols.sandbox_runner import SandboxRunner
from app.domain.protocols.tool_executor import ExecutionResult, ToolExecutor
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.policy_repository import PolicyRepository

logger = structlog.get_logger(__name__)


class ToolGateway(ToolExecutor):
    """
    Orchestrates physical execution of approved ActionIntents.
    The agent and PolicyGateway never hold execution credentials directly.
    """

    def __init__(
        self,
        github_client: GitHubClient,
        sandbox_runner: SandboxRunner,
        policy_repository: PolicyRepository | None = None,
        event_repository: EventRepository | None = None,
        llm_gateway: Any | None = None,
    ) -> None:
        """
        Initialize ToolGateway with required execution clients and repositories.

        Args:
            github_client: Injected client for GitHub API operations.
            sandbox_runner: Injected runner for isolated command/test execution.
            policy_repository: Optional repository to verify capability boundaries.
            event_repository: Optional repository to log append-only execution events.
            llm_gateway: Optional LLM gateway for model invocation.
        """
        self._github_client = github_client
        self._sandbox_runner = sandbox_runner
        self._policy_repo = policy_repository
        self._event_repo = event_repository
        self._llm_gateway = llm_gateway

    async def execute(
        self,
        action_intent: ActionIntent,
        repo: str = "",
        is_approved: bool = False,
    ) -> ExecutionResult:
        """
        Execute an approved ActionIntent with defense-in-depth verification.

        Args:
            action_intent: The ActionIntent approved by PolicyGateway.
            repo: Target repository ('owner/repo').
            is_approved: True if a human reviewer granted approval for sensitive actions.

        Returns:
            ExecutionResult containing execution status, output, duration, and error.
        """
        start_time = time.monotonic()

        # 1. Defense-in-depth capability check
        if self._policy_repo and repo:
            policy = await self._policy_repo.get_by_repo(repo)
            if policy:
                cap_config = policy.parsed_content.capabilities
                capability = action_intent.capability

                # Hard deny check
                if capability in cap_config.deny:
                    logger.warning("tool_gateway_capability_denied", capability=capability, repo=repo)
                    return ExecutionResult(
                        success=False,
                        error=f"Capability '{capability}' is strictly forbidden by repository policy",
                    )

                # Approval gate check
                if capability in cap_config.approval and not is_approved:
                    logger.info("tool_gateway_capability_requires_approval", capability=capability, repo=repo)
                    return ExecutionResult(
                        success=False,
                        error=f"Capability '{capability}' requires explicit human approval before execution",
                    )

        # 2. Action Dispatching Matrix
        result: ExecutionResult
        try:
            match action_intent.action:
                case ActionType.COMMAND_EXEC:
                    result = await self._dispatch_command(action_intent)

                case ActionType.GITHUB_API:
                    result = await self._dispatch_github_api(action_intent, repo)

                case ActionType.FILE_READ:
                    result = await self._dispatch_file_read(action_intent, repo)

                case ActionType.FILE_WRITE:
                    result = await self._dispatch_file_write(action_intent)

                case ActionType.LLM_CALL:
                    result = await self._dispatch_llm_call(action_intent)

                case _:
                    result = ExecutionResult(
                        success=False,
                        error=f"Unsupported action type: {action_intent.action}",
                    )

        except Exception as err:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error("tool_gateway_dispatch_exception", error=str(err), action=action_intent.action)
            result = ExecutionResult(
                success=False,
                error=f"Execution failed: {err}",
                duration_ms=duration_ms,
            )

        # Set total measured duration if not already set by executor
        if result.duration_ms == 0:
            result.duration_ms = int((time.monotonic() - start_time) * 1000)

        # 3. Log Audit Trail Event
        if self._event_repo:
            try:
                event = RunEvent(
                    run_id=action_intent.run_id,
                    step_name="tool_execution",
                    event_type=EventType.TOOL_CALL,
                    content={
                        "action": action_intent.action.value,
                        "target": action_intent.target,
                        "capability": action_intent.capability,
                        "success": result.success,
                        "error": result.error,
                    },
                    tokens_used=result.tokens_used,
                    latency_ms=result.duration_ms,
                )
                await self._event_repo.append(event)
            except Exception as log_err:
                logger.warning("tool_gateway_audit_log_failed", error=str(log_err))

        return result

    async def _dispatch_command(self, intent: ActionIntent) -> ExecutionResult:
        """Dispatch shell command to the isolated SandboxRunner."""
        files = intent.metadata.get("files")
        timeout = int(intent.metadata.get("timeout_seconds", 60))

        sandbox_result = await self._sandbox_runner.run_command(
            command=intent.target,
            files=files,
            timeout_seconds=timeout,
        )

        return ExecutionResult(
            success=sandbox_result.exit_code == 0,
            output={
                "stdout": sandbox_result.stdout,
                "stderr": sandbox_result.stderr,
                "exit_code": sandbox_result.exit_code,
            },
            error=sandbox_result.stderr if sandbox_result.exit_code != 0 else None,
            duration_ms=sandbox_result.duration_ms,
            metadata={"timed_out": sandbox_result.timed_out},
        )

    async def _dispatch_github_api(self, intent: ActionIntent, repo: str) -> ExecutionResult:
        """Dispatch GitHub API requests with scoped GitHub App credentials."""
        target = intent.target.strip("/")

        # Handle PR Comment
        if "comments" in target:
            pr_number = int(intent.metadata.get("pr_number", 0))
            if not pr_number:
                # Parse PR number from target path if format is 'pull_requests/{pr_number}/comments'
                parts = target.split("/")
                if len(parts) >= 2 and parts[1].isdigit():
                    pr_number = int(parts[1])

            body = intent.metadata.get("body") or intent.metadata.get("comment_preview", "")
            if not repo or not pr_number:
                return ExecutionResult(
                    success=False,
                    error="Repository and PR number required for posting comment",
                )

            comment_id = await self._github_client.post_comment(repo, pr_number, body)
            return ExecutionResult(
                success=True,
                output={"comment_id": comment_id},
            )

        return ExecutionResult(
            success=True,
            output={"status": "completed", "target": target},
        )

    async def _dispatch_file_read(self, intent: ActionIntent, repo: str) -> ExecutionResult:
        """Fetch file content via GitHub REST API rather than local disk."""
        ref = intent.metadata.get("ref", "HEAD")
        content = await self._github_client.get_file_content(repo, intent.target, ref)
        return ExecutionResult(
            success=True,
            output=content,
        )

    async def _dispatch_file_write(self, intent: ActionIntent) -> ExecutionResult:
        """Record candidate patch diff to be applied to the PR."""
        diff = intent.metadata.get("diff", "")
        return ExecutionResult(
            success=True,
            output={
                "target": intent.target,
                "diff_length": len(diff),
                "staged": True,
            },
        )

    async def _dispatch_llm_call(self, intent: ActionIntent) -> ExecutionResult:
        """Forward LLM generation through the Unified LLM Gateway."""
        if not self._llm_gateway:
            return ExecutionResult(
                success=False,
                error="LLMGateway not configured in ToolGateway",
            )

        prompt = intent.metadata.get("prompt", intent.target)
        task_type_str = intent.metadata.get("task_type", "general").lower()
        try:
            task_type = TaskType(task_type_str)
        except ValueError:
            task_type = TaskType.GENERAL

        resp = await self._llm_gateway.generate(prompt=prompt, task_type=task_type)

        return ExecutionResult(
            success=True,
            output=resp.content,
            tokens_used=resp.total_tokens,
            duration_ms=resp.latency_ms,
        )
