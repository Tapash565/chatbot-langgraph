"""Pydantic models for document functionality."""
from typing import Optional
from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""
    filename: str
    documents: int
    chunks: int
    thread_id: str


class DocumentMetadata(BaseModel):
    """Schema for document metadata."""
    thread_id: str
    filename: Optional[str] = None
    documents: int = 0
    chunks: int = 0
    faiss_index_path: Optional[str] = None
