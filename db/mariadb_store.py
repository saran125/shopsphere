"""Optional MariaDB connection helper.

The demo application uses SQLite so it can run without services. This module
is used by deployment scripts when APP_MODE=mariadb.
"""
from contextlib import contextmanager
from typing import Any, Iterator

from ..config import settings


class MariaDBStore:
    def __init__(self) -> None:
        try:
            import mariadb
        except ImportError as exc:
            raise RuntimeError(
                "MariaDB mode requires mariadb. Install requirements and retry."
            ) from exc
        self._mariadb = mariadb

    @contextmanager
    def connection(self) -> Iterator[Any]:
        conn = self._mariadb.connect(
            host=settings.mariadb_host,
            port=settings.mariadb_port,
            user=settings.mariadb_user,
            password=settings.mariadb_password,
            database=settings.mariadb_database,
        )
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall() if cursor.description else []
            conn.commit()
            cursor.close()
            return rows
