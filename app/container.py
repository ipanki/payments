from collections.abc import AsyncGenerator

import httpx
from dependency_injector import containers, providers
from faststream.rabbit import RabbitBroker

from app.db.database import Database
from app.outbox.publisher import OutboxPublisher
from app.repositories.outbox import OutboxRepository
from app.repositories.payment import PaymentRepository
from app.services.payment import PaymentService
from app.services.webhook import WebhookService
from app.settings import settings


async def _create_database() -> AsyncGenerator[Database, None]:
    db = Database(
        url=settings.database.url,
        echo=settings.app.debug,
        pool_size=settings.database.pool_size,
        pool_timeout=settings.database.pool_timeout,
        pool_recycle=settings.database.pool_recycle,
        pool_pre_ping=settings.database.pool_pre_ping,
    )
    yield db
    await db.disconnect()


async def _create_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


async def _create_broker() -> AsyncGenerator[RabbitBroker, None]:
    broker = RabbitBroker(url=settings.rabbitmq.url)
    await broker.connect()
    yield broker
    await broker.stop()


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["app.api", "app.outbox"])

    db: providers.Resource[Database] = providers.Resource(_create_database)

    broker: providers.Resource[RabbitBroker] = providers.Resource(_create_broker)

    http_client: providers.Resource[httpx.AsyncClient] = providers.Resource(_create_http_client)

    payment_repository: providers.Singleton[PaymentRepository] = providers.Singleton(
        PaymentRepository, db=db
    )

    outbox_repository: providers.Singleton[OutboxRepository] = providers.Singleton(
        OutboxRepository, db=db
    )

    payment_service: providers.Singleton[PaymentService] = providers.Singleton(
        PaymentService,
        payment_repository=payment_repository,
        outbox_repository=outbox_repository,
    )

    webhook_service: providers.Singleton[WebhookService] = providers.Singleton(
        WebhookService,
        http_client=http_client,
    )

    outbox_publisher: providers.Singleton[OutboxPublisher] = providers.Singleton(
        OutboxPublisher,
        outbox_repository=outbox_repository,
        broker=broker,
        poll_interval=settings.app.outbox_poll_interval,
    )


container = Container()
