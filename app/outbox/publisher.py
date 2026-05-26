import asyncio
import logging

from faststream.rabbit import RabbitBroker

from app.messaging.broker import payments_exchange
from app.messaging.schemas import PaymentCreatedEvent
from app.models.outbox import OutboxEvent
from app.repositories.outbox import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxPublisher:
    def __init__(
        self,
        outbox_repository: OutboxRepository,
        broker: RabbitBroker,
        poll_interval: float = 2.0,
    ) -> None:
        self._outbox_repo = outbox_repository
        self._broker = broker
        self._poll_interval = poll_interval
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())
        logger.info("Outbox publisher started (poll_interval=%.1fs)", self._poll_interval)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Outbox publisher stopped")

    async def _run(self) -> None:
        while True:
            try:
                await self._publish_pending()
            except Exception:
                logger.exception("Outbox publisher cycle error")
            await asyncio.sleep(self._poll_interval)

    async def _publish_pending(self) -> None:
        async with self._outbox_repo.uow() as uow:
            events = await self._outbox_repo.get_pending(uow.session)
            for event in events:
                try:
                    await self._dispatch(event)
                    await self._outbox_repo.mark_published(uow.session, event.id)
                except Exception:
                    await self._outbox_repo.increment_retry(uow.session, event.id)
                    logger.exception(
                        "Failed to publish outbox event %s (type=%s)",
                        event.id,
                        event.event_type,
                    )

    async def _dispatch(self, event: OutboxEvent) -> None:
        if event.event_type == "payment.created":
            await self._broker.publish(
                PaymentCreatedEvent(payment_id=event.payload["payment_id"]),
                exchange=payments_exchange,
                routing_key="payments.new",
            )
            logger.debug(
                "Published %s for payment %s", event.event_type, event.payload["payment_id"]
            )
        else:
            logger.warning("Unknown event type: %s", event.event_type)
