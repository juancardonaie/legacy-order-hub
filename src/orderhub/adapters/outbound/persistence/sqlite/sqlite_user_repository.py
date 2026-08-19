import sqlite3
from typing import Callable, Optional

from orderhub.application.ports.user_repository import UserRepository
from orderhub.domain.entities.user import User


class SQLiteUserRepository(UserRepository):
    """Implementación del puerto de usuarios sobre SQLite.

    Consulta parametrizada (RNF-02.2); solo lee password_hash, nunca la
    columna legada `password` en texto plano.
    """

    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]) -> None:
        self._connection_factory = connection_factory

    def find_by_username(self, username: str) -> Optional[User]:
        connection = self._connection_factory()
        try:
            row = connection.execute(
                "SELECT id, username, password_hash, role FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        finally:
            connection.close()

        return self._to_entity(row) if row is not None else None

    @staticmethod
    def _to_entity(row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
        )
