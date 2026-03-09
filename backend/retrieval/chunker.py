"""Document chunking utilities."""
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from backend.core.logging import get_logger

logger = get_logger(__name__)


class DocumentChunker:
    """Handles document chunking for RAG."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.separators,
        )

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks."""
        if not documents:
            return []

        chunks = self._splitter.split_documents(documents)

        logger.info(
            "documents_chunked",
            original_count=len(documents),
            chunk_count=len(chunks),
        )

        return chunks

    def chunk_text(self, text: str, metadata: dict = None) -> List[Document]:
        """Split raw text into chunks."""
        chunks = self._splitter.split_text(text)

        documents = [
            Document(page_content=chunk, metadata=metadata or {})
            for chunk in chunks
        ]

        logger.info("text_chunked", text_length=len(text), chunk_count=len(documents))

        return documents


# Global chunker instance
document_chunker = DocumentChunker()
