"""
Repository for recording and checking webhook deliveries for idempotency.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DuplicateDeliveryError
from app.domain.models.webhook_delivery import WebhookDelivery
from app.infrastructure.database.models import WebhookDeliveryORM


class WebhookRepository:
    """
    Manages persistence for incoming GitHub webhook deliveries.
    Enforces strict idempotency by converting database unique constraint violations
    into DuplicateDeliveryError domain exceptions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_delivery(self, delivery: WebhookDelivery) -> WebhookDelivery:
        """
        Persist an incoming delivery record.
        Uses a database savepoint (begin_nested) so an IntegrityError does not
        poison the entire parent transaction if a duplicate delivery arrives.
        """
        orm = WebhookDeliveryORM(
            id=delivery.id,
            github_delivery_id=delivery.github_delivery_id,
            event_type=delivery.event_type,
            payload_summary=delivery.payload_summary,
            run_id=delivery.run_id,
            received_at=delivery.received_at,
        )

        try:
            async with self._session.begin_nested():
                self._session.add(orm)
                await self._session.flush()
        except IntegrityError as err:
            raise DuplicateDeliveryError(
                f"Webhook delivery '{delivery.github_delivery_id}' has already been processed."
            ) from err

        return self._to_domain(orm)

    async def exists(self, github_delivery_id: str) -> bool:
        """Check if a delivery GUID has already been recorded."""
        stmt = select(WebhookDeliveryORM.id).where(
            WebhookDeliveryORM.github_delivery_id == github_delivery_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_by_id(self, delivery_id: UUID) -> WebhookDelivery | None:
        """Fetch delivery record by internal UUID."""
        stmt = select(WebhookDeliveryORM).where(WebhookDeliveryORM.id == delivery_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    @staticmethod
    def _to_domain(orm: WebhookDeliveryORM) -> WebhookDelivery:
        """Map internal SQLAlchemy ORM to pure domain model."""
        return WebhookDelivery(
            id=orm.id,
            github_delivery_id=orm.github_delivery_id,
            event_type=orm.event_type,
            payload_summary=orm.payload_summary,
            run_id=orm.run_id,
            received_at=orm.received_at,
        )
