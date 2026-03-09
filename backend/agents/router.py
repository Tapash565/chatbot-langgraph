"""Router for conditional edges in the agent graph."""
from typing import Literal
from langgraph.prebuilt import tools_condition
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage


def route_tools(
    state: dict,
) -> Literal["tools", "__end__"]:
    """
    Route to tools if there are tool calls, otherwise end.

    Args:
        state: Current graph state

    Returns:
        Next node to route to
    """
    messages = state.get("messages", [])
    if not messages:
        return "__end__"

    last_message = messages[-1]
    if isinstance(last_message, BaseMessage) and last_message.tool_calls:
        return "tools"

    return "__end__"
