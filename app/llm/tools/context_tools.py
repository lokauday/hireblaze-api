"""
Tool functions for retrieving context during LLM calls.
"""
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.db.models.job import Job
from app.db.models.job_posting import JobPosting
from app.db.models.document import Document
from app.db.models.resume import Resume

logger = logging.getLogger(__name__)


def get_user_profile(user_id: int, db: Session) -> Dict[str, Any]:
    """
    Get user profile for context.
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        User profile dict
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {}
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "plan": user.plan or "free",
        "visa_status": user.visa_status,
    }


def get_job(job_id: Optional[int], db: Session) -> Optional[Dict[str, Any]]:
    """
    Get job information for context.
    
    Args:
        job_id: Job ID (can be Job or JobPosting)
        db: Database session
        
    Returns:
        Job dict or None
    """
    if not job_id:
        return None
    
    # Try JobPosting first
    job_posting = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if job_posting:
        return {
            "id": job_posting.id,
            "company": job_posting.company,
            "job_title": job_posting.job_title,
            "jd_text": job_posting.jd_text,
            "url": job_posting.url,
        }
    
    # Try Job
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        return {
            "id": job.id,
            "company": job.company,
            "title": job.title,
            "status": job.status,
            "notes": job.notes,
            "url": job.url,
        }
    
    return None


def list_documents(user_id: int, filters: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
    """
    List user documents with filters.
    
    Args:
        user_id: User ID
        filters: Filter dict (type, tags, etc.)
        db: Database session
        
    Returns:
        List of document dicts
    """
    query = db.query(Document).filter(Document.user_id == user_id)
    
    if filters.get("type"):
        query = query.filter(Document.type == filters["type"])
    
    if filters.get("tags"):
        # Simple tag filtering (can be enhanced)
        tags = filters["tags"]
        if isinstance(tags, str):
            tags = [tags]
        # Note: Tag filtering would need proper implementation
    
    documents = query.limit(filters.get("limit", 20)).all()
    
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "type": doc.type,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in documents
    ]


def get_document_content(doc_id: int, db: Session) -> Optional[str]:
    """
    Get document content.
    
    Args:
        doc_id: Document ID
        db: Database session
        
    Returns:
        Document content text or None
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        return None
    
    return doc.content_text or ""


def get_resume_versions(job_id: Optional[int], db: Session) -> List[Dict[str, Any]]:
    """
    Get resume versions for a job.
    
    Args:
        job_id: Job ID (optional)
        db: Database session
        
    Returns:
        List of resume dicts
    """
    query = db.query(Resume)
    
    if job_id:
        # Filter by job if provided (would need join table)
        pass
    
    resumes = query.limit(10).all()
    
    return [
        {
            "id": resume.id,
            "title": resume.title or "Resume",
            "created_at": resume.created_at.isoformat() if resume.created_at else None,
        }
        for resume in resumes
    ]


def compute_keyword_match(jd_text: str, resume_text: str) -> Dict[str, Any]:
    """
    Compute basic keyword match between JD and resume.
    
    Args:
        jd_text: Job description text
        resume_text: Resume text
        
    Returns:
        Match statistics dict
    """
    import re
    
    # Extract keywords (simple word-based matching)
    jd_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', jd_text.lower()))
    resume_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', resume_text.lower()))
    
    overlap = jd_words & resume_words
    missing = jd_words - resume_words
    
    return {
        "jd_keywords": len(jd_words),
        "resume_keywords": len(resume_words),
        "overlap_count": len(overlap),
        "missing_count": len(missing),
        "match_ratio": len(overlap) / len(jd_words) if jd_words else 0.0,
    }
