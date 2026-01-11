from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.ai_engine import extract_skills_from_jd
from app.services.jd_parser_service import parse_job_description
from app.core.quota_guard import require_quota
from app.core.auth_dependency import get_current_user
from app.db.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jd", tags=["Job Description"])


class ParseJDRequest(BaseModel):
    """Request model for JD parsing."""
    jd_text: str = Field(..., min_length=10, description="Job description text to parse")


class ParseJDResponse(BaseModel):
    """Response model for JD parsing."""
    job_title: str = Field(..., description="Extracted job title")
    company: str = Field(default="", description="Extracted company name")
    location: str = Field(default="", description="Extracted location")
    skills: List[str] = Field(default_factory=list, description="Extracted skills")
    requirements: List[str] = Field(default_factory=list, description="Extracted requirements")
    responsibilities: List[str] = Field(default_factory=list, description="Extracted responsibilities")
    experience_level: str = Field(default="mid", description="Experience level (entry/mid/senior/executive)")
    salary_range: Optional[str] = Field(default=None, description="Salary range if mentioned")
    summary: str = Field(default="", description="Summary of the role")


@router.post("/parse", response_model=ParseJDResponse)
def parse_jd(
    request: ParseJDRequest = Body(...),
    email: str = Depends(get_current_user)
):
    """
    Parse job description text and extract structured data.
    
    Extracts: job title, company, location, skills, requirements, 
    responsibilities, experience level, salary range, and summary.
    """
    try:
        result = parse_job_description(request.jd_text)
        return ParseJDResponse(**result)
    except Exception as e:
        logger.error(f"Error parsing JD: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse job description"
        )


@router.post("/skills")
def extract_skills(
    jd_text: str,
    user: User = Depends(require_quota("jd_parse"))
):
    skills = extract_skills_from_jd(jd_text)
    return {"skills": skills}
