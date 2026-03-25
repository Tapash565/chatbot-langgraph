"""Database session management."""
import sqlite3
from typing import Optional
from contextlib import contextmanager
import aiosqlite

from backend.core.config import config


class DatabaseSession:
    """SQLite database session manager."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or config.DATABASE_URL
        self._connection: Optional[sqlite3.Connection] = None
        self._async_connection: Optional[aiosqlite.Connection] = None

    @property
    def connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.database_url, check_same_thread=False
            )
            self._connection.row_factory = sqlite3.Row
        return self._connection

    @contextmanager
    def cursor(self):
        """Context manager for database cursor."""
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    async def get_async_connection(self) -> aiosqlite.Connection:
        """Get or create async database connection."""
        if self._async_connection is None:
            self._async_connection = await aiosqlite.connect(
                self.database_url,
                check_same_thread=False,
            )
            self._async_connection.row_factory = sqlite3.Row
        return self._async_connection

    async def close_async(self):
        """Close async database connection."""
        if self._async_connection:
            await self._async_connection.close()
            self._async_connection = None


# Global session instance
db_session = DatabaseSession()


def get_db() -> DatabaseSession:
    """Get database session dependency."""
    return db_session
