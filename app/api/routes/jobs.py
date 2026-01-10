"""
Job endpoints for Job Tracker.

Provides CRUD operations for tracking job applications.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.job import Job
from app.db.models.job_posting import JobPosting
from app.db.models.match_analysis import MatchAnalysis
from app.db.models.interview_pack import InterviewPack
from app.db.models.outreach_message import OutreachMessage
from app.core.auth_dependency import get_current_user
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobResponse,
    JobListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_from_email(email: str, db: Session) -> User:
    """Fetch User object from email."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("", status_code=status.HTTP_201_CREATED, response_model=JobResponse)
def create_job(
    job_data: JobCreate,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new job application entry.
    
    Requires authentication. Job will be associated with the authenticated user.
    """
    try:
        user = get_user_from_email(email, db)
        
        job = Job(
            user_id=user.id,
            company=job_data.company,
            title=job_data.title,
            url=job_data.url,
            status=job_data.status,
            notes=job_data.notes,
            applied_at=job_data.applied_at
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(f"Job created: job_id={job.id}, user_id={user.id}, company={job.company}")
        
        return JobResponse.model_validate(job)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job"
        )


@router.get("", status_code=status.HTTP_200_OK, response_model=JobListResponse)
def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    company: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    search: Optional[str] = Query(None, description="Search in company, title, and notes"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List job applications for the authenticated user.
    
    Supports filtering by status, company, and search query.
    Returns paginated results.
    """
    try:
        user = get_user_from_email(email, db)
        
        # Base query - only user's jobs
        query = db.query(Job).filter(Job.user_id == user.id)
        
        # Apply filters
        if status:
            query = query.filter(Job.status == status)
        
        if company:
            company_filter = f"%{company}%"
            query = query.filter(Job.company.ilike(company_filter))
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Job.company.ilike(search_term),
                    Job.title.ilike(search_term),
                    Job.notes.ilike(search_term)
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(page_size).all()
        
        logger.debug(f"Jobs listed: user_id={user.id}, total={total}, page={page}")
        
        return JobListResponse(
            jobs=[JobResponse.model_validate(job) for job in jobs],
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list jobs"
        )


@router.get("/{job_id}", status_code=status.HTTP_200_OK, response_model=JobResponse)
def get_job(
    job_id: int,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific job by ID.
    
    Returns 404 if job not found or user doesn't have access.
    """
    try:
        user = get_user_from_email(email, db)
        
        job = db.query(Job).filter(
            and_(
                Job.id == job_id,
                Job.user_id == user.id
            )
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return JobResponse.model_validate(job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job"
        )


@router.put("/{job_id}", status_code=status.HTTP_200_OK, response_model=JobResponse)
def update_job(
    job_id: int,
    job_data: JobUpdate,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing job.
    
    Only updates provided fields. Returns 404 if job not found or user doesn't have access.
    """
    try:
        user = get_user_from_email(email, db)
        
        job = db.query(Job).filter(
            and_(
                Job.id == job_id,
                Job.user_id == user.id
            )
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Update only provided fields
        update_data = job_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(job, field, value)
        
        db.commit()
        db.refresh(job)
        
        logger.info(f"Job updated: job_id={job.id}, user_id={user.id}")
        
        return JobResponse.model_validate(job)
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update job"
        )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a job.
    
    Returns 404 if job not found or user doesn't have access.
    """
    try:
        user = get_user_from_email(email, db)
        
        job = db.query(Job).filter(
            and_(
                Job.id == job_id,
                Job.user_id == user.id
            )
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        db.delete(job)
        db.commit()
        
        logger.info(f"Job deleted: job_id={job_id}, user_id={user.id}")
        
        return None
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete job"
        )


# ============================================
# Job Auto-Tracking Endpoints (JobPosting)
# ============================================

class ImportUrlRequest(BaseModel):
    """Request model for importing job URL."""
    source_url: str = Field(..., description="URL of the job posting")
    company: Optional[str] = Field(None, description="Company name (auto-detected if not provided)")
    title: Optional[str] = Field(None, description="Job title (auto-detected if not provided)")
    location: Optional[str] = Field(None, description="Job location")


class JobPostingResponse(BaseModel):
    """Response model for JobPosting."""
    id: int
    user_id: int
    source_url: Optional[str]
    company: str
    title: str
    location: Optional[str]
    jd_text: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.post("/import-url", status_code=status.HTTP_201_CREATED, response_model=JobPostingResponse)
def import_job_url(
    request: ImportUrlRequest = ...,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Import a job posting by URL.
    
    Creates a JobPosting entry with placeholder JD text. Use parse-jd endpoint to extract full JD.
    """
    try:
        user = get_user_from_email(email, db)
        
        # Create job posting with placeholder JD text
        job_posting = JobPosting(
            user_id=user.id,
            source_url=request.source_url,
            company=request.company or "Unknown Company",
            title=request.title or "Job Posting",
            location=request.location,
            jd_text="[JD parsing pending - use /jobs/{id}/parse-jd to extract]"
        )
        
        db.add(job_posting)
        db.commit()
        db.refresh(job_posting)
        
        logger.info(f"Job posting imported: id={job_posting.id}, user_id={user.id}, url={request.source_url}")
        
        return JobPostingResponse.model_validate(job_posting)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to import job URL: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import job URL"
        )


@router.post("/{job_id}/parse-jd", status_code=status.HTTP_200_OK, response_model=JobPostingResponse)
def parse_job_description(
    job_id: int,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Parse job description from a JobPosting's source URL.
    
    Uses existing JD parsing logic or AI if configured. Updates the jd_text field.
    """
    try:
        user = get_user_from_email(email, db)
        
        # Get job posting (note: using job_id but looking up JobPosting)
        job_posting = db.query(JobPosting).filter(
            JobPosting.id == job_id,
            JobPosting.user_id == user.id
        ).first()
        
        if not job_posting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job posting not found"
            )
        
        # Try to parse JD from URL or use AI
        # For now, use a placeholder - in production, implement actual URL scraping or AI extraction
        try:
            from app.services.ai_service import OPENAI_API_KEY
            if OPENAI_API_KEY:
                # Use AI to extract JD from URL (placeholder - implement actual scraping/extraction)
                job_posting.jd_text = "[JD extracted from URL - implement URL scraping here]"
            else:
                # Fallback: try existing JD parsing logic
                from app.api.routes import jd
                # This would need to be implemented based on existing JD parsing logic
                job_posting.jd_text = "[JD parsing not available - manual entry required]"
        except Exception as e:
            logger.warning(f"JD parsing failed, using placeholder: {e}")
            job_posting.jd_text = "[JD parsing failed - please enter manually]"
        
        db.commit()
        db.refresh(job_posting)
        
        logger.info(f"JD parsed for job posting: id={job_posting.id}, user_id={user.id}")
        
        return JobPostingResponse.model_validate(job_posting)
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to parse JD: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse job description"
        )


@router.get("/{job_id}/insights", status_code=status.HTTP_200_OK)
def get_job_insights(
    job_id: int,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get insights for a job posting.
    
    Returns match analysis, recruiter lens, outreach suggestions, and interview pack availability.
    """
    try:
        user = get_user_from_email(email, db)
        
        # Get job posting
        job_posting = db.query(JobPosting).filter(
            JobPosting.id == job_id,
            JobPosting.user_id == user.id
        ).first()
        
        if not job_posting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job posting not found"
            )
        
        # Get latest match analysis for this job
        match_analysis = db.query(MatchAnalysis).filter(
            MatchAnalysis.job_id == job_id,
            MatchAnalysis.user_id == user.id
        ).order_by(MatchAnalysis.created_at.desc()).first()
        
        # Get outreach messages for this job
        outreach_messages = db.query(OutreachMessage).filter(
            OutreachMessage.job_id == job_id,
            OutreachMessage.user_id == user.id
        ).order_by(OutreachMessage.created_at.desc()).limit(5).all()
        
        # Build insights response
        insights = {
            "job_posting": {
                "id": job_posting.id,
                "company": job_posting.company,
                "title": job_posting.title,
                "location": job_posting.location,
                "has_jd": bool(job_posting.jd_text and job_posting.jd_text != "[JD parsing pending - use /jobs/{id}/parse-jd to extract]")
            },
            "match_analysis": None,
            "recruiter_lens": None,
            "outreach_suggestions": [
                {
                    "type": msg.type.value,
                    "created_at": str(msg.created_at),
                    "preview": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                }
                for msg in outreach_messages
            ],
            "has_interview_pack": db.query(InterviewPack).filter(
                InterviewPack.job_id == job_id,
                InterviewPack.user_id == user.id
            ).first() is not None
        }
        
        if match_analysis:
            insights["match_analysis"] = {
                "score": match_analysis.score,
                "created_at": str(match_analysis.created_at),
                "narrative": match_analysis.narrative
            }
            insights["recruiter_lens"] = match_analysis.recruiter_lens
        
        return insights
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job insights"
        )
