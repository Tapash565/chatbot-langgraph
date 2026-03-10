"""Chat node for the LangGraph agent."""
import time
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph.message import add_messages

from backend.agents.prompts import get_system_prompt
from backend.core.logging import get_logger, log_span, set_thread_id

logger = get_logger(__name__)


class ChatState(TypedDict):
    """State for the chat graph."""
    messages: Annotated[list[BaseMessage], add_messages]


def create_chat_node(llm_with_tools):
    """
    Factory function to create a chat node with the given LLM.

    Args:
        llm_with_tools: LLM bound with tools

    Returns:
        Chat node function
    """

    def chat_node(state: ChatState, config=None) -> dict:
        """LLM node that may answer or request a tool call."""
        thread_id = None
        if config and isinstance(config, dict):
            thread_id = config.get("configurable", {}).get("thread_id")

        set_thread_id(thread_id if thread_id else "unknown")

        with log_span(
            "llm_invocation",
            thread_id=thread_id,
            model="llama-3.3-70b-versatile",
        ):
            system_message = SystemMessage(content=get_system_prompt(thread_id))
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
                response_length=len(response.content) if response.content else 0,
            )

        return {"messages": [response]}

    return chat_node
