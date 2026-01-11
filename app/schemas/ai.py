"""
Pydantic schemas for AI endpoints.
"""
from typing import Optional, List, Dict, Any
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


class CompanyPackRequest(BaseModel):
    """Request model for company pack generation."""
    job_id: Optional[int] = Field(None, description="Job ID from database")
    company: Optional[str] = Field(None, description="Company name")
    job_title: Optional[str] = Field(None, description="Job title")
    jd_text: Optional[str] = Field(None, description="Job description text")
    save_to_drive: bool = Field(default=True, description="Save result to Drive")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": 1,
                "company": "Tech Corp",
                "job_title": "Senior Software Engineer",
                "save_to_drive": True
            }
        }


class CompanyPackResponse(BaseModel):
    """Response model for company pack generation."""
    document_id: Optional[int] = Field(None, description="ID of saved document in Drive")
    content: Dict[str, Any] = Field(..., description="Company pack content")
    preview: str = Field(default="", description="Preview text of pack")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": 101,
                "content": {
                    "company_overview": "Tech Corp is...",
                    "competitors": ["Company A", "Company B"],
                    "interview_angles": ["Angle 1", "Angle 2"],
                    "questions_to_ask": ["Question 1", "Question 2"],
                    "role_risks": [],
                    "plan_30_60_90": {
                        "days_30": "Learn...",
                        "days_60": "Contribute...",
                        "days_90": "Establish..."
                    }
                },
                "preview": "Company research for Tech Corp..."
            }
        }


class JobPackExportRequest(BaseModel):
    """Request model for job pack export."""
    job_id: int = Field(..., description="Job ID")
    resume_doc_id: Optional[int] = Field(None, description="Resume document ID")
    cover_letter_doc_id: Optional[int] = Field(None, description="Cover letter document ID")
    outreach_doc_id: Optional[int] = Field(None, description="Outreach message document ID")
    interview_pack_doc_id: Optional[int] = Field(None, description="Interview pack document ID")


class JobPackExportResponse(BaseModel):
    """Response model for job pack export."""
    export_name: str = Field(..., description="Export file name")
    documents: List[Dict[str, Any]] = Field(..., description="List of documents in export")
    pdf_url: Optional[str] = Field(None, description="URL to generated PDF")
    zip_url: Optional[str] = Field(None, description="URL to generated ZIP")
    note: Optional[str] = Field(None, description="Additional notes")
