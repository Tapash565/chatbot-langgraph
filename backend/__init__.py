"""Backend module - Modular LangGraph Chatbot Backend.

This module provides a production-ready chatbot with:
- LangGraph orchestration with persistent checkpointing
- Multi-tool LLM using Groq
- FastAPI backend with SSE streaming
- FAISS vector search for PDF RAG
- SQLite for conversation persistence
"""

from backend.core.config import config, Config
from backend.core.logging import (
    get_logger,
    configure_logging,
    log_span,
    set_thread_id,
    get_correlation_id,
)
from backend.db import (
    DatabaseSession,
    db_session,
    get_db,
    ThreadRepository,
    ThreadMetadata,
    ThreadDocument,
    thread_repository,
)
from backend.agents import ChatAgent, get_system_prompt
from backend.tools import tools
from backend.services import ChatService, ThreadService, DocumentService

__version__ = "1.0.0"

__all__ = [
    # Config
    "config",
    "Config",
    # Logging
    "get_logger",
    "configure_logging",
    "log_span",
    "set_thread_id",
    "get_correlation_id",
    # Database
    "DatabaseSession",
    "db_session",
    "get_db",
    "ThreadRepository",
    "ThreadMetadata",
    "ThreadDocument",
    "thread_repository",
    # Agents
    "ChatAgent",
    "get_system_prompt",
    # Tools
    "tools",
    # Services
    "ChatService",
    "ThreadService",
    "DocumentService",
]
