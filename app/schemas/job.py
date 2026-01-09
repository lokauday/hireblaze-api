"""
Pydantic schemas for job endpoints.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class JobBase(BaseModel):
    """Base job schema with common fields."""
    company: str = Field(..., description="Company name", min_length=1, max_length=255)
    title: str = Field(..., description="Job title", min_length=1, max_length=255)
    url: Optional[str] = Field(None, description="Job posting URL")
    status: str = Field(
        default="applied",
        description="Job application status",
        pattern="^(saved|applied|interviewing|offer|rejected|withdrawn)$"
    )
    notes: Optional[str] = Field(None, description="Notes about this job application")
    applied_at: Optional[datetime] = Field(None, description="Date applied")


class JobCreate(JobBase):
    """Schema for creating a new job."""
    pass


class JobUpdate(BaseModel):
    """Schema for updating an existing job."""
    company: Optional[str] = Field(None, description="Company name", min_length=1, max_length=255)
    title: Optional[str] = Field(None, description="Job title", min_length=1, max_length=255)
    url: Optional[str] = Field(None, description="Job posting URL")
    status: Optional[str] = Field(
        None,
        description="Job application status",
        pattern="^(saved|applied|interviewing|offer|rejected|withdrawn)$"
    )
    notes: Optional[str] = Field(None, description="Notes about this job application")
    applied_at: Optional[datetime] = Field(None, description="Date applied")


class JobResponse(JobBase):
    """Schema for job response."""
    id: int = Field(..., description="Job ID")
    user_id: int = Field(..., description="User ID who owns this job")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Job last update timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "company": "Tech Corp",
                "title": "Senior Software Engineer",
                "url": "https://example.com/job/123",
                "status": "applied",
                "notes": "Applied on 2026-01-15. Follow up next week.",
                "applied_at": "2026-01-15T10:00:00Z",
                "created_at": "2026-01-15T09:00:00Z",
                "updated_at": "2026-01-15T10:00:00Z"
            }
        }


class JobListResponse(BaseModel):
    """Schema for list of jobs response."""
    jobs: list[JobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(20, description="Number of items per page")
    
    class Config:
        json_schema_extra = {
            "example": {
                "jobs": [],
                "total": 0,
                "page": 1,
                "page_size": 20
            }
        }


class JobFilter(BaseModel):
    """Schema for filtering jobs."""
    status: Optional[str] = Field(None, description="Filter by status")
    company: Optional[str] = Field(None, description="Filter by company name (partial match)")
    search: Optional[str] = Field(None, description="Search in company, title, and notes")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
