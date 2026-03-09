"""Pydantic models for thread functionality."""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ThreadCreate(BaseModel):
    """Schema for creating a thread."""
    name: Optional[str] = None


class ThreadUpdate(BaseModel):
    """Schema for updating a thread."""
    name: str = Field(..., min_length=1, description="New thread name")


class ThreadResponse(BaseModel):
    """Schema for thread response."""
    id: str = Field(..., alias="thread_id")
    name: Optional[str] = None
    last_active: Optional[datetime] = None

    class Config:
        populate_by_name = True


class ThreadListResponse(BaseModel):
    """Schema for thread list response."""
    threads: List[ThreadResponse]
