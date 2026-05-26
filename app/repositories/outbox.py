from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import Database
from app.models.outbox import OutboxEvent
from app.repositories.base import BaseRepository


class OutboxRepository(BaseRepository):
    def __init__(self, db: Database) -> None:
        super().__init__(db)

    async def create(self, session: AsyncSession, event: OutboxEvent) -> OutboxEvent:
        session.add(event)
        await session.flush()
        return event

    async def get_pending(self, session: AsyncSession, limit: int = 100) -> list[OutboxEvent]:
        result = await session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.published == False)  # noqa: E712
            .order_by(OutboxEvent.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())

    async def mark_published(self, session: AsyncSession, event_id: object) -> None:
        await session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(published=True, published_at=datetime.now(tz=UTC))
        )

    async def increment_retry(self, session: AsyncSession, event_id: object) -> None:
        result = await session.execute(select(OutboxEvent).where(OutboxEvent.id == event_id))
        event = result.scalar_one_or_none()
        if event:
            event.retry_count += 1
