"""
Pydantic schemas for document endpoints.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Base document schema with common fields."""
    title: str = Field(..., description="Document title", min_length=1, max_length=255)
    type: str = Field(..., description="Document type", pattern="^(resume|cover_letter|job_description|interview_notes)$")
    content_text: Optional[str] = Field(None, description="Document content (text or JSON)")
    tags: Optional[List[str]] = Field(default=[], description="List of tag strings")


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""
    pass


class DocumentUpdate(BaseModel):
    """Schema for updating an existing document."""
    title: Optional[str] = Field(None, description="Document title", min_length=1, max_length=255)
    type: Optional[str] = Field(None, description="Document type", pattern="^(resume|cover_letter|job_description|interview_notes)$")
    content_text: Optional[str] = Field(None, description="Document content (text or JSON)")
    tags: Optional[List[str]] = Field(None, description="List of tag strings")


class DocumentResponse(DocumentBase):
    """Schema for document response."""
    id: int = Field(..., description="Document ID")
    user_id: int = Field(..., description="User ID who owns this document")
    created_at: datetime = Field(..., description="Document creation timestamp")
    updated_at: datetime = Field(..., description="Document last update timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "title": "Software Engineer Resume",
                "type": "resume",
                "content_text": "# John Doe\n\nSoftware Engineer...",
                "tags": ["software", "engineer", "python"],
                "created_at": "2026-01-15T10:30:00Z",
                "updated_at": "2026-01-15T10:30:00Z"
            }
        }


class DocumentListResponse(BaseModel):
    """Schema for list of documents response."""
    documents: List[DocumentResponse] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(20, description="Number of items per page")
    
    class Config:
        json_schema_extra = {
            "example": {
                "documents": [],
                "total": 0,
                "page": 1,
                "page_size": 20
            }
        }


class DocumentFilter(BaseModel):
    """Schema for filtering documents."""
    type: Optional[str] = Field(None, description="Filter by document type")
    tags: Optional[List[str]] = Field(None, description="Filter by tags (AND logic)")
    search: Optional[str] = Field(None, description="Search in title and content")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
