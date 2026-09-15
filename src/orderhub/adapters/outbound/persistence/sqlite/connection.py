import sqlite3


class SQLiteConnectionFactory:
    """Crea conexiones SQLite. Se inyecta en los repositorios."""

    def __init__(self, database_path: str) -> None:
        self._database_path = database_path

    def __call__(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection
