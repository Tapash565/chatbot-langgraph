"""Chat service - business logic for chat operations."""
import uuid
from typing import AsyncGenerator, Optional

from backend.agents.graph import ChatAgent
from backend.db.repositories import thread_repository
from backend.core.logging import get_logger, set_thread_id
from langchain_core.messages import HumanMessage

logger = get_logger(__name__)


class ChatService:
    """Service for handling chat operations."""

    def __init__(self, agent: ChatAgent):
        self.agent = agent

    async def create_thread(self, name: Optional[str] = None) -> dict:
        """Create a new chat thread."""
        thread_id = str(uuid.uuid4())
        thread = thread_repository.create_or_update_thread(thread_id, name)

        logger.info("thread_created", thread_id=thread_id, name=name)

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

    async def get_all_threads(self) -> list:
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
        from backend.retrieval.retriever import thread_retriever
        from backend.memory.thread_state import thread_state_manager

        # Remove retriever
        thread_retriever.remove_retriever(thread_id)

        # Remove thread state
        thread_state_manager.remove_state(thread_id)

        # Delete from database
        thread_repository.delete_thread(thread_id)

        logger.info("thread_deleted", thread_id=thread_id)

    async def stream_chat(
        self, message: str, thread_id: Optional[str] = None
    ) -> AsyncGenerator[dict, None]:
        """
        Stream chat response.

        Yields events:
        - ai: AI message content
        - tool_call: Tool being invoked
        - tool: Tool result
        - done: Streaming complete
        """
        # Create or get thread
        if not thread_id:
            thread_data = await self.create_thread()
            thread_id = thread_data["thread_id"]
        else:
            # Update thread activity
            thread_repository.create_or_update_thread(thread_id)

        set_thread_id(thread_id)

        config = {"configurable": {"thread_id": thread_id}}

        # Convert message to LangChain format
        input_data = {"messages": [HumanMessage(content=message)]}

        logger.info(
            "chat_started",
            thread_id=thread_id,
            message_length=len(message),
        )

        # Stream events
        async for event in self.agent.astream(input_data, config):
            for node_name, node_output in event.items():
                if node_name == "chat_node":
                    # Check for tool calls
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tool_call in msg.tool_calls:
                                yield {
                                    "type": "tool_call",
                                    "tool_name": tool_call.get("name"),
                                    "tool_args": tool_call.get("args", {}),
                                }

                        # Yield AI response
                        if hasattr(msg, "content") and msg.content:
                            yield {
                                "type": "ai",
                                "content": msg.content,
                            }

                elif node_name == "tools":
                    # Tool execution results
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        if hasattr(msg, "tool_call_id") and msg.content:
                            yield {
                                "type": "tool",
                                "tool_name": msg.name,
                                "tool_result": msg.content,
                            }

        yield {"type": "done"}

    async def generate_title(self, thread_id: str) -> Optional[str]:
        """Generate a title for a thread based on conversation."""
        from backend.agents.prompts import TITLE_GENERATION_PROMPT
        from backend.core.config import config
        from langchain_groq import ChatGroq

        state = await self.agent.aget_state(config={"configurable": {"thread_id": thread_id}})
        messages = state.values.get("messages", [])

        if not messages:
            return None

        # Check if already titled
        thread = thread_repository.get_thread(thread_id)
        if thread and thread.name and thread.name != "Untitled Chat":
            return None

        # Generate title
        conversation_text = "\n".join(
            [f"{msg.type}: {msg.content}" for msg in messages[-4:]]
        )
        prompt = TITLE_GENERATION_PROMPT.format(
            conversation_text=conversation_text
        )

        try:
            llm = ChatGroq(model=config.GROQ_MODEL, temperature=0.7)
            response = await llm.ainvoke(prompt)
            title = response.content.strip().replace('"', '')
            await self.rename_thread(thread_id, title)
            return title
        except Exception as e:
            logger.error("title_generation_error", thread_id=thread_id, error=str(e))
            return None
