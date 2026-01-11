"""
Job Pack Export Service.
Generates PDF and ZIP bundles for job application packs.
"""
import logging
import json
import zipfile
import io
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.models.job import Job
from app.db.models.document import Document

logger = logging.getLogger(__name__)


def generate_job_pack_export(
    db: Session,
    user: User,
    job_id: int,
    resume_doc_id: Optional[int] = None,
    cover_letter_doc_id: Optional[int] = None,
    outreach_doc_id: Optional[int] = None,
    interview_pack_doc_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate job pack export (PDF + ZIP).
    
    For now, returns metadata and document IDs.
    PDF and ZIP generation can be added with libraries like weasyprint or reportlab.
    
    Args:
        db: Database session
        user: User object
        job_id: Job ID
        resume_doc_id: Resume document ID
        cover_letter_doc_id: Cover letter document ID
        outreach_doc_id: Outreach message document ID
        interview_pack_doc_id: Interview pack document ID
        
    Returns:
        Dictionary with export metadata and document IDs
    """
    # Verify job belongs to user
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    # Collect documents
    documents = []
    doc_types = []
    
    if resume_doc_id:
        doc = db.query(Document).filter(Document.id == resume_doc_id, Document.user_id == user.id).first()
        if doc:
            documents.append(("Resume", doc))
            doc_types.append("resume")
    
    if cover_letter_doc_id:
        doc = db.query(Document).filter(Document.id == cover_letter_doc_id, Document.user_id == user.id).first()
        if doc:
            documents.append(("Cover Letter", doc))
            doc_types.append("cover_letter")
    
    if outreach_doc_id:
        doc = db.query(Document).filter(Document.id == outreach_doc_id, Document.user_id == user.id).first()
        if doc:
            documents.append(("Outreach Message", doc))
            doc_types.append("outreach")
    
    if interview_pack_doc_id:
        doc = db.query(Document).filter(Document.id == interview_pack_doc_id, Document.user_id == user.id).first()
        if doc:
            documents.append(("Interview Pack", doc))
            doc_types.append("interview_pack")
    
    if not documents:
        raise ValueError("No documents provided for export")
    
    # Generate export metadata
    export_name = f"{job.company}_{job.title}_Application_Pack_{datetime.now().strftime('%Y%m%d')}"
    
    # For now, return metadata (PDF/ZIP generation can be added later)
    # In production, you would:
    # 1. Generate PDF using weasyprint or reportlab
    # 2. Create ZIP with all documents
    # 3. Upload to storage (S3, etc.)
    # 4. Return download URLs
    
    return {
        "export_name": export_name,
        "documents": [
            {
                "type": doc_type,
                "title": title,
                "doc_id": doc.id,
                "content_preview": doc.content_text[:200] + "..." if doc.content_text and len(doc.content_text) > 200 else (doc.content_text or ""),
            }
            for (title, doc), doc_type in zip(documents, doc_types)
        ],
        "pdf_url": None,  # Would be URL to generated PDF
        "zip_url": None,  # Would be URL to generated ZIP
        "note": "PDF and ZIP generation requires additional libraries. Export metadata is ready.",
    }


def create_job_timeline_event(
    db: Session,
    user: User,
    job_id: int,
    event_type: str,
    description: str,
    document_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Create a timeline event for a job.
    
    For now, returns metadata. Timeline events can be stored in a separate table.
    
    Args:
        db: Database session
        user: User object
        job_id: Job ID
        event_type: Event type (e.g., "pack_generated", "resume_updated")
        description: Event description
        document_ids: Optional list of related document IDs
        
    Returns:
        Timeline event metadata
    """
    # Verify job belongs to user
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    # For now, return metadata
    # In production, you would store this in a JobTimelineEvent table
    return {
        "job_id": job_id,
        "event_type": event_type,
        "description": description,
        "document_ids": document_ids or [],
        "created_at": datetime.utcnow().isoformat(),
    }
