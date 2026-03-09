"""Pydantic models for chat functionality."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Schema for creating a message."""
    message: str
    thread_id: Optional[str] = None


class MessageResponse(BaseModel):
    """Schema for message response."""
    content: str
    role: str = "assistant"
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatStreamRequest(BaseModel):
    """Schema for chat streaming request."""
    message: str = Field(..., description="User message")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation")


class ChatStreamResponse(BaseModel):
    """Schema for chat streaming response."""
    type: str = Field(..., description="Event type: ai, tool_call, tool, done, error")
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_result: Optional[Any] = None


class ToolCallEvent(BaseModel):
    """Schema for tool call event."""
    tool_name: str
    tool_args: Dict[str, Any]
