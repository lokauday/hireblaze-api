"""
Job Pack Service.

Generates a complete application pack for a job: tailored resume, cover letter, 
outreach message, and interview pack.
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.db.models.resume import Resume
from app.db.models.job import Job
from app.db.models.job_posting import JobPosting
from app.db.models.document import Document
from app.services.ai_service import (
    generate_interview_pack,
    generate_outreach_message
)
from app.services.ai_engine import tailor_resume_for_jd, generate_cover_letter

logger = logging.getLogger(__name__)


def generate_application_pack(
    db: Session,
    user: User,
    resume_id: Optional[int] = None,
    job_id: Optional[int] = None,
    resume_text: Optional[str] = None,
    jd_text: Optional[str] = None,
    company: Optional[str] = None,
    job_title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a complete application pack for a job.
    
    Creates:
    1. Tailored resume (JD-optimized)
    2. Cover letter
    3. Outreach message (recruiter followup)
    4. Interview pack (STAR answers, 30/60/90 plan)
    
    All outputs are saved as Documents in the user's Drive.
    
    Returns:
        Dictionary with document IDs and preview text for each component
    """
    # Get resume text
    resume_text_content = resume_text
    if not resume_text_content and resume_id:
        resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
        if not resume:
            raise ValueError(f"Resume {resume_id} not found")
        resume_text_content = resume.content or resume.parsed_text or ""
    
    if not resume_text_content:
        raise ValueError("Resume text is required")
    
    # Get JD text
    jd_text_content = jd_text
    job_company = company
    job_title_value = job_title
    
    if not jd_text_content and job_id:
        # Try JobPosting first, then Job
        job_posting = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == user.id).first()
        if job_posting:
            jd_text_content = job_posting.jd_text or ""
            job_company = job_posting.company or job_company
            job_title_value = job_posting.job_title or job_title_value
        else:
            job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
            if job:
                job_company = job.company or job_company
                job_title_value = job.title or job_title_value
                # Job model doesn't store JD text - use notes as fallback
                jd_text_content = job.notes or ""
    
    if not jd_text_content:
        raise ValueError("Job description text is required")
    
    results = {
        "resume_doc_id": None,
        "cover_letter_doc_id": None,
        "outreach_doc_id": None,
        "interview_pack_doc_id": None,
        "resume_preview": "",
        "cover_letter_preview": "",
        "outreach_preview": "",
        "interview_pack_preview": ""
    }
    
    try:
        # 1. Generate tailored resume
        logger.info(f"Generating tailored resume for job pack: user_id={user.id}, job_id={job_id}")
        try:
            tailored_resume = tailor_resume(resume_text_content, jd_text_content)
            resume_doc = Document(
                user_id=user.id,
                title=f"Tailored Resume - {job_title_value or 'Job'}",
                type="resume",
                content_text=tailored_resume,
                tags=["job-pack", "tailored"]
            )
            db.add(resume_doc)
            db.commit()
            db.refresh(resume_doc)
            results["resume_doc_id"] = resume_doc.id
            results["resume_preview"] = tailored_resume[:200] + "..." if len(tailored_resume) > 200 else tailored_resume
            logger.info(f"Tailored resume saved: doc_id={resume_doc.id}")
        except Exception as e:
            logger.warning(f"Failed to generate tailored resume: {e}", exc_info=True)
            # Continue with other components
        
        # 2. Generate cover letter
        logger.info(f"Generating cover letter for job pack: user_id={user.id}, job_id={job_id}")
        try:
            cover_letter = generate_cover_letter(resume_text_content, jd_text_content, job_company, job_title_value)
            cover_letter_doc = Document(
                user_id=user.id,
                title=f"Cover Letter - {job_title_value or 'Job'}",
                type="cover_letter",
                content_text=cover_letter,
                tags=["job-pack", "cover-letter"]
            )
            db.add(cover_letter_doc)
            db.commit()
            db.refresh(cover_letter_doc)
            results["cover_letter_doc_id"] = cover_letter_doc.id
            results["cover_letter_preview"] = cover_letter[:200] + "..." if len(cover_letter) > 200 else cover_letter
            logger.info(f"Cover letter saved: doc_id={cover_letter_doc.id}")
        except Exception as e:
            logger.warning(f"Failed to generate cover letter: {e}", exc_info=True)
            # Continue with other components
        
        # 3. Generate outreach message
        logger.info(f"Generating outreach message for job pack: user_id={user.id}, job_id={job_id}")
        try:
            outreach_response = generate_outreach_message(
                resume_text=resume_text_content,
                jd_text=jd_text_content,
                message_type="recruiter_followup",
                company=job_company,
                job_title=job_title_value
            )
            outreach_message = outreach_response.message
            outreach_doc = Document(
                user_id=user.id,
                title=f"Outreach Message - {job_title_value or 'Job'}",
                type="outreach",
                content_text=outreach_message,
                tags=["job-pack", "outreach"]
            )
            db.add(outreach_doc)
            db.commit()
            db.refresh(outreach_doc)
            results["outreach_doc_id"] = outreach_doc.id
            results["outreach_preview"] = outreach_message[:200] + "..." if len(outreach_message) > 200 else outreach_message
            logger.info(f"Outreach message saved: doc_id={outreach_doc.id}")
        except Exception as e:
            logger.warning(f"Failed to generate outreach message: {e}", exc_info=True)
            # Continue with other components
        
        # 4. Generate interview pack
        logger.info(f"Generating interview pack for job pack: user_id={user.id}, job_id={job_id}")
        try:
            interview_pack_response = generate_interview_pack(
                resume_text=resume_text_content,
                jd_text=jd_text_content
            )
            # Format interview pack as markdown
            interview_pack_md = _format_interview_pack(interview_pack_response)
            interview_pack_doc = Document(
                user_id=user.id,
                title=f"Interview Pack - {job_title_value or 'Job'}",
                type="interview_pack",
                content_text=interview_pack_md,
                tags=["job-pack", "interview"]
            )
            db.add(interview_pack_doc)
            db.commit()
            db.refresh(interview_pack_doc)
            results["interview_pack_doc_id"] = interview_pack_doc.id
            results["interview_pack_preview"] = interview_pack_md[:200] + "..." if len(interview_pack_md) > 200 else interview_pack_md
            logger.info(f"Interview pack saved: doc_id={interview_pack_doc.id}")
        except Exception as e:
            logger.warning(f"Failed to generate interview pack: {e}", exc_info=True)
            # Continue
        
        logger.info(f"Job pack generation completed: user_id={user.id}, job_id={job_id}")
        return results
        
    except Exception as e:
        logger.error(f"Error generating job pack: {e}", exc_info=True)
        db.rollback()
        raise


def _format_interview_pack(pack_response: Any) -> str:
    """Format interview pack response as markdown."""
    lines = []
    
    if hasattr(pack_response, 'questions') and pack_response.questions:
        lines.append("## Interview Questions\n")
        for i, q in enumerate(pack_response.questions[:10], 1):  # Limit to 10
            lines.append(f"{i}. {q}\n")
        lines.append("\n")
    
    if hasattr(pack_response, 'star_outlines') and pack_response.star_outlines:
        lines.append("## STAR Answers\n")
        for key, outline in list(pack_response.star_outlines.items())[:5]:  # Limit to 5
            lines.append(f"### {key}\n{outline}\n\n")
    
    if hasattr(pack_response, 'plan_30_60_90') and pack_response.plan_30_60_90:
        lines.append("## 30/60/90 Day Plan\n")
        if hasattr(pack_response.plan_30_60_90, 'days_30'):
            lines.append(f"### 30 Days\n{pack_response.plan_30_60_90.days_30}\n\n")
        if hasattr(pack_response.plan_30_60_90, 'days_60'):
            lines.append(f"### 60 Days\n{pack_response.plan_30_60_90.days_60}\n\n")
        if hasattr(pack_response.plan_30_60_90, 'days_90'):
            lines.append(f"### 90 Days\n{pack_response.plan_30_60_90.days_90}\n\n")
        # Handle dict format too
        if isinstance(pack_response.plan_30_60_90, dict):
            if '30_days' in pack_response.plan_30_60_90:
                lines.append(f"### 30 Days\n{pack_response.plan_30_60_90['30_days']}\n\n")
            if '60_days' in pack_response.plan_30_60_90:
                lines.append(f"### 60 Days\n{pack_response.plan_30_60_90['60_days']}\n\n")
            if '90_days' in pack_response.plan_30_60_90:
                lines.append(f"### 90 Days\n{pack_response.plan_30_60_90['90_days']}\n\n")
    
    return "\n".join(lines)
