"""Domain protocol interfaces."""

from app.domain.protocols.github_client import GitHubClient
from app.domain.protocols.policy_evaluator import PolicyEvaluator
from app.domain.protocols.repository import Repository

__all__ = [
    "GitHubClient",
    "PolicyEvaluator",
    "Repository",
]
