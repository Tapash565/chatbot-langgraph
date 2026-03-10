"""Tests for tool routing behavior in graph router."""
from langchain_core.messages import AIMessage, HumanMessage

from backend.agents.router import route_tools


def test_route_tools_returns_end_for_empty_state():
    """Empty message state should route to graph end."""
    assert route_tools({"messages": []}) == "__end__"


def test_route_tools_returns_end_for_non_tool_message():
    """Human/AI text without tool calls should route to graph end."""
    state = {"messages": [HumanMessage(content="hello"), AIMessage(content="hi")]}
    assert route_tools(state) == "__end__"


def test_route_tools_returns_tools_for_tool_call_message():
    """AI message with tool calls should route to tools node."""
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "calculator",
                        "args": {"first_num": 1, "second_num": 2, "operation": "add"},
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            )
        ]
    }
    assert route_tools(state) == "tools"
