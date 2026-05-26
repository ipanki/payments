import asyncio
from logging.config import fileConfig

import sqlalchemy
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.models.base import Base
from app.models.outbox import OutboxEvent  # noqa: F401 — registers model
from app.models.payment import Payment  # noqa: F401 — registers model
from app.settings import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database.url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: "sqlalchemy.engine.Connection") -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(settings.database.url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
