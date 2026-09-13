"""
Generic repository protocol defining standard data access operations.
"""

from typing import Generic, Protocol, TypeVar, runtime_checkable
from uuid import UUID

T = TypeVar("T")


@runtime_checkable
class Repository(Protocol, Generic[T]):
    """Generic repository protocol for domain entity persistence."""

    async def get_by_id(self, entity_id: UUID) -> T | None:
        """Fetch an entity by its primary UUID."""
        ...

    async def save(self, entity: T) -> T:
        """Persist a new or modified entity."""
        ...
