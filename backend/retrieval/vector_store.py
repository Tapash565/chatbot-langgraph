"""Vector store management for FAISS."""
import os
from typing import Optional, List
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from backend.retrieval.embedder import embeddings_provider
from backend.core.config import config
from backend.core.logging import get_logger

logger = get_logger(__name__)


class VectorStoreManager:
    """Manages FAISS vector stores for threads."""

    def __init__(self):
        self.indices_dir = config.FAISS_INDICES_DIR
        os.makedirs(self.indices_dir, exist_ok=True)

    def get_index_path(self, thread_id: str) -> str:
        """Get the file path for a thread's FAISS index."""
        # Validate thread_id to prevent path traversal
        if ".." in thread_id or "/" in thread_id or "\\" in thread_id:
            raise ValueError("Invalid thread_id: path traversal not allowed")

        # Ensure only safe characters
        if not thread_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Invalid thread_id: must be alphanumeric with hyphens/underscores")

        return os.path.join(self.indices_dir, f"{thread_id}.faiss")

    def create_vector_store(
        self, documents: List[Document], thread_id: str
    ) -> FAISS:
        """Create a new FAISS vector store from documents."""
        embeddings = embeddings_provider.get_embeddings()
        vector_store = FAISS.from_documents(documents, embeddings)

        # Persist to disk
        index_path = self.get_index_path(thread_id)
        vector_store.save_local(index_path)

        logger.info(
            "vector_store_created",
            thread_id=thread_id,
            doc_count=len(documents),
            index_path=index_path,
        )

        return vector_store

    def load_vector_store(self, thread_id: str) -> Optional[FAISS]:
        """Load a FAISS vector store from disk."""
        index_path = self.get_index_path(thread_id)

        if not os.path.exists(index_path):
            logger.warning("vector_store_not_found", thread_id=thread_id)
            return None

        try:
            embeddings = embeddings_provider.get_embeddings()
            vector_store = FAISS.load_local(
                index_path,
                embeddings,
                allow_dangerous_deserialization=True,
            )

            logger.info("vector_store_loaded", thread_id=thread_id)
            return vector_store
        except Exception as e:
            logger.error(
                "vector_store_load_error",
                thread_id=thread_id,
                error=str(e),
            )
            return None

    def delete_vector_store(self, thread_id: str) -> bool:
        """Delete a FAISS vector store from disk."""
        index_path = self.get_index_path(thread_id)

        if not os.path.exists(index_path):
            return False

        try:
            # FAISS saves as directory, not single file
            import shutil
            if os.path.isdir(index_path):
                shutil.rmtree(index_path)
            else:
                os.remove(index_path)

            logger.info("vector_store_deleted", thread_id=thread_id)
            return True
        except Exception as e:
            logger.error(
                "vector_store_delete_error",
                thread_id=thread_id,
                error=str(e),
            )
            return False

    def exists(self, thread_id: str) -> bool:
        """Check if a vector store exists for a thread."""
        index_path = self.get_index_path(thread_id)
        return os.path.exists(index_path)


# Global vector store manager
vector_store_manager = VectorStoreManager()
