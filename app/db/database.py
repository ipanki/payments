import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


class Database:
    def __init__(
        self,
        url: str,
        echo: bool = False,
        pool_size: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        pool_pre_ping: bool = True,
        poolclass: type | None = None,
    ) -> None:
        if poolclass is not None:
            self._engine: AsyncEngine = create_async_engine(url=url, echo=echo, poolclass=poolclass)
        else:
            self._engine = create_async_engine(
                url=url,
                echo=echo,
                pool_size=pool_size,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                pool_pre_ping=pool_pre_ping,
            )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        session: AsyncSession = self._session_factory()
        async with session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    async def disconnect(self) -> None:
        logger.info("Closing database connection...")
        await self._engine.dispose()
        logger.info("Database connection closed")
