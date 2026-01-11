"""
Resume Version endpoints for managing resume versions per job.
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.job import Job
from app.db.models.resume_version import ResumeVersion
from app.core.auth_dependency import get_current_user, get_current_user_obj, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resume-versions", tags=["Resume Versions"])


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Request/Response models
class ResumeVersionCreate(BaseModel):
    """Request model for creating a resume version."""
    job_id: Optional[int] = Field(None, description="Job ID for this version")
    title: str = Field(..., min_length=1, description="Version title")
    content: str = Field(..., min_length=1, description="Resume content")
    notes: Optional[str] = Field(None, description="User notes")
    make_active: bool = Field(default=False, description="Set as active version for this job")


class ResumeVersionResponse(BaseModel):
    """Response model for resume version."""
    id: int
    job_id: Optional[int]
    version: int
    title: str
    content: str
    is_active: bool
    is_base: bool
    created_at: str
    created_by: Optional[str]
    notes: Optional[str]
    
    class Config:
        from_attributes = True


class ResumeVersionListResponse(BaseModel):
    """Response model for list of resume versions."""
    versions: List[ResumeVersionResponse]
    total: int


class ResumeVersionCompareResponse(BaseModel):
    """Response model for comparing two versions."""
    version1: ResumeVersionResponse
    version2: ResumeVersionResponse
    diff: Dict[str, Any]  # Simple diff data


@router.get("/{job_id}", response_model=ResumeVersionListResponse)
def list_versions(
    job_id: int,
    current_user: User = Depends(get_current_user_obj),
    db: Session = Depends(get_db)
):
    """List all resume versions for a job."""
    # Verify job belongs to user
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    versions = db.query(ResumeVersion).filter(
        ResumeVersion.user_id == current_user.id,
        ResumeVersion.job_id == job_id
    ).order_by(ResumeVersion.version.desc()).all()
    
    return ResumeVersionListResponse(
        versions=[ResumeVersionResponse(
            id=v.id,
            job_id=v.job_id,
            version=v.version,
            title=v.title,
            content=v.content,
            is_active=v.is_active,
            is_base=v.is_base,
            created_at=v.created_at.isoformat() if v.created_at else "",
            created_by=v.created_by,
            notes=v.notes,
        ) for v in versions],
        total=len(versions)
    )


@router.post("", response_model=ResumeVersionResponse, status_code=status.HTTP_201_CREATED)
def create_version(
    request: ResumeVersionCreate = Body(...),
    current_user: User = Depends(get_current_user_obj),
    db: Session = Depends(get_db)
):
    """Create a new resume version."""
    # Verify job belongs to user if job_id provided
    if request.job_id:
        job = db.query(Job).filter(Job.id == request.job_id, Job.user_id == current_user.id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    
    # Get next version number
    existing = db.query(ResumeVersion).filter(
        ResumeVersion.user_id == current_user.id,
        ResumeVersion.job_id == request.job_id
    ).order_by(ResumeVersion.version.desc()).first()
    
    next_version = (existing.version + 1) if existing else 1
    
    # Deactivate other versions if make_active is True
    if request.make_active and request.job_id:
        db.query(ResumeVersion).filter(
            ResumeVersion.user_id == current_user.id,
            ResumeVersion.job_id == request.job_id,
            ResumeVersion.is_active == True
        ).update({"is_active": False})
    
    # Create new version
    version = ResumeVersion(
        user_id=current_user.id,
        job_id=request.job_id,
        version=next_version,
        title=request.title,
        content=request.content,
        is_active=request.make_active,
        created_by="user",
        notes=request.notes,
    )
    
    db.add(version)
    db.commit()
    db.refresh(version)
    
    logger.info(f"Resume version created: id={version.id}, user_id={current_user.id}, job_id={request.job_id}")
    
    return ResumeVersionResponse(
        id=version.id,
        job_id=version.job_id,
        version=version.version,
        title=version.title,
        content=version.content,
        is_active=version.is_active,
        is_base=version.is_base,
        created_at=version.created_at.isoformat() if version.created_at else "",
        created_by=version.created_by,
        notes=version.notes,
    )


@router.post("/{version_id}/restore", response_model=ResumeVersionResponse)
def restore_version(
    version_id: int,
    current_user: User = Depends(get_current_user_obj),
    db: Session = Depends(get_db)
):
    """Restore a version as active (creates a new version with same content)."""
    version = db.query(ResumeVersion).filter(
        ResumeVersion.id == version_id,
        ResumeVersion.user_id == current_user.id
    ).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Create new version with same content
    request = ResumeVersionCreate(
        job_id=version.job_id,
        title=f"Restored: {version.title}",
        content=version.content,
        make_active=True,
        notes=f"Restored from version {version.version}",
    )
    
    return create_version(request, current_user, db)


@router.post("/{version_id}/make-active", response_model=ResumeVersionResponse)
def make_active(
    version_id: int,
    current_user: User = Depends(get_current_user_obj),
    db: Session = Depends(get_db)
):
    """Set a version as the active version for its job."""
    version = db.query(ResumeVersion).filter(
        ResumeVersion.id == version_id,
        ResumeVersion.user_id == current_user.id
    ).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    if not version.job_id:
        raise HTTPException(status_code=400, detail="Cannot set active version for general resume")
    
    # Deactivate other versions for this job
    db.query(ResumeVersion).filter(
        ResumeVersion.user_id == current_user.id,
        ResumeVersion.job_id == version.job_id,
        ResumeVersion.is_active == True
    ).update({"is_active": False})
    
    # Activate this version
    version.is_active = True
    db.commit()
    db.refresh(version)
    
    logger.info(f"Resume version activated: id={version.id}, user_id={current_user.id}, job_id={version.job_id}")
    
    return ResumeVersionResponse(
        id=version.id,
        job_id=version.job_id,
        version=version.version,
        title=version.title,
        content=version.content,
        is_active=version.is_active,
        is_base=version.is_base,
        created_at=version.created_at.isoformat() if version.created_at else "",
        created_by=version.created_by,
        notes=version.notes,
    )


@router.get("/{version_id1}/compare/{version_id2}", response_model=ResumeVersionCompareResponse)
def compare_versions(
    version_id1: int,
    version_id2: int,
    current_user: User = Depends(get_current_user_obj),
    db: Session = Depends(get_db)
):
    """Compare two resume versions."""
    v1 = db.query(ResumeVersion).filter(
        ResumeVersion.id == version_id1,
        ResumeVersion.user_id == current_user.id
    ).first()
    
    v2 = db.query(ResumeVersion).filter(
        ResumeVersion.id == version_id2,
        ResumeVersion.user_id == current_user.id
    ).first()
    
    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Simple diff (can be enhanced with proper diff library)
    diff_data = {
        "content_diff": _simple_diff(v1.content, v2.content),
        "title_changed": v1.title != v2.title,
        "version_diff": v2.version - v1.version,
    }
    
    return ResumeVersionCompareResponse(
        version1=ResumeVersionResponse(
            id=v1.id,
            job_id=v1.job_id,
            version=v1.version,
            title=v1.title,
            content=v1.content,
            is_active=v1.is_active,
            is_base=v1.is_base,
            created_at=v1.created_at.isoformat() if v1.created_at else "",
            created_by=v1.created_by,
            notes=v1.notes,
        ),
        version2=ResumeVersionResponse(
            id=v2.id,
            job_id=v2.job_id,
            version=v2.version,
            title=v2.title,
            content=v2.content,
            is_active=v2.is_active,
            is_base=v2.is_base,
            created_at=v2.created_at.isoformat() if v2.created_at else "",
            created_by=v2.created_by,
            notes=v2.notes,
        ),
        diff=diff_data,
    )


def _simple_diff(text1: str, text2: str) -> Dict[str, Any]:
    """Simple text diff (can be enhanced with diff library)."""
    lines1 = text1.split("\n")
    lines2 = text2.split("\n")
    
    added = [line for line in lines2 if line not in lines1]
    removed = [line for line in lines1 if line not in lines2]
    
    return {
        "added_lines": added,
        "removed_lines": removed,
        "total_changes": len(added) + len(removed),
    }
