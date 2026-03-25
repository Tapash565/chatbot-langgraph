"""RAG (Retrieval Augmented Generation) tool."""
import time
from typing import Optional
from langchain_core.tools import tool

from backend.retrieval.retriever import thread_retriever
from backend.retrieval.chunker import document_chunker
from backend.retrieval.vector_store import vector_store_manager
from backend.db.repositories import thread_repository, ThreadDocument
from backend.core.logging import get_logger, log_span, set_thread_id

logger = get_logger(__name__)


@tool
def rag_tool(query: str, thread_id: Optional[str] = None) -> dict:
    """
    Retrieve relevant information from the uploaded PDF for this chat thread.

    Args:
        query: The search query
        thread_id: The thread ID for the conversation

    Returns:
        A dictionary with query results, context, and metadata
    """
    thread_id = thread_id or "unknown"
    set_thread_id(thread_id)

    with log_span(
        "rag_retrieval", thread_id=thread_id, query_length=len(query)
    ):
        logger.info("rag_tool_invoked", thread_id=thread_id, query=query[:100])

        retriever = thread_retriever.get_retriever(thread_id)
        if retriever is None:
            logger.warning("rag_tool_no_document", thread_id=thread_id)
            return {
                "error": "No document indexed for this chat. Upload a PDF first.",
                "query": query,
            }

        start_time = time.perf_counter()
        result = retriever.invoke(query)
        duration_ms = (time.perf_counter() - start_time) * 1000

        context = [doc.page_content for doc in result]
        metadata = [doc.metadata for doc in result]

        # Get source filename from database
        doc_meta = thread_repository.get_document_metadata(thread_id)
        source_file = doc_meta.filename if doc_meta else None

        logger.info(
            "rag_tool_success",
            thread_id=thread_id,
            results_count=len(result),
            duration_ms=round(duration_ms, 2),
        )

        return {
            "query": query,
            "context": context,
            "metadata": metadata,
            "source_file": source_file,
        }


@tool
def ingest_pdf(file_bytes: bytes, thread_id: str, filename: Optional[str] = None) -> dict:
    """
    Build a FAISS retriever for the uploaded PDF and store it for the thread.

    Args:
        file_bytes: PDF file content as bytes
        thread_id: The thread ID for the conversation
        filename: Optional filename

    Returns:
        A summary dictionary with document stats
    """
    import tempfile
    from langchain_community.document_loaders import PyPDFLoader

    thread_id = str(thread_id)
    set_thread_id(thread_id)

    with log_span(
        "pdf_ingestion", thread_id=thread_id, filename=filename or "unknown"
    ):
        if not file_bytes:
            raise ValueError("No bytes received for ingestion.")

        logger.info("pdf_ingestion_start", thread_id=thread_id, filename=filename)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        try:
            start_time = time.perf_counter()
            loader = PyPDFLoader(temp_path)
            docs = loader.load()
            load_duration = time.perf_counter() - start_time

            logger.info(
                "pdf_loaded",
                document_count=len(docs),
                load_duration_ms=round(load_duration * 1000, 2),
            )

            # Chunk documents
            chunks = document_chunker.chunk_documents(docs)

            logger.info("pdf_chunked", chunk_count=len(chunks))

            # Create vector store
            start_time = time.perf_counter()
            vector_store = vector_store_manager.create_vector_store(
                chunks, thread_id
            )
            index_duration = time.perf_counter() - start_time

            logger.info(
                "faiss_index_created",
                thread_id=thread_id,
                index_duration_ms=round(index_duration * 1000, 2),
            )

            # Create retriever and store in memory
            retriever = vector_store.as_retriever(
                search_type="similarity", search_kwargs={"k": 4}
            )
            thread_retriever.set_retriever(thread_id, retriever)

            # Save metadata to database
            doc = ThreadDocument(
                thread_id=thread_id,
                filename=filename or "uploaded.pdf",
                documents=len(docs),
                chunks=len(chunks),
                faiss_index_path=vector_store_manager.get_index_path(thread_id),
            )
            thread_repository.save_document_metadata(doc)

            result = {
                "filename": filename or "uploaded.pdf",
                "documents": len(docs),
                "chunks": len(chunks),
            }

            logger.info(
                "pdf_ingestion_complete",
                thread_id=thread_id,
                documents=len(docs),
                chunks=len(chunks),
            )

            return result
        finally:
            # Clean up temp file
            try:
                import os
                os.remove(temp_path)
            except OSError:
                pass
