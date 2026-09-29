"""Domain protocol interfaces."""

from app.domain.protocols.github_client import GitHubClient
from app.domain.protocols.llm_provider import LLMProvider
from app.domain.protocols.policy_evaluator import PolicyEvaluator
from app.domain.protocols.repository import Repository
from app.domain.protocols.sandbox_runner import SandboxResult, SandboxRunner
from app.domain.protocols.tool_executor import ExecutionResult, ToolExecutor

__all__ = [
    "ExecutionResult",
    "GitHubClient",
    "LLMProvider",
    "PolicyEvaluator",
    "Repository",
    "SandboxResult",
    "SandboxRunner",
    "ToolExecutor",
]
