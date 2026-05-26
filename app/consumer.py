import asyncio
import logging
import random
import uuid
from datetime import UTC, datetime

import httpx
from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitMessage
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from app.db.database import Database
from app.messaging.broker import (
    payments_dlx,
    payments_exchange,
    payments_new_queue,
    payments_retry_exchange,
)
from app.messaging.schemas import PaymentCreatedEvent
from app.models.payment import PaymentStatus
from app.repositories.outbox import OutboxRepository
from app.repositories.payment import PaymentRepository
from app.services.payment import PaymentService
from app.services.webhook import WebhookService
from app.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

broker = RabbitBroker(url=settings.rabbitmq.url)
app = FastStream(broker)

_payment_service: PaymentService | None = None
_webhook_service: WebhookService | None = None
_db: Database | None = None
_http_client: httpx.AsyncClient | None = None


@app.on_startup
async def on_startup() -> None:
    global _payment_service, _webhook_service, _db, _http_client

    _db = Database(
        url=settings.database.url,
        echo=settings.app.debug,
        pool_size=settings.database.pool_size,
        pool_timeout=settings.database.pool_timeout,
        pool_recycle=settings.database.pool_recycle,
        pool_pre_ping=settings.database.pool_pre_ping,
    )
    _http_client = httpx.AsyncClient(timeout=30.0)

    _payment_service = PaymentService(
        payment_repository=PaymentRepository(db=_db),
        outbox_repository=OutboxRepository(db=_db),
    )
    _webhook_service = WebhookService(http_client=_http_client)
    logger.info("Consumer started")


@app.on_shutdown
async def on_shutdown() -> None:
    if _http_client:
        await _http_client.aclose()
    if _db:
        await _db.disconnect()
    logger.info("Consumer stopped")


@broker.subscriber(payments_new_queue, exchange=payments_exchange)
async def process_payment(event: PaymentCreatedEvent, msg: RabbitMessage) -> None:
    retry_count = int((msg.headers or {}).get("x-retry-count", 0))

    logger.info(
        "Processing payment %s (attempt %d/%d)",
        event.payment_id,
        retry_count + 1,
        settings.consumer.max_retries + 1,
    )

    try:
        await _handle_payment(event.payment_id)
    except Exception as exc:
        logger.error("Payment %s processing failed: %s", event.payment_id, exc)
        await _schedule_retry_or_dlq(event, retry_count)


async def _handle_payment(payment_id: uuid.UUID) -> None:
    assert _payment_service is not None

    await asyncio.sleep(random.uniform(2.0, 5.0))
    success = random.random() < 0.9
    status = PaymentStatus.SUCCEEDED if success else PaymentStatus.FAILED
    processed_at = datetime.now(tz=UTC)

    await _payment_service.update_status(payment_id, status, processed_at)
    logger.info("Payment %s updated to %s", payment_id, status)

    payment = await _payment_service.get_payment(payment_id)
    if payment and payment.webhook_url:
        await _send_webhook_with_retries(payment.id, payment.webhook_url, status, processed_at)


async def _send_webhook_with_retries(
    payment_id: uuid.UUID,
    webhook_url: str,
    status: str,
    processed_at: datetime,
) -> None:
    assert _webhook_service is not None

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.consumer.webhook_max_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=settings.consumer.webhook_retry_min_wait,
                max=settings.consumer.webhook_retry_max_wait,
            ),
            reraise=True,
        ):
            with attempt:
                await _webhook_service.send(
                    webhook_url=webhook_url,
                    payment_id=payment_id,
                    status=status,
                    processed_at=processed_at,
                )
                if attempt.retry_state.attempt_number > 1:
                    logger.info(
                        "Webhook delivered on attempt %d for payment %s",
                        attempt.retry_state.attempt_number,
                        payment_id,
                    )
    except Exception as exc:
        logger.error("All webhook delivery attempts failed for payment %s: %s", payment_id, exc)


async def _schedule_retry_or_dlq(event: PaymentCreatedEvent, retry_count: int) -> None:
    max_retries = settings.consumer.max_retries
    if retry_count < max_retries:
        delay_seconds = settings.consumer.base_delay_seconds * (2**retry_count)
        logger.info(
            "Retry %d/%d for payment %s in %d s",
            retry_count + 1,
            max_retries,
            event.payment_id,
            delay_seconds,
        )
        await broker.publish(
            event.model_dump(mode="json"),
            exchange=payments_retry_exchange,
            routing_key="payments.retry",
            headers={"x-retry-count": retry_count + 1},
            expiration=delay_seconds,
        )
    else:
        logger.error(
            "Payment %s exhausted %d retries — moving to DLQ",
            event.payment_id,
            max_retries,
        )
        await broker.publish(
            event.model_dump(mode="json"),
            exchange=payments_dlx,
            routing_key="payments.dlq",
            headers={"x-retry-count": retry_count, "x-final-failure": "true"},
        )


def run() -> None:
    asyncio.run(app.run())


if __name__ == "__main__":
    run()
