"""LangGraph agent orchestration."""
from typing import Optional
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.agents.nodes import ChatState, create_chat_node
from backend.agents.router import route_tools
from backend.tools import tools
from backend.core.logging import get_logger
from backend.db.session import db_session

logger = get_logger(__name__)


class ChatAgent:
    """LangGraph-based chat agent with persistent state."""

    def __init__(self, llm, llm_with_tools):
        self.llm = llm
        self.llm_with_tools = llm_with_tools
        self._graph: Optional[StateGraph] = None
        self._checkpointer: Optional[AsyncSqliteSaver] = None
        self._chatbot = None

    @property
    def graph(self) -> StateGraph:
        """Get or create the state graph."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    @property
    def checkpointer(self) -> Optional[AsyncSqliteSaver]:
        """Get checkpointer if already initialized."""
        return self._checkpointer

    async def _get_checkpointer(self) -> AsyncSqliteSaver:
        """Get or create the async SQLite checkpointer."""
        if self._checkpointer is None:
            conn = await db_session.get_async_connection()
            self._checkpointer = AsyncSqliteSaver(conn=conn)
        return self._checkpointer

    async def _get_chatbot(self):
        """Get compiled chatbot."""
        if self._chatbot is None:
            checkpointer = await self._get_checkpointer()
            self._chatbot = self.graph.compile(checkpointer=checkpointer)
        return self._chatbot

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        graph = StateGraph(ChatState)

        # Create chat node with bound LLM
        chat_node = create_chat_node(self.llm, self.llm_with_tools)
        tool_node = ToolNode(tools)

        # Add nodes
        graph.add_node("chat_node", chat_node)
        graph.add_node("tools", tool_node)

        # Set edges
        graph.add_edge(START, "chat_node")
        graph.add_conditional_edges(
            "chat_node",
            route_tools,
            {
                "tools": "tools",
                "__end__": END,
            }
        )
        graph.add_edge("tools", "chat_node")

        return graph

    async def aget_state(self, config: dict):
        """Get current state for a thread."""
        chatbot = await self._get_chatbot()
        return await chatbot.aget_state(config)

    async def ainvoke(self, input_data: dict, config: dict):
        """Invoke the agent asynchronously."""
        chatbot = await self._get_chatbot()
        return await chatbot.ainvoke(input_data, config)

    async def astream(self, input_data: dict, config: dict):
        """Stream agent responses."""
        chatbot = await self._get_chatbot()
        async for event in chatbot.astream(input_data, config):
            yield event
