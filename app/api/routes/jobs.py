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
from app.core.auth_dependency import get_current_user
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
