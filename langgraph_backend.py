"""
LangGraph Backend - Core agent graph, tools, and state management.

This module provides:
- LangGraph chatbot with multi-tool support (search, calculator, stock price, PDF RAG)
- SQLite checkpointing for conversation persistence
- FAISS vector search for PDF document retrieval
- Async-first design with proper concurrency handling
"""

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Any, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.aiosqlite import AsyncSqliteSaver
from langchain_core.tools import tool
from dotenv import load_dotenv
import shutil
import sqlite3
import httpx
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_huggingface import HuggingFaceEndpointEmbeddings
import tempfile
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_community.vectorstores import FAISS
import time
import aiosqlite
import re
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

from backend.core.logging import (
    get_logger,
    configure_logging,
    log_span,
    set_thread_id,
)

# Configure structured logging (guarded against re-running)
configure_logging(level="INFO", json_format=True)
logger = get_logger(__name__)

load_dotenv()

# Thread-local state storage (in-memory, per-process)
_THREAD_RETRIEVERS: Dict[str, Any] = {}
_THREAD_METADATA: Dict[str, dict] = {}

# Database path
DB_PATH = "chatbot.db"
FAISS_INDEX_DIR = "faiss_indices"

# UUID validation regex - thread_ids MUST be valid UUIDs
UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')

# Thread pool for CPU-bound operations
_pdf_executor = ThreadPoolExecutor(max_workers=2)

# =============================================================================
# VALIDATION HELPERS
# =============================================================================


def _validate_thread_id(thread_id: str) -> str:
    """Validate that thread_id is a valid UUID to prevent path traversal."""
    if not UUID_RE.match(thread_id):
        raise ValueError(f"Invalid thread_id format: {thread_id}. Expected UUID.")
    return thread_id


def _validate_stock_symbol(symbol: str) -> Optional[str]:
    """Validate stock symbol to prevent URL injection."""
    symbol = symbol.strip().upper()
    if not re.match(r'^[A-Z]{1,10}$', symbol):
        return None
    return symbol


def _get_faiss_path(thread_id: str) -> str:
    """Get FAISS index path with validation."""
    tid = _validate_thread_id(thread_id)
    os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
    return os.path.join(FAISS_INDEX_DIR, f"{tid}.faiss")


# =============================================================================
# LAZY EMBEDDINGS INITIALIZATION (Thread-safe)
# =============================================================================


class LazyEmbeddings:
    """Lazy-loading wrapper for embeddings with thread-safe initialization."""

    _instance: Optional[HuggingFaceEndpointEmbeddings] = None
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def get(cls) -> HuggingFaceEndpointEmbeddings:
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    cls._instance = HuggingFaceEndpointEmbeddings(
                        model="sentence-transformers/all-MiniLM-L6-v2"
                    )
        return cls._instance


def _get_embeddings() -> HuggingFaceEndpointEmbeddings:
    return LazyEmbeddings.get()


# =============================================================================
# LLM INITIALIZATION
# =============================================================================


llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)

# =============================================================================
# TOOLS
# =============================================================================


search_tool = DuckDuckGoSearchRun(region="us-en")


@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    logger = get_logger(__name__)

    with log_span("tool_calculator", operation=operation):
        logger.info(
            "calculator_invoked",
            operation=operation,
            first_num=first_num,
            second_num=second_num,
        )

        try:
            if operation == "add":
                result = first_num + second_num
            elif operation == "sub":
                result = first_num - second_num
            elif operation == "mul":
                result = first_num * second_num
            elif operation == "div":
                if second_num == 0:
                    logger.error("calculator_error", error="Division by zero")
                    return {"error": "Division by zero is not allowed"}
                result = first_num / second_num
            else:
                logger.warning("calculator_unsupported", operation=operation)
                return {"error": f"Unsupported operation '{operation}'"}

            response = {
                "first_num": first_num,
                "second_num": second_num,
                "operation": operation,
                "result": result,
            }
            logger.info("calculator_success", operation=operation, result=result)
            return response
        except Exception as e:
            logger.error(
                "calculator_exception",
                error=str(e),
                error_type=type(e).__name__,
            )
            return {"error": str(e)}


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA')
    using Alpha Vantage with API key from environment variable.

    Note: This tool runs in a thread pool via LangGraph's ToolNode,
    so synchronous httpx usage is acceptable.
    """
    logger = get_logger(__name__)
    logger.info("stock_price_request", symbol=symbol)

    # Validate symbol to prevent URL injection
    validated_symbol = _validate_stock_symbol(symbol)
    if not validated_symbol:
        logger.warning("stock_price_invalid_symbol", symbol=symbol)
        return {"error": f"Invalid stock symbol: {symbol}", "symbol": symbol}

    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        logger.warning("stock_price_missing_api_key")
        return {
            "error": "ALPHA_VANTAGE_API_KEY environment variable is not set",
            "symbol": validated_symbol,
        }

    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={validated_symbol}&apikey={api_key}"

    try:
        start_time = time.perf_counter()
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "stock_price_success",
            symbol=validated_symbol,
            duration_ms=round(duration_ms, 2),
        )
        return response.json()
    except httpx.TimeoutException:
        logger.error("stock_price_timeout", symbol=validated_symbol)
        return {
            "error": f"Request timed out while fetching stock price for {validated_symbol}",
            "symbol": validated_symbol,
        }
    except httpx.HTTPStatusError as e:
        logger.error("stock_price_http_error", symbol=validated_symbol, error=str(e))
        return {
            "error": f"HTTP error: {str(e)}",
            "symbol": validated_symbol,
        }
    except Exception as e:
        logger.error(
            "stock_price_exception",
            symbol=validated_symbol,
            error=str(e),
            error_type=type(e).__name__,
        )
        return {
            "error": f"Unexpected error: {str(e)}",
            "symbol": validated_symbol,
        }


@tool
def rag_tool(query: str, thread_id: str) -> dict:
    """
    Retrieve relevant information from the uploaded PDF for this chat thread.
    Always include the thread_id when calling this tool.
    """
    logger = get_logger(__name__)

    # Validate thread_id - required parameter, not Optional
    try:
        validated_thread_id = _validate_thread_id(thread_id)
    except ValueError as e:
        logger.error("rag_tool_invalid_thread_id", thread_id=thread_id, error=str(e))
        return {"error": str(e), "query": query}

    set_thread_id(validated_thread_id)

    with log_span(
        "rag_retrieval",
        thread_id=validated_thread_id,
        query_length=len(query),
    ):
        logger.info(
            "rag_tool_invoked", thread_id=validated_thread_id, query=query[:100]
        )

        retriever = _get_retriever(validated_thread_id)
        if retriever is None:
            logger.warning(
                "rag_tool_no_document", thread_id=validated_thread_id
            )
            return {
                "error": "No document indexed for this chat. Upload a PDF first.",
                "query": query,
            }

        start_time = time.perf_counter()
        result = retriever.invoke(query)
        duration_ms = (time.perf_counter() - start_time) * 1000

        context = [doc.page_content for doc in result]
        metadata = [doc.metadata for doc in result]

        logger.info(
            "rag_tool_success",
            thread_id=validated_thread_id,
            results_count=len(result),
            duration_ms=round(duration_ms, 2),
        )

        return {
            "query": query,
            "context": context,
            "metadata": metadata,
            "source_file": _THREAD_METADATA.get(validated_thread_id, {}).get(
                "filename"
            ),
        }


tools = [search_tool, calculator, get_stock_price, rag_tool]

llm_with_tools = llm.bind_tools(tools)


# =============================================================================
# RETRIEVER HELPERS
# =============================================================================


def _get_retriever(thread_id: Optional[str]) -> Optional[Any]:
    """Fetch the retriever for a thread if available."""
    if thread_id and thread_id in _THREAD_RETRIEVERS:
        return _THREAD_RETRIEVERS[thread_id]
    return None


# =============================================================================
# CHAT STATE & GRAPH
# =============================================================================


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def chat_node(state: ChatState, config=None):
    """LLM node that may answer or request a tool call."""
    logger = get_logger(__name__)

    thread_id = None
    if config and isinstance(config, dict):
        thread_id = config.get("configurable", {}).get("thread_id")

    set_thread_id(thread_id if thread_id else "unknown")

    with log_span(
        "llm_invocation", thread_id=thread_id, model="llama-3.3-70b-versatile"
    ):
        system_message = SystemMessage(
            content=(
                "You are a helpful assistant. For questions about the uploaded PDF, call "
                "the `rag_tool` and include the thread_id "
                f"`{thread_id}`. You can also use the web search, stock price, and "
                "calculator tools when helpful. If no document is available, ask the user "
                "to upload a PDF."
            )
        )

        messages = [system_message, *state["messages"]]

        # Log incoming message
        user_message = state["messages"][-1].content if state["messages"] else ""
        logger.info(
            "llm_request",
            thread_id=thread_id,
            message_length=len(user_message),
            message_preview=user_message[:50] if user_message else "",
        )

        start_time = time.perf_counter()
        response = llm_with_tools.invoke(messages, config=config)
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log response
        has_tool_calls = bool(response.tool_calls)
        logger.info(
            "llm_response",
            thread_id=thread_id,
            duration_ms=round(duration_ms, 2),
            has_tool_calls=has_tool_calls,
            response_length=len(response.content),
        )

    return {"messages": [response]}


tool_node = ToolNode(tools)


# =============================================================================
# DATABASE OPERATIONS (Async with connection-per-operation)
# =============================================================================


async def init_db_async():
    """Initialize database tables asynchronously."""
    logger = get_logger(__name__)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS thread_metadata (
                    thread_id TEXT PRIMARY KEY,
                    name TEXT,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS thread_documents (
                    thread_id TEXT PRIMARY KEY,
                    filename TEXT,
                    documents INTEGER,
                    chunks INTEGER,
                    faiss_index_path TEXT
                )
            """
            )
            await db.commit()
        logger.info("database_initialized")
    except Exception as e:
        logger.error(
            "database_init_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


async def get_thread_documents_async() -> list:
    """Get all thread documents from database."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT thread_id, filename, documents, chunks, faiss_index_path FROM thread_documents"
        ) as cursor:
            return await cursor.fetchall()


async def save_thread_document_async(
    thread_id: str, filename: str, documents: int, chunks: int, faiss_path: str
):
    """Save thread document metadata to database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO thread_documents
            (thread_id, filename, documents, chunks, faiss_index_path)
            VALUES (?, ?, ?, ?, ?)
        """,
            (thread_id, filename, documents, chunks, faiss_path),
        )
        await db.commit()


async def delete_thread_documents_async(thread_id: str):
    """Delete thread document metadata from database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM thread_documents WHERE thread_id = ?", (thread_id,)
        )
        await db.commit()


async def get_thread_metadata_async(thread_id: str) -> Optional[dict]:
    """Get thread metadata from database."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT name FROM thread_metadata WHERE thread_id = ?", (thread_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"name": row[0]}
            return None


async def update_thread_async(thread_id: str, name: Optional[str] = None):
    """Update thread metadata in database."""
    async with aiosqlite.connect(DB_PATH) as db:
        if name:
            await db.execute(
                """
                INSERT INTO thread_metadata (thread_id, name, last_active)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(thread_id) DO UPDATE SET name=excluded.name, last_active=CURRENT_TIMESTAMP
            """,
                (thread_id, name),
            )
        else:
            await db.execute(
                """
                INSERT INTO thread_metadata (thread_id, name, last_active)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(thread_id) DO UPDATE SET last_active=CURRENT_TIMESTAMP
            """,
                (thread_id, "Untitled Chat"),
            )
        await db.commit()


async def get_sorted_threads_async() -> list:
    """Get all threads sorted by last active."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT thread_id, name FROM thread_metadata ORDER BY last_active DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"id": row[0], "name": row[1]} for row in rows]


async def delete_thread_metadata_async(thread_id: str):
    """Delete thread metadata from database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM thread_metadata WHERE thread_id = ?", (thread_id,)
        )
        await db.commit()


async def delete_thread_checkpoints_async(thread_id: str):
    """Delete LangGraph checkpoints and writes for a thread."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        await db.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        await db.commit()


async def get_all_thread_ids_async() -> list:
    """Get all thread IDs from database."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT thread_id FROM thread_metadata") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


# =============================================================================
# PDF INGESTION (Async with thread executor for CPU-bound work)
# =============================================================================


def _ingest_pdf_sync(file_bytes: bytes, thread_id: str, filename: Optional[str]) -> dict:
    """Synchronous PDF ingestion - runs in thread pool."""
    logger = get_logger(__name__)
    set_thread_id(thread_id)

    with log_span(
        "pdf_ingestion",
        thread_id=thread_id,
        filename=filename or "unknown",
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

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""]
            )
            chunks = splitter.split_documents(docs)

            logger.info("pdf_chunked", chunk_count=len(chunks))

            start_time = time.perf_counter()
            vector_store = FAISS.from_documents(chunks, _get_embeddings())
            index_duration = time.perf_counter() - start_time

            logger.info(
                "faiss_index_created",
                index_duration_ms=round(index_duration * 1000, 2),
            )

            retriever = vector_store.as_retriever(
                search_type="similarity", search_kwargs={"k": 4}
            )

            # Save FAISS index to disk with validated path
            faiss_path = _get_faiss_path(thread_id)
            vector_store.save_local(faiss_path)

            result = {
                "filename": filename or os.path.basename(temp_path),
                "documents": len(docs),
                "chunks": len(chunks),
                "thread_id": thread_id,
                "faiss_path": faiss_path,
                "retriever": retriever,
            }

            logger.info(
                "pdf_ingestion_complete",
                thread_id=thread_id,
                documents=len(docs),
                chunks=len(chunks),
            )

            return result
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass


async def ingest_pdf(file_bytes: bytes, thread_id: str, filename: Optional[str] = None) -> dict:
    """
    Build a FAISS retriever for the uploaded PDF and store it for the thread.

    Returns a summary dict that can be surfaced in the UI.
    """
    logger = get_logger(__name__)

    # Validate thread_id for security
    validated_thread_id = _validate_thread_id(thread_id)

    # Run CPU-bound PDF processing in thread executor
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        _pdf_executor,
        _ingest_pdf_sync,
        file_bytes,
        validated_thread_id,
        filename,
    )

    # Store in-memory state (after thread executor completes)
    _THREAD_RETRIEVERS[validated_thread_id] = result["retriever"]
    _THREAD_METADATA[validated_thread_id] = {
        "filename": result["filename"],
        "documents": result["documents"],
        "chunks": result["chunks"],
    }

    # Persist to database
    await save_thread_document_async(
        validated_thread_id,
        result["filename"],
        result["documents"],
        result["chunks"],
        result["faiss_path"],
    )

    return {
        "filename": result["filename"],
        "documents": result["documents"],
        "chunks": result["chunks"],
    }


# =============================================================================
# FAISS INDEX RESTORATION
# =============================================================================


async def restore_faiss_indices_async():
    """Load FAISS indices from disk for all threads that have them."""
    logger = get_logger(__name__)
    try:
        rows = await get_thread_documents_async()

        for thread_id, filename, documents, chunks, faiss_index_path in rows:
            if os.path.exists(faiss_index_path):
                try:
                    vector_store = FAISS.load_local(
                        faiss_index_path,
                        _get_embeddings(),
                        allow_dangerous_deserialization=True,
                    )
                    retriever = vector_store.as_retriever(
                        search_type="similarity", search_kwargs={"k": 4}
                    )
                    _THREAD_RETRIEVERS[thread_id] = retriever
                    _THREAD_METADATA[thread_id] = {
                        "filename": filename,
                        "documents": documents,
                        "chunks": chunks,
                    }
                    logger.info(
                        "faiss_index_restored", thread_id=thread_id, filename=filename
                    )
                except Exception as e:
                    logger.error(
                        "faiss_restore_error",
                        thread_id=thread_id,
                        error=str(e),
                    )
    except Exception as e:
        logger.error("faiss_restore_global_error", error=str(e))


# =============================================================================
# LANGGRAPH CHECKPOINTER (Async)
# =============================================================================


# Create async checkpointer - will be initialized in lifespan
checkpointer: Optional[AsyncSqliteSaver] = None
graph: Optional[StateGraph] = None
chatbot = None


async def init_graph_async():
    """Initialize the LangGraph checkpointer and compile the graph."""
    global checkpointer, graph, chatbot

    logger = get_logger(__name__)

    # Initialize database
    await init_db_async()

    # Restore FAISS indices
    await restore_faiss_indices_async()

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _get_embeddings)

    # Create async checkpointer with aiosqlite
    checkpointer = AsyncSqliteSaver.from_conn_string(DB_PATH)

    # Build and compile graph
    graph = StateGraph(ChatState)
    graph.add_node("chat_node", chat_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "chat_node")
    graph.add_conditional_edges("chat_node", tools_condition)
    graph.add_edge("tools", "chat_node")

    chatbot = graph.compile(checkpointer=checkpointer)

    logger.info("langgraph_initialized", status="ready")


def get_chatbot():
    """Get the chatbot instance, raising if not initialized."""
    if chatbot is None:
        raise RuntimeError(
            "Chatbot not initialized. Call init_graph_async() from lifespan first."
        )
    return chatbot


# =============================================================================
# THREAD OPERATIONS
# =============================================================================


async def generate_title_async(thread_id: str):
    """Generate a title for the thread based on recent messages."""
    logger = get_logger(__name__)

    if chatbot is None:
        logger.warning("generate_title_no_chatbot")
        raise RuntimeError("Chatbot not initialized")

    validated_thread_id = _validate_thread_id(thread_id)

    try:
        state = await chatbot.aget_state(
            config={"configurable": {"thread_id": validated_thread_id}}
        )
        messages = state.values.get("messages", []) if state else []
        if not messages:
            return

        # Check if already named
        metadata = await get_thread_metadata_async(validated_thread_id)
        if metadata and metadata.get("name") and metadata["name"] != "Untitled Chat":
            return

        # Sanitize user content - truncate to 200 chars per message
        conversation_text = "\n".join(
            [f"{msg.type}: {msg.content[:200]}" for msg in messages[-4:]]
        )
        prompt = f"Generate a short, 3-5 word title for this conversation summary. Do not use quotes:\n\n{conversation_text}"

        response = await llm.ainvoke(prompt)
        title = response.content.strip().replace('"', '')
        await update_thread_async(validated_thread_id, name=title)
        logger.info("title_generated", thread_id=validated_thread_id, title=title)
    except Exception as e:
        logger.error("title_generation_error", thread_id=validated_thread_id, error=str(e))


async def delete_thread_async(thread_id: str) -> None:
    """Delete a single thread: checkpoints, document index, FAISS files, and in-memory state."""
    logger = get_logger(__name__)

    # Validate thread_id
    validated_thread_id = _validate_thread_id(thread_id)
    tid = str(validated_thread_id)

    # Remove in-memory retriever and metadata
    _THREAD_RETRIEVERS.pop(tid, None)
    _THREAD_METADATA.pop(tid, None)

    # Remove FAISS index from disk
    faiss_path = _get_faiss_path(tid)
    try:
        for ext in [".faiss", ".pkl"]:
            index_file = faiss_path.replace(".faiss", ext)
            if os.path.exists(index_file):
                os.remove(index_file)
    except Exception as e:
        logger.error("faiss_delete_error", thread_id=tid, error=str(e))

    # Remove from database - includes checkpoint cleanup
    await delete_thread_documents_async(tid)
    await delete_thread_metadata_async(tid)
    await delete_thread_checkpoints_async(tid)

    logger.info("thread_deleted", thread_id=tid)


async def rename_thread_async(thread_id: str, name: str) -> None:
    """Rename a thread in the database."""
    logger = get_logger(__name__)

    validated_thread_id = _validate_thread_id(thread_id)
    await update_thread_async(validated_thread_id, name=name.strip())
    logger.info("thread_renamed", thread_id=validated_thread_id, name=name.strip())



def thread_has_document(thread_id: str) -> bool:
    """Check if thread has a document indexed."""
    try:
        validated = _validate_thread_id(thread_id)
        return validated in _THREAD_RETRIEVERS
    except ValueError:
        return False


def thread_document_metadata(thread_id: str) -> dict:
    """Get document metadata for a thread."""
    try:
        validated = _validate_thread_id(thread_id)
        if validated in _THREAD_METADATA:
            return _THREAD_METADATA.get(validated, {})
    except ValueError:
        pass
    return {}