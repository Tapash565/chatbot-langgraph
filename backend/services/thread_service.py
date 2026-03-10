"""Thread service - business logic for thread operations."""
from typing import List, Optional

from backend.db.repositories import thread_repository
from backend.retrieval.retriever import thread_retriever
from backend.memory.thread_state import thread_state_manager
from backend.core.logging import get_logger

logger = get_logger(__name__)


class ThreadService:
    """Service for handling thread operations."""

    async def create_thread(self, name: Optional[str] = None) -> dict:
        """Create a new thread."""
        thread = thread_repository.create_or_update_thread(
            thread_id=name or "Untitled Chat"
        )
        logger.info("thread_created", thread_id=thread.thread_id, name=thread.name)
        return {
            "thread_id": thread.thread_id,
            "name": thread.name,
        }

    async def get_thread(self, thread_id: str) -> Optional[dict]:
        """Get a thread by ID."""
        thread = thread_repository.get_thread(thread_id)
        if thread:
            return {
                "thread_id": thread.thread_id,
                "name": thread.name,
                "last_active": thread.last_active.isoformat() if thread.last_active else None,
            }
        return None

    async def get_all_threads(self) -> List[dict]:
        """Get all threads sorted by last active."""
        threads = thread_repository.get_all_threads()
        return [
            {
                "thread_id": t.thread_id,
                "name": t.name,
                "last_active": t.last_active.isoformat() if t.last_active else None,
            }
            for t in threads
        ]

    async def rename_thread(self, thread_id: str, name: str) -> None:
        """Rename a thread."""
        thread_repository.rename_thread(thread_id, name)
        logger.info("thread_renamed", thread_id=thread_id, name=name)

    async def delete_thread(self, thread_id: str) -> None:
        """Delete a thread and all related data."""
        # Remove retriever
        thread_retriever.remove_retriever(thread_id)

        # Remove thread state
        thread_state_manager.remove_state(thread_id)

        # Delete from database
        thread_repository.delete_thread(thread_id)

        logger.info("thread_deleted", thread_id=thread_id)

    def has_document(self, thread_id: str) -> bool:
        """Check if thread has an indexed document."""
        return thread_retriever.has_retriever(thread_id)

    def get_document_status(self, thread_id: str) -> dict:
        """Get document status for a thread."""
        has_doc = self.has_document(thread_id)
        if has_doc:
            doc = thread_repository.get_document_metadata(thread_id)
            if doc:
                return {
                    "has_document": True,
                    "filename": doc.filename,
                    "documents": doc.documents,
                    "chunks": doc.chunks,
                }
        return {"has_document": False}
