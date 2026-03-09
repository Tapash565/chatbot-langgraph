"""Document service - business logic for document operations."""
from typing import Optional
import io

from backend.tools.rag_tool import ingest_pdf
from backend.retrieval.retriever import thread_retriever
from backend.db.repositories import thread_repository
from backend.core.logging import get_logger

logger = get_logger(__name__)


class DocumentService:
    """Service for handling document operations."""

    async def upload_pdf(
        self, file_content: bytes, thread_id: str, filename: Optional[str] = None
    ) -> dict:
        """
        Upload and index a PDF document.

        Args:
            file_content: PDF file content as bytes
            thread_id: Thread ID for the conversation
            filename: Optional filename

        Returns:
            Document metadata
        """
        logger.info(
            "pdf_upload_started",
            thread_id=thread_id,
            filename=filename,
            file_size=len(file_content),
        )

        # Use the tool directly (it's synchronous)
        result = ingest_pdf.invoke({
            "file_bytes": file_content,
            "thread_id": thread_id,
            "filename": filename,
        })

        if "error" in result:
            logger.error(
                "pdf_upload_error",
                thread_id=thread_id,
                error=result["error"],
            )
            raise ValueError(result["error"])

        logger.info(
            "pdf_upload_complete",
            thread_id=thread_id,
            filename=result.get("filename"),
            documents=result.get("documents"),
            chunks=result.get("chunks"),
        )

        return {
            "filename": result.get("filename"),
            "documents": result.get("documents"),
            "chunks": result.get("chunks"),
            "thread_id": thread_id,
        }

    async def get_document_metadata(self, thread_id: str) -> Optional[dict]:
        """Get document metadata for a thread."""
        # Check memory first
        from backend.retrieval.retriever import thread_retriever

        if thread_retriever.has_retriever(thread_id):
            doc = thread_repository.get_document_metadata(thread_id)
            if doc:
                return {
                    "thread_id": doc.thread_id,
                    "filename": doc.filename,
                    "documents": doc.documents,
                    "chunks": doc.chunks,
                    "faiss_index_path": doc.faiss_index_path,
                }

        return None

    async def delete_document(self, thread_id: str) -> bool:
        """Delete a document and its index for a thread."""
        thread_retriever.remove_retriever(thread_id)
        logger.info("document_deleted", thread_id=thread_id)
        return True


# Global document service instance (will be initialized with agent)
document_service: Optional[DocumentService] = None


def get_document_service(agent) -> DocumentService:
    """Get or create document service."""
    global document_service
    if document_service is None:
        document_service = DocumentService()
    return document_service
