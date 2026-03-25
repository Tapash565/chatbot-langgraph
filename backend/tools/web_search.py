"""Web search tool using DuckDuckGo."""
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

from backend.core.logging import get_logger

logger = get_logger(__name__)

# Initialize the search tool
search_tool = DuckDuckGoSearchRun(region="us-en")


@tool
def web_search(query: str) -> str:
    """
    Search the web for information using DuckDuckGo.

    Args:
        query: The search query

    Returns:
        Search results as a string
    """
    logger.info("web_search_invoked", query=query[:100])

    try:
        result = search_tool.run(query)
        logger.info("web_search_success", query=query[:50], result_length=len(result))
        return result
    except Exception as e:
        logger.error("web_search_error", query=query[:50], error=str(e))
        return f"Search error: {str(e)}"
