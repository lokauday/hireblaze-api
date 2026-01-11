"""
Pydantic schemas for AI endpoints.
"""
from typing import Optional
from pydantic import BaseModel, Field


class JobPackRequest(BaseModel):
    """Request model for job pack generation."""
    resume_id: Optional[int] = Field(None, description="Resume ID from database")
    job_id: Optional[int] = Field(None, description="Job posting ID from database")
    resume_text: Optional[str] = Field(None, description="Resume text content")
    jd_text: Optional[str] = Field(None, description="Job description text")
    company: Optional[str] = Field(None, description="Company name")
    job_title: Optional[str] = Field(None, description="Job title")
    
    class Config:
        json_schema_extra = {
            "example": {
                "resume_id": 1,
                "job_id": 2,
                "company": "Tech Corp",
                "job_title": "Senior Software Engineer"
            }
        }


class JobPackResponse(BaseModel):
    """Response model for job pack generation."""
    resume_doc_id: Optional[int] = Field(None, description="ID of generated resume document")
    cover_letter_doc_id: Optional[int] = Field(None, description="ID of generated cover letter document")
    outreach_doc_id: Optional[int] = Field(None, description="ID of generated outreach message document")
    interview_pack_doc_id: Optional[int] = Field(None, description="ID of generated interview pack document")
    resume_preview: str = Field(default="", description="Preview text of generated resume")
    cover_letter_preview: str = Field(default="", description="Preview text of generated cover letter")
    outreach_preview: str = Field(default="", description="Preview text of generated outreach message")
    interview_pack_preview: str = Field(default="", description="Preview text of generated interview pack")
    
    class Config:
        json_schema_extra = {
            "example": {
                "resume_doc_id": 101,
                "cover_letter_doc_id": 102,
                "outreach_doc_id": 103,
                "interview_pack_doc_id": 104,
                "resume_preview": "Senior Software Engineer...",
                "cover_letter_preview": "Dear Hiring Manager...",
                "outreach_preview": "Hello [Name]...",
                "interview_pack_preview": "## Interview Questions..."
            }
        }
