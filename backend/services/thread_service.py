"""Thread service - business logic for thread operations."""
import uuid
from typing import List, Optional

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from backend.db.repositories import thread_repository
from backend.retrieval.retriever import thread_retriever
from backend.memory.thread_state import thread_state_manager
from backend.core.logging import get_logger
from backend.agents.graph import ChatAgent

logger = get_logger(__name__)


class ThreadService:
    """Service for handling thread operations."""

    def __init__(self, agent: Optional[ChatAgent] = None):
        self.agent = agent

    async def create_thread(self, name: Optional[str] = None) -> dict:
        """Create a new thread."""
        thread_id = str(uuid.uuid4())
        thread = thread_repository.create_or_update_thread(
            thread_id=thread_id,
            name=name or "New Chat",
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

    async def get_thread_messages(self, thread_id: str) -> List[dict]:
        """Get chat messages for a thread in frontend-friendly format."""
        if not self.agent:
            return []

        state = await self.agent.aget_state({"configurable": {"thread_id": thread_id}})
        messages = state.values.get("messages", []) if state else []
        result: List[dict] = []

        for index, message in enumerate(messages):
            if isinstance(message, HumanMessage):
                result.append(
                    {
                        "id": f"{thread_id}-user-{index}",
                        "type": "user",
                        "content": message.content,
                    }
                )
            elif isinstance(message, AIMessage) and message.content:
                result.append(
                    {
                        "id": f"{thread_id}-ai-{index}",
                        "type": "ai",
                        "content": message.content,
                    }
                )
            elif isinstance(message, ToolMessage):
                result.append(
                    {
                        "id": f"{thread_id}-tool-{index}",
                        "type": "tool",
                        "content": message.content,
                        "toolName": getattr(message, "name", "tool"),
                    }
                )

        return result
