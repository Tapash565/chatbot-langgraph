from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Any, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.tools import tool
from dotenv import load_dotenv
import shutil
import sqlite3
import requests
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_huggingface import HuggingFaceEndpointEmbeddings
import tempfile
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_community.vectorstores import FAISS
import time

# Import observability
from observability.logging_config import (
    get_logger,
    configure_logging,
    log_span,
    set_thread_id,
    get_correlation_id,
    generate_correlation_id,
)

# Initialize structured logging
configure_logging(level="INFO", json_format=True)
logger = get_logger(__name__)

load_dotenv()

_THREAD_RETRIEVERS: Dict[str, Any] = {}
_THREAD_METADATA: Dict[str, dict] = {}

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
embeddings = HuggingFaceEndpointEmbeddings(model="sentence-transformers/all-MiniLM-L6-v2")

def _get_retriever(thread_id: Optional[str]):
    """Fetch the retriever for a thread if available."""
    if thread_id and thread_id in _THREAD_RETRIEVERS:
        return _THREAD_RETRIEVERS[thread_id]
    return None

def ingest_pdf(file_bytes: bytes, thread_id: str, filename: Optional[str] = None) -> dict:
    """
    Build a FAISS retriever for the uploaded PDF and store it for the thread.

    Returns a summary dict that can be surfaced in the UI.
    """
    logger = get_logger(__name__)
    set_thread_id(thread_id)

    with log_span("pdf_ingestion", thread_id=thread_id, filename=filename or "unknown"):
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

            logger.info("pdf_loaded", document_count=len(docs), load_duration_ms=round(load_duration * 1000, 2))

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""]
            )
            chunks = splitter.split_documents(docs)

            logger.info("pdf_chunked", chunk_count=len(chunks))

            start_time = time.perf_counter()
            vector_store = FAISS.from_documents(chunks, embeddings)
            index_duration = time.perf_counter() - start_time

            logger.info("faiss_index_created", index_duration_ms=round(index_duration * 1000, 2))

            retriever = vector_store.as_retriever(
                search_type="similarity", search_kwargs={"k": 4}
            )

            # Save FAISS index to disk
            os.makedirs("faiss_indices", exist_ok=True)
            faiss_path = f"faiss_indices/{thread_id}.faiss"
            vector_store.save_local(faiss_path)

            _THREAD_RETRIEVERS[str(thread_id)] = retriever
            _THREAD_METADATA[str(thread_id)] = {
                "filename": filename or os.path.basename(temp_path),
                "documents": len(docs),
                "chunks": len(chunks),
            }

            # Persist to database
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO thread_documents
                (thread_id, filename, documents, chunks, faiss_index_path)
                VALUES (?, ?, ?, ?, ?)
            ''', (str(thread_id), filename or os.path.basename(temp_path),
                  len(docs), len(chunks), faiss_path))
            conn.commit()

            result = {
                "filename": filename or os.path.basename(temp_path),
                "documents": len(docs),
                "chunks": len(chunks),
            }

            logger.info("pdf_ingestion_complete", thread_id=thread_id,
                        documents=len(docs), chunks=len(chunks))

            return result
        finally:
            # The FAISS store keeps copies of the text, so the temp file is safe to remove.
            try:
                os.remove(temp_path)
            except OSError:
                pass
# Define tools
# Tools
search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    logger = get_logger(__name__)

    with log_span("tool_calculator", operation=operation):
        logger.info("calculator_invoked", operation=operation,
                    first_num=first_num, second_num=second_num)

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

            response = {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
            logger.info("calculator_success", operation=operation, result=result)
            return response
        except Exception as e:
            logger.error("calculator_exception", error=str(e), error_type=type(e).__name__)
            return {"error": str(e)}


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA')
    using Alpha Vantage with API key from environment variable.
    """
    logger = get_logger(__name__)
    logger.info("stock_price_request", symbol=symbol)

    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        logger.warning("stock_price_missing_api_key")
        return {
            "error": "ALPHA_VANTAGE_API_KEY environment variable is not set",
            "symbol": symbol,
        }

    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"

    try:
        start_time = time.perf_counter()
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info("stock_price_success", symbol=symbol, duration_ms=round(duration_ms, 2))
        return r.json()
    except requests.exceptions.Timeout:
        logger.error("stock_price_timeout", symbol=symbol)
        return {
            "error": f"Request timed out while fetching stock price for {symbol}",
            "symbol": symbol,
        }
    except requests.exceptions.RequestException as e:
        logger.error("stock_price_error", symbol=symbol, error=str(e))
        return {
            "error": f"Request failed: {str(e)}",
            "symbol": symbol,
        }
    except Exception as e:
        logger.error("stock_price_exception", symbol=symbol, error=str(e), error_type=type(e).__name__)
        return {
            "error": f"Unexpected error: {str(e)}",
            "symbol": symbol,
        }

@tool
def rag_tool(query: str, thread_id: Optional[str] = None) -> dict:
    """
    Retrieve relevant information from the uploaded PDF for this chat thread.
    Always include the thread_id when calling this tool.
    """
    logger = get_logger(__name__)
    set_thread_id(thread_id if thread_id else "unknown")

    with log_span("rag_retrieval", thread_id=thread_id or "unknown", query_length=len(query)):
        logger.info("rag_tool_invoked", thread_id=thread_id, query=query[:100])

        retriever = _get_retriever(thread_id)
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

        logger.info("rag_tool_success", thread_id=thread_id,
                   results_count=len(result), duration_ms=round(duration_ms, 2))

        return {
            "query": query,
            "context": context,
            "metadata": metadata,
            "source_file": _THREAD_METADATA.get(str(thread_id), {}).get("filename"),
        }


tools = [search_tool, calculator, get_stock_price, rag_tool]

llm_with_tools = llm.bind_tools(tools)



class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState, config=None):
    """LLM node that may answer or request a tool call."""
    logger = get_logger(__name__)

    thread_id = None
    if config and isinstance(config, dict):
        thread_id = config.get("configurable", {}).get("thread_id")

    set_thread_id(thread_id if thread_id else "unknown")

    with log_span("llm_invocation", thread_id=thread_id, model="llama-3.3-70b-versatile"):
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
        logger.info("llm_request", thread_id=thread_id,
                  message_length=len(user_message), message_preview=user_message[:50] if user_message else "")

        start_time = time.perf_counter()
        response = llm_with_tools.invoke(messages, config=config)
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log response
        has_tool_calls = bool(response.tool_calls)
        logger.info("llm_response", thread_id=thread_id,
                   duration_ms=round(duration_ms, 2),
                   has_tool_calls=has_tool_calls,
                   response_length=len(response.content))

    return {"messages": [response]}

tool_node = ToolNode(tools)

conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)
# Checkpointer
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

chatbot = graph.compile(checkpointer=checkpointer)

def init_db():
    logger = get_logger(__name__)
    try:
        cursor = conn.cursor()
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
        conn.commit()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_error", error=str(e), error_type=type(e).__name__)
        print(f"DB Init Error: {e}")

def restore_faiss_indices():
    """Load FAISS indices from disk for all threads that have them."""
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT thread_id, filename, documents, chunks, faiss_index_path FROM thread_documents')
        rows = cursor.fetchall()
        
        for thread_id, filename, documents, chunks, faiss_index_path in rows:
            if os.path.exists(faiss_index_path):
                try:
                    vector_store = FAISS.load_local(
                        faiss_index_path, 
                        embeddings, 
                        allow_dangerous_deserialization=True
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
                except Exception as e:
                    print(f"Failed to restore FAISS index for thread {thread_id}: {e}")
    except Exception as e:
        print(f"Restore FAISS Error: {e}")

init_db()
restore_faiss_indices()

def update_thread(thread_id, name=None):
    cursor = conn.cursor()
    if name:
        cursor.execute('''
            INSERT INTO thread_metadata (thread_id, name, last_active) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(thread_id) DO UPDATE SET name=excluded.name, last_active=CURRENT_TIMESTAMP
        ''', (thread_id, name))
    else:
        cursor.execute('''
            INSERT INTO thread_metadata (thread_id, name, last_active) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(thread_id) DO UPDATE SET last_active=CURRENT_TIMESTAMP
        ''', (thread_id, "Untitled Chat"))
    conn.commit()

def get_sorted_threads():
    cursor = conn.cursor()
    # Backfill if needed (simple check)
    all_checkpoints = set()
    for c in checkpointer.list(None):
        all_checkpoints.add(c.config['configurable']['thread_id'])
    
    for tid in all_checkpoints:
        cursor.execute("SELECT 1 FROM thread_metadata WHERE thread_id = ?", (tid,))
        if not cursor.fetchone():
            update_thread(tid)
            
    cursor.execute("SELECT thread_id, name FROM thread_metadata ORDER BY last_active DESC")
    return [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

def generate_title(thread_id):
    messages = chatbot.get_state(config={'configurable': {'thread_id': thread_id}}).values.get('messages', [])
    if not messages:
        return
    
    # Simple check to see if title is already set to something custom (heuristic: distinctive name check could be complex, 
    # so we just rely on the caller to only call this when appropriate, or check if it's the default name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM thread_metadata WHERE thread_id = ?", (thread_id,))
    row = cursor.fetchone()
    if row and row[0] and row[0] != "Untitled Chat":
        return # Already named
        
    conversation_text = "\n".join([f"{msg.type}: {msg.content}" for msg in messages[-4:]]) # Last few messages
    prompt = f"Generate a short, 3-5 word title for this conversation summary. Do not use quotes:\n\n{conversation_text}"
    
    try:
        response = llm.invoke(prompt)
        title = response.content.strip().replace('"', '')
        update_thread(thread_id, name=title)
    except Exception as e:
        print(f"Title Gen Error: {e}")

def delete_chats():
    cursor = conn.cursor()
    cursor.execute("DELETE FROM thread_metadata")
    cursor.execute("DELETE FROM checkpoints")
    cursor.execute("DELETE FROM writes")
    conn.commit()


def delete_thread(thread_id: str) -> None:
    """Delete a single thread: checkpoints, document index, FAISS files, and in-memory state."""
    tid = str(thread_id)

    # Remove in-memory retriever and metadata
    _THREAD_RETRIEVERS.pop(tid, None)
    _THREAD_METADATA.pop(tid, None)

    # Remove FAISS index directory from disk
    faiss_path = f"faiss_indices/{tid}.faiss"
    if os.path.exists(faiss_path):
        try:
            shutil.rmtree(faiss_path)
        except Exception as e:
            print(f"Failed to remove FAISS index for {tid}: {e}")

    # Remove from database
    cursor = conn.cursor()
    cursor.execute("DELETE FROM thread_documents WHERE thread_id = ?", (tid,))
    cursor.execute("DELETE FROM thread_metadata WHERE thread_id = ?", (tid,))
    cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (tid,))
    cursor.execute("DELETE FROM writes WHERE thread_id = ?", (tid,))
    conn.commit()


def rename_thread(thread_id: str, name: str) -> None:
    """Rename a thread in the database."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE thread_metadata SET name = ? WHERE thread_id = ?",
        (name.strip(), str(thread_id)),
    )
    conn.commit()


def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)


def thread_has_document(thread_id: str) -> bool:
    return str(thread_id) in _THREAD_RETRIEVERS


def thread_document_metadata(thread_id: str) -> dict:
    """Get document metadata from memory or database."""
    # Check memory first
    if str(thread_id) in _THREAD_METADATA:
        return _THREAD_METADATA.get(str(thread_id), {})
    
    # Check database
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT filename, documents, chunks FROM thread_documents WHERE thread_id = ?',
            (str(thread_id),)
        )
        row = cursor.fetchone()
        if row:
            return {
                "filename": row[0],
                "documents": row[1],
                "chunks": row[2],
            }
    except Exception as e:
        print(f"Error fetching document metadata: {e}")
    
    return {}