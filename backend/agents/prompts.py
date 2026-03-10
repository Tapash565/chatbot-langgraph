"""Prompt templates for the agent."""
from typing import Optional


def get_system_prompt(thread_id: Optional[str] = None) -> str:
    """
    Generate the system prompt for the chat node.

    Args:
        thread_id: Optional thread ID for context

    Returns:
        System prompt string
    """
    base_prompt = """You are a helpful assistant. You have access to the following tools:
- web_search: Search the web for information
- calculator: Perform arithmetic calculations
- get_stock_price: Get stock price information
- rag_tool: Answer questions about uploaded PDF documents

When a user asks about a PDF document, use the rag_tool with the thread_id to retrieve relevant information.
If no document is available, ask the user to upload a PDF.
"""

    if thread_id:
        base_prompt += f"\nCurrent thread_id: {thread_id}"

    return base_prompt


# Additional prompt templates can be added here
TITLE_GENERATION_PROMPT = """Generate a short, 3-5 word title for this conversation summary. Do not use quotes:

{conversation_text}
"""
