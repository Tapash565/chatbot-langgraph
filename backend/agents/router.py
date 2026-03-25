"""Router for conditional edges in the agent graph.

This module re-exports LangGraph's built-in tools_condition for routing
decisions in the agent graph.
"""
from langgraph.prebuilt import tools_condition

# Re-export for backwards compatibility
route_tools = tools_condition

__all__ = ["tools_condition", "route_tools"]