"""
Pydantic schemas for history/activity endpoints.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class HistoryEntryResponse(BaseModel):
    """Schema for a single history entry."""
    id: int = Field(..., description="History entry ID")
    feature: str = Field(..., description="Feature name (ats_scan, resume_tailor, cover_letter, jd_parse, document_create, etc.)")
    created_at: datetime = Field(..., description="When this action occurred")
    amount: int = Field(default=1, description="Number of credits used")
    document_id: Optional[int] = Field(None, description="Related document ID if applicable")
    job_id: Optional[int] = Field(None, description="Related job ID if applicable")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "feature": "resume_tailor",
                "created_at": "2026-01-15T10:30:00Z",
                "amount": 1,
                "document_id": 5,
                "job_id": None
            }
        }


class HistoryListResponse(BaseModel):
    """Schema for history list response."""
    entries: list[HistoryEntryResponse] = Field(..., description="List of history entries")
    total: int = Field(..., description="Total number of entries")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(20, description="Number of items per page")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entries": [],
                "total": 0,
                "page": 1,
                "page_size": 20
            }
        }


class HistoryFilter(BaseModel):
    """Schema for filtering history."""
    feature: Optional[str] = Field(None, description="Filter by feature name")
    document_id: Optional[int] = Field(None, description="Filter by document ID")
    job_id: Optional[int] = Field(None, description="Filter by job ID")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
