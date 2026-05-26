from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import Database


class UnitOfWork:
    def __init__(self, db: Database) -> None:
        self._db = db
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        assert self._session is not None
        return self._session

    async def __aenter__(self) -> "UnitOfWork":
        self._ctx = self._db.session()
        self._session = await self._ctx.__aenter__()
        await self._session.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        if exc_type:
            await self._session.rollback()
        else:
            await self._session.commit()

        await self._ctx.__aexit__(exc_type, exc_val, exc_tb)
