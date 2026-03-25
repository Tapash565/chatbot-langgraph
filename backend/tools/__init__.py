"""Tools layer - LLM tools for the agent."""
from backend.tools.calculator import calculator
from backend.tools.web_search import web_search
from backend.tools.stock_price import get_stock_price
from backend.tools.rag_tool import rag_tool, ingest_pdf

# Export all tools as a list
tools = [
    web_search,
    calculator,
    get_stock_price,
    rag_tool,
]

__all__ = [
    "calculator",
    "web_search",
    "get_stock_price",
    "rag_tool",
    "ingest_pdf",
    "tools",
]
