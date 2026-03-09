"""Retriever for document search."""
from typing import List, Dict, Any, Optional
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from backend.retrieval.vector_store import vector_store_manager
from backend.core.logging import get_logger

logger = get_logger(__name__)


class ThreadRetriever:
    """Manages retrievers for thread-specific document search."""

    def __init__(self):
        self._retrievers: Dict[str, Any] = {}

    def get_retriever(self, thread_id: str) -> Optional[Any]:
        """Get or load retriever for a thread."""
        thread_id = str(thread_id)

        # Check memory first
        if thread_id in self._retrievers:
            return self._retrievers[thread_id]

        # Try to load from disk
        vector_store = vector_store_manager.load_vector_store(thread_id)
        if vector_store:
            retriever = vector_store.as_retriever(
                search_type="similarity", search_kwargs={"k": 4}
            )
            self._retrievers[thread_id] = retriever
            return retriever

        return None

    def set_retriever(self, thread_id: str, retriever: Any) -> None:
        """Set retriever in memory."""
        self._retrievers[str(thread_id)] = retriever

    def has_retriever(self, thread_id: str) -> bool:
        """Check if retriever exists for thread."""
        thread_id = str(thread_id)
        if thread_id in self._retrievers:
            return True
        return vector_store_manager.exists(thread_id)

    def remove_retriever(self, thread_id: str) -> None:
        """Remove retriever from memory."""
        thread_id = str(thread_id)
        self._retrievers.pop(thread_id, None)
        vector_store_manager.delete_vector_store(thread_id)

    def restore_all(self) -> int:
        """Restore all retrievers from disk. Returns count restored."""
        import sqlite3

        # Query database for all indexed documents
        conn = sqlite3.connect("chatbot.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT thread_id, faiss_index_path FROM thread_documents"
            )
            rows = cursor.fetchall()
        finally:
            conn.close()

        restored = 0
        for thread_id, index_path in rows:
            if vector_store_manager.exists(thread_id):
                retriever = self.get_retriever(thread_id)
                if retriever:
                    restored += 1
                    logger.info("retriever_restored", thread_id=thread_id)

        logger.info("retrievers_restored", count=restored)
        return restored


# Global retriever manager
thread_retriever = ThreadRetriever()
