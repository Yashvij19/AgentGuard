"""
Repository for managing policy configurations and audit policy decisions.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.policy import Policy, PolicyConfig
from app.domain.models.policy_decision import Decision, PolicyDecision
from app.infrastructure.database.models import PolicyDecisionORM, PolicyORM


class PolicyRepository:
    """
    Persistence layer for repository policies and evaluation decisions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_repo(self, repo: str) -> Policy | None:
        """Fetch the active policy for a repository."""
        stmt = select(PolicyORM).where(PolicyORM.repo == repo)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._policy_to_domain(orm) if orm else None

    async def save_policy(
        self,
        repo: str,
        yaml_content: str,
        parsed_config: PolicyConfig,
        rego_bundle: str | None = None,
    ) -> Policy:
        """
        Create or update a policy for a repository.
        Automatically increments the version counter upon update.
        """
        stmt = select(PolicyORM).where(PolicyORM.repo == repo)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        parsed_dict = parsed_config.model_dump(mode="json")

        if existing:
            existing.yaml_content = yaml_content
            existing.parsed_content = parsed_dict
            existing.rego_bundle = rego_bundle
            existing.version += 1
            await self._session.flush()
            return self._policy_to_domain(existing)

        new_policy = PolicyORM(
            repo=repo,
            yaml_content=yaml_content,
            parsed_content=parsed_dict,
            rego_bundle=rego_bundle,
            version=1,
        )
        self._session.add(new_policy)
        await self._session.flush()
        return self._policy_to_domain(new_policy)

    async def record_decision(
        self,
        decision: PolicyDecision,
        action_requested: dict[str, Any],
    ) -> PolicyDecision:
        """
        Record an immutable policy evaluation decision.
        """
        orm = PolicyDecisionORM(
            id=decision.id,
            run_id=decision.run_id,
            action_intent_id=decision.action_intent_id,
            action_requested=action_requested,
            rule_matched=decision.rule_matched,
            risk_score=decision.risk_score,
            decision=decision.decision.value,
            policy_version=decision.policy_version,
            opa_query_id=decision.opa_query_id,
            reason=decision.reason,
            details=decision.details,
            created_at=decision.created_at,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._decision_to_domain(orm)

    async def get_decisions_for_run(self, run_id: UUID) -> list[PolicyDecision]:
        """Fetch all policy decisions for a given run in chronological order."""
        stmt = (
            select(PolicyDecisionORM)
            .where(PolicyDecisionORM.run_id == run_id)
            .order_by(PolicyDecisionORM.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [self._decision_to_domain(orm) for orm in result.scalars().all()]

    @staticmethod
    def _policy_to_domain(orm: PolicyORM) -> Policy:
        """Convert PolicyORM to domain Policy model."""
        return Policy(
            id=orm.id,
            repo=orm.repo,
            yaml_content=orm.yaml_content,
            rego_bundle=orm.rego_bundle,
            parsed_content=PolicyConfig.model_validate(orm.parsed_content),
            version=orm.version,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def _decision_to_domain(orm: PolicyDecisionORM) -> PolicyDecision:
        """Convert PolicyDecisionORM to domain PolicyDecision model."""
        return PolicyDecision(
            id=orm.id,
            run_id=orm.run_id,
            action_intent_id=orm.action_intent_id,
            decision=Decision(orm.decision),
            rule_matched=orm.rule_matched,
            risk_score=orm.risk_score,
            policy_version=orm.policy_version,
            opa_query_id=orm.opa_query_id,
            reason=orm.reason,
            details=orm.details,
            created_at=orm.created_at,
        )
