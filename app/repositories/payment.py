import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import Database
from app.models.payment import Payment
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository):
    def __init__(self, db: Database) -> None:
        super().__init__(db)

    async def create(self, session: AsyncSession, payment: Payment) -> Payment:
        session.add(payment)
        await session.flush()
        await session.refresh(payment)
        return payment

    async def get_by_id(self, session: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
        return await session.get(Payment, payment_id)

    async def get_by_idempotency_key(self, session: AsyncSession, key: str) -> Payment | None:
        result = await session.execute(select(Payment).where(Payment.idempotency_key == key))
        return result.scalar_one_or_none()

    async def update_status(
        self,
        session: AsyncSession,
        payment_id: uuid.UUID,
        status: str,
        processed_at: datetime | None = None,
    ) -> None:
        await session.execute(
            update(Payment)
            .where(Payment.id == payment_id)
            .values(status=status, processed_at=processed_at)
        )
