"""Thread repository for database operations."""
import sqlite3
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from backend.db.session import db_session


@dataclass
class ThreadMetadata:
    """Thread metadata model."""
    thread_id: str
    name: Optional[str] = None
    last_active: Optional[datetime] = None


@dataclass
class ThreadDocument:
    """Thread document metadata model."""
    thread_id: str
    filename: Optional[str] = None
    documents: int = 0
    chunks: int = 0
    faiss_index_path: Optional[str] = None


class ThreadRepository:
    """Repository for thread-related database operations."""

    def init_tables(self):
        """Create thread tables if they don't exist."""
        with db_session.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS thread_metadata (
                    thread_id TEXT PRIMARY KEY,
                    name TEXT,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS thread_documents (
                    thread_id TEXT PRIMARY KEY,
                    filename TEXT,
                    documents INTEGER,
                    chunks INTEGER,
                    faiss_index_path TEXT
                )
            ''')

    def create_or_update_thread(
        self, thread_id: str, name: Optional[str] = None
    ) -> ThreadMetadata:
        """Create or update a thread."""
        with db_session.cursor() as cursor:
            cursor.execute('''
                INSERT INTO thread_metadata (thread_id, name, last_active)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(thread_id) DO UPDATE SET
                    name=COALESCE(excluded.name, name),
                    last_active=CURRENT_TIMESTAMP
            ''', (thread_id, name))
            return self.get_thread(thread_id)

    def get_thread(self, thread_id: str) -> Optional[ThreadMetadata]:
        """Get thread by ID."""
        with db_session.cursor() as cursor:
            cursor.execute(
                "SELECT thread_id, name, last_active FROM thread_metadata WHERE thread_id = ?",
                (thread_id,),
            )
            row = cursor.fetchone()
            if row:
                return ThreadMetadata(
                    thread_id=row[0],
                    name=row[1],
                    last_active=datetime.fromisoformat(row[2]) if row[2] else None,
                )
            return None

    def get_all_threads(self) -> List[ThreadMetadata]:
        """Get all threads sorted by last active."""
        with db_session.cursor() as cursor:
            cursor.execute(
                "SELECT thread_id, name, last_active FROM thread_metadata ORDER BY last_active DESC"
            )
            return [
                ThreadMetadata(
                    thread_id=row[0],
                    name=row[1],
                    last_active=datetime.fromisoformat(row[2]) if row[2] else None,
                )
                for row in cursor.fetchall()
            ]

    def rename_thread(self, thread_id: str, name: str) -> None:
        """Rename a thread."""
        with db_session.cursor() as cursor:
            cursor.execute(
                "UPDATE thread_metadata SET name = ?, last_active = CURRENT_TIMESTAMP WHERE thread_id = ?",
                (name.strip(), thread_id),
            )

    def delete_thread(self, thread_id: str) -> None:
        """Delete a thread and all related data."""
        with db_session.cursor() as cursor:
            cursor.execute("DELETE FROM thread_documents WHERE thread_id = ?", (thread_id,))
            cursor.execute("DELETE FROM thread_metadata WHERE thread_id = ?", (thread_id,))
            for table_name in ("checkpoints", "writes"):
                try:
                    cursor.execute(f"DELETE FROM {table_name} WHERE thread_id = ?", (thread_id,))
                except sqlite3.OperationalError as exc:
                    if "no such table" not in str(exc):
                        raise

    def save_document_metadata(self, doc: ThreadDocument) -> None:
        """Save document metadata for a thread."""
        with db_session.cursor() as cursor:
            cursor.execute('''
                INSERT OR REPLACE INTO thread_documents
                (thread_id, filename, documents, chunks, faiss_index_path)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                doc.thread_id,
                doc.filename,
                doc.documents,
                doc.chunks,
                doc.faiss_index_path,
            ))

    def get_document_metadata(self, thread_id: str) -> Optional[ThreadDocument]:
        """Get document metadata for a thread."""
        with db_session.cursor() as cursor:
            cursor.execute('''
                SELECT thread_id, filename, documents, chunks, faiss_index_path
                FROM thread_documents WHERE thread_id = ?
            ''', (thread_id,))
            row = cursor.fetchone()
            if row:
                return ThreadDocument(
                    thread_id=row[0],
                    filename=row[1],
                    documents=row[2],
                    chunks=row[3],
                    faiss_index_path=row[4],
                )
            return None

    def get_all_documents(self) -> List[ThreadDocument]:
        """Get all thread documents."""
        with db_session.cursor() as cursor:
            cursor.execute('''
                SELECT thread_id, filename, documents, chunks, faiss_index_path
                FROM thread_documents
            ''')
            return [
                ThreadDocument(
                    thread_id=row[0],
                    filename=row[1],
                    documents=row[2],
                    chunks=row[3],
                    faiss_index_path=row[4],
                )
                for row in cursor.fetchall()
            ]


# Global repository instance
thread_repository = ThreadRepository()
