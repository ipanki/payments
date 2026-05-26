from app.db.database import Database
from app.db.unit_of_work import UnitOfWork


class BaseRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def uow(self) -> UnitOfWork:
        return UnitOfWork(self._db)
