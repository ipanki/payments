import uuid
from datetime import UTC, datetime

from app.models.outbox import OutboxEvent
from app.models.payment import Payment, PaymentStatus
from app.repositories.outbox import OutboxRepository
from app.repositories.payment import PaymentRepository
from app.schemas.payment import CreatePaymentRequest


class PaymentService:
    def __init__(
        self,
        payment_repository: PaymentRepository,
        outbox_repository: OutboxRepository,
    ) -> None:
        self._payment_repo = payment_repository
        self._outbox_repo = outbox_repository

    async def create_payment(self, body: CreatePaymentRequest, idempotency_key: str) -> Payment:
        async with self._payment_repo.uow() as uow:
            existing = await self._payment_repo.get_by_idempotency_key(uow.session, idempotency_key)
            if existing:
                return existing

            payment = Payment(
                amount=body.amount,
                currency=body.currency,
                description=body.description,
                metadata_=body.metadata or {},
                idempotency_key=idempotency_key,
                webhook_url=body.webhook_url,
                status=PaymentStatus.PENDING,
            )
            payment = await self._payment_repo.create(uow.session, payment)
            await self._outbox_repo.create(
                uow.session,
                OutboxEvent(
                    event_type="payment.created",
                    payload={"payment_id": str(payment.id)},
                ),
            )
            return payment

    async def get_payment(self, payment_id: uuid.UUID) -> Payment | None:
        async with self._payment_repo.uow() as uow:
            return await self._payment_repo.get_by_id(uow.session, payment_id)

    async def update_status(
        self,
        payment_id: uuid.UUID,
        status: str,
        processed_at: datetime | None = None,
    ) -> None:
        async with self._payment_repo.uow() as uow:
            await self._payment_repo.update_status(
                uow.session,
                payment_id,
                status,
                processed_at or datetime.now(tz=UTC),
            )
