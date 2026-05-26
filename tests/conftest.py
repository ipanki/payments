import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from app.db.database import Database
from app.models.base import Base
from app.repositories.outbox import OutboxRepository
from app.repositories.payment import PaymentRepository
from app.schemas.payment import CreatePaymentRequest
from app.services.payment import PaymentService


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest.fixture(scope="session")
def db_url(postgres_container):
    return postgres_container.get_connection_url().replace("+psycopg2", "+asyncpg")


@pytest.fixture(scope="session", autouse=True)
def create_schema(db_url):
    async def _run():
        engine = create_async_engine(db_url, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_run())


@pytest.fixture
async def db(db_url):
    database = Database(url=db_url, poolclass=NullPool)
    yield database
    await database.disconnect()


@pytest.fixture(autouse=True)
async def clean_tables(db):
    yield
    async with db.engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE payments, outbox_events RESTART IDENTITY CASCADE"))


@pytest.fixture
def payment_repo(db):
    return PaymentRepository(db=db)


@pytest.fixture
def outbox_repo(db):
    return OutboxRepository(db=db)


@pytest.fixture
def payment_service(payment_repo, outbox_repo):
    return PaymentService(payment_repository=payment_repo, outbox_repository=outbox_repo)


@pytest.fixture
def create_request():
    return CreatePaymentRequest(
        amount=Decimal("250.00"),
        currency="RUB",
        description="Test payment",
        metadata={"order_id": "42"},
        webhook_url="https://example.com/webhook",
    )
