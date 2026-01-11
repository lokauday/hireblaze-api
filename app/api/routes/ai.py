"""
AI endpoints for FinalRoundAI++ features.
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.resume import Resume
from app.db.models.job import Job
from app.db.models.job_posting import JobPosting
from app.db.models.match_analysis import MatchAnalysis
from app.db.models.interview_pack import InterviewPack
from app.db.models.outreach_message import OutreachMessage, OutreachType
from app.db.models.document import Document
from app.core.auth_dependency import get_current_user, get_current_user_obj, get_db
from app.core.gating import enforce_ai_limit, increment_ai_usage
from app.services.ai_explain_service import explain_changes
from app.services.job_pack_service import generate_application_pack
from app.schemas.ai import JobPackRequest, JobPackResponse, CompanyPackRequest, CompanyPackResponse
from app.services.ai_service import (
    analyze_job_match,
    generate_recruiter_lens,
    generate_interview_pack,
    generate_outreach_message,
    transform_text,
    MatchScoreResponse,
    RecruiterLensResponse,
    InterviewPackResponse,
    OutreachResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])




# ============================================
# Request Models
# ============================================

class JobMatchRequest(BaseModel):
    """Request model for job match analysis."""
    resume_text: Optional[str] = Field(None, description="Resume text content")
    resume_id: Optional[int] = Field(None, description="Resume ID from database")
    jd_text: Optional[str] = Field(None, description="Job description text")
    job_id: Optional[int] = Field(None, description="Job posting ID from database")
    
    class Config:
        schema_extra = {
            "example": {
                "resume_id": 1,
                "job_id": 2
            }
        }


class RecruiterLensRequest(BaseModel):
    """Request model for recruiter lens analysis."""
    resume_text: Optional[str] = Field(None, description="Resume text content")
    resume_id: Optional[int] = Field(None, description="Resume ID from database")
    jd_text: Optional[str] = Field(None, description="Job description text")
    job_id: Optional[int] = Field(None, description="Job posting ID from database")
    save_to_drive: bool = Field(False, description="Save result as Document in Drive")


class InterviewPackRequest(BaseModel):
    """Request model for interview pack generation."""
    resume_text: Optional[str] = Field(None, description="Resume text content")
    resume_id: Optional[int] = Field(None, description="Resume ID from database")
    jd_text: Optional[str] = Field(None, description="Job description text")
    job_id: Optional[int] = Field(None, description="Job posting ID from database")
    save_to_drive: bool = Field(False, description="Save result as Document in Drive")


class OutreachRequest(BaseModel):
    """Request model for outreach message generation."""
    message_type: str = Field(..., description="Type: recruiter_followup, linkedin_dm, thank_you, referral_ask")
    resume_text: Optional[str] = Field(None, description="Resume text content")
    resume_id: Optional[int] = Field(None, description="Resume ID from database")
    jd_text: Optional[str] = Field(None, description="Job description text")
    job_id: Optional[int] = Field(None, description="Job posting ID from database")
    company: Optional[str] = Field(None, description="Company name")
    job_title: Optional[str] = Field(None, description="Job title")
    save_to_drive: bool = Field(False, description="Save result as Document in Drive")


class TransformRequest(BaseModel):
    """Request model for text transformation in editor."""
    mode: str = Field(..., description="Transformation mode: rewrite, shorten, expand, ats_optimize, fix_grammar, add_keywords")
    text: str = Field(..., min_length=1, description="Markdown content to transform")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional context: job_title, company, job_description, seniority")


class TransformResponse(BaseModel):
    """Response model for text transformation."""
    output: str = Field(..., description="Transformed markdown content")
    explanation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Explanation of changes (what changed, why changed, keywords added)"
    )


# ============================================
# Helper Functions
# ============================================

def _get_resume_text(db: Session, user_id: int, resume_id: Optional[int], resume_text: Optional[str]) -> str:
    """Get resume text from ID or use provided text."""
    if resume_text:
        return resume_text
    if resume_id:
        resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        return resume.content or resume.parsed_text or ""
    raise HTTPException(status_code=400, detail="Either resume_text or resume_id must be provided")


def _get_jd_text(db: Session, user_id: int, job_id: Optional[int], jd_text: Optional[str]) -> tuple:
    """Get job description text and metadata from ID or use provided text.
    
    Supports both JobPosting (has jd_text) and Job (tracking model, uses notes as fallback).
    """
    company = ""
    job_title = ""
    
    if jd_text:
        return jd_text, company, job_title
    
    if job_id:
        # First try JobPosting (has full JD text)
        job_posting = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == user_id).first()
        if job_posting:
            return job_posting.jd_text, job_posting.company or "", job_posting.title or ""
        
        # Fallback to Job model (tracking - use notes as JD text)
        job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
        if job:
            jd_content = job.notes or f"Position: {job.title}\nCompany: {job.company}\n{job.url or ''}"
            return jd_content, job.company or "", job.title or ""
        
        raise HTTPException(status_code=404, detail="Job not found")
    
    raise HTTPException(status_code=400, detail="Either jd_text or job_id must be provided")


def _save_to_drive(db: Session, user_id: int, title: str, content: str, doc_type: str) -> Document:
    """Save content as a Document in Drive."""
    import json
    
    doc = Document(
        user_id=user_id,
        title=title,
        type=doc_type,
        content_text=content if isinstance(content, str) else json.dumps(content),
        tags=[]
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ============================================
# Endpoints
# ============================================

@router.post("/job-match", response_model=MatchScoreResponse)
def job_match(
    request: JobMatchRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze match between resume and job description.
    
    Returns match score (0-100), overlap, missing skills, risks, improvement plan, and recruiter lens.
    Automatically persists the analysis to MatchAnalysis table.
    """
    try:
        # Get resume and JD text
        resume_text = _get_resume_text(db, current_user.id, request.resume_id, request.resume_text)
        jd_text, company, job_title = _get_jd_text(db, current_user.id, request.job_id, request.jd_text)
        
        # Analyze match
        result = analyze_job_match(resume_text, jd_text)
        
        # Persist to database
        match_analysis = MatchAnalysis(
            user_id=current_user.id,
            resume_id=request.resume_id,
            job_id=request.job_id,
            score=result.match_score,
            overlap=result.overlap,
            missing=result.missing,
            risks=result.risks,
            improvement_plan=result.improvement_plan,
            recruiter_lens=result.recruiter_lens,
            narrative=f"Match score: {result.match_score}%"
        )
        db.add(match_analysis)
        db.commit()
        db.refresh(match_analysis)
        
        logger.info(f"Match analysis created: id={match_analysis.id}, user_id={current_user.id}, score={result.match_score}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in job-match endpoint: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze job match"
        )


@router.post("/recruiter-lens", response_model=RecruiterLensResponse)
def recruiter_lens(
    request: RecruiterLensRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate recruiter perspective analysis.
    
    Returns first impression, red flags, strengths, shortlist decision, and fixes.
    Optionally saves to Drive if save_to_drive is True.
    """
    try:
        # Get resume and JD text
        resume_text = _get_resume_text(db, current_user.id, request.resume_id, request.resume_text)
        jd_text, company, job_title = _get_jd_text(db, current_user.id, request.job_id, request.jd_text)
        
        # Generate recruiter lens
        result = generate_recruiter_lens(resume_text, jd_text)
        
        # Save to Drive if requested
        if request.save_to_drive:
            import json
            content = json.dumps({
                "first_impression": result.first_impression,
                "red_flags": result.red_flags,
                "strengths": result.strengths,
                "shortlist_decision": result.shortlist_decision,
                "fixes": result.fixes
            }, indent=2)
            _save_to_drive(
                db, current_user.id,
                f"Recruiter Lens - {job_title or 'Job'}",
                content,
                "interview_notes"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in recruiter-lens endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recruiter lens"
        )


@router.post("/interview-pack", response_model=InterviewPackResponse)
def interview_pack(
    request: InterviewPackRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate interview preparation pack.
    
    Returns 10 questions, STAR outlines, and 30/60/90 day plan.
    Automatically persists to InterviewPack table and optionally saves to Drive.
    """
    try:
        # Get resume and JD text
        resume_text = _get_resume_text(db, current_user.id, request.resume_id, request.resume_text)
        jd_text, company, job_title = _get_jd_text(db, current_user.id, request.job_id, request.jd_text)
        
        # Generate interview pack
        result = generate_interview_pack(resume_text, jd_text)
        
        # Persist to database
        interview_pack = InterviewPack(
            user_id=current_user.id,
            job_id=request.job_id,
            content={
                "questions": result.questions,
                "star_outlines": result.star_outlines,
                "plan_30_60_90": result.plan_30_60_90,
                "additional_prep": result.additional_prep
            }
        )
        db.add(interview_pack)
        db.commit()
        db.refresh(interview_pack)
        
        # Save to Drive if requested
        if request.save_to_drive:
            import json
            content = json.dumps({
                "questions": result.questions,
                "star_outlines": result.star_outlines,
                "plan_30_60_90": result.plan_30_60_90,
                "additional_prep": result.additional_prep
            }, indent=2)
            _save_to_drive(
                db, current_user.id,
                f"Interview Pack - {job_title or 'Job'}",
                content,
                "interview_notes"
            )
        
        logger.info(f"Interview pack created: id={interview_pack.id}, user_id={current_user.id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in interview-pack endpoint: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate interview pack"
        )


@router.post("/outreach", response_model=OutreachResponse)
def outreach(
    request: OutreachRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate outreach message.
    
    Types: recruiter_followup, linkedin_dm, thank_you, referral_ask
    Automatically persists to OutreachMessage table and optionally saves to Drive.
    """
    try:
        # Validate message type
        try:
            outreach_type = OutreachType(request.message_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid message_type. Must be one of: {[e.value for e in OutreachType]}"
            )
        
        # Get resume and JD text
        resume_text = _get_resume_text(db, current_user.id, request.resume_id, request.resume_text)
        jd_text, company, job_title = _get_jd_text(db, current_user.id, request.job_id, request.jd_text)
        
        # Use provided company/title or from job posting
        company = request.company or company
        job_title = request.job_title or job_title
        
        # Generate outreach message
        result = generate_outreach_message(
            message_type=request.message_type,
            resume_text=resume_text,
            jd_text=jd_text,
            company=company,
            job_title=job_title
        )
        
        # Persist to database
        outreach_msg = OutreachMessage(
            user_id=current_user.id,
            job_id=request.job_id,
            type=outreach_type,
            content=result.message
        )
        db.add(outreach_msg)
        db.commit()
        db.refresh(outreach_msg)
        
        # Save to Drive if requested
        if request.save_to_drive:
            import json
            content = json.dumps({
                "type": request.message_type,
                "subject": result.subject,
                "message": result.message,
                "tone": result.tone
            }, indent=2)
            _save_to_drive(
                db, current_user.id,
                f"Outreach - {request.message_type} - {job_title or 'Job'}",
                content,
                "cover_letter"  # Using cover_letter type for outreach messages
            )
        
        logger.info(f"Outreach message created: id={outreach_msg.id}, user_id={current_user.id}, type={request.message_type}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in outreach endpoint: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate outreach message"
        )


@router.post("/transform", response_model=TransformResponse)
def transform(
    request: TransformRequest = Body(...),
    current_user: User = Depends(get_current_user_obj),
    db: Session = Depends(get_db)
):
    """
    Transform text content using AI.
    
    Supported modes:
    - rewrite: Improve clarity and impact
    - shorten: Make more concise
    - expand: Add detail with placeholders
    - ats_optimize: Optimize for ATS systems
    - fix_grammar: Fix grammar only
    - add_keywords: Add relevant keywords
    
    Requires authentication. Free users limited to 3 AI calls per day.
    Premium users have unlimited access.
    Returns transformed markdown.
    """
    try:
        # Enforce usage limits based on plan
        enforce_ai_limit(db, current_user)
        
        # Validate mode
        valid_modes = ["rewrite", "shorten", "expand", "ats_optimize", "fix_grammar", "add_keywords"]
        if request.mode not in valid_modes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid mode. Must be one of: {', '.join(valid_modes)}"
            )
        
        # Validate text length (cap at 50k chars)
        MAX_LENGTH = 50000
        if len(request.text) > MAX_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Text too long. Maximum {MAX_LENGTH:,} characters allowed."
            )
        
        # Validate text is not empty
        if not request.text or not request.text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text cannot be empty"
            )
        
        # Transform text using AI
        before_text = request.text
        result = transform_text(
            mode=request.mode,
            text=before_text,
            context=request.context or {}
        )
        
        # Generate explanation of changes
        explanation = None
        try:
            explanation = explain_changes(
                before=before_text[:2000],  # Limit for explanation
                after=result[:2000],
                mode=request.mode
            )
        except Exception as e:
            logger.warning(f"Failed to generate explanation: {e}", exc_info=True)
            # Continue without explanation - not critical
        
        # Increment usage count after successful transformation
        increment_ai_usage(db, current_user.id)
        
        logger.info(f"Text transformed: mode={request.mode}, user_id={current_user.id}, plan={current_user.plan}, length={len(result)}")
        
        return TransformResponse(output=result, explanation=explanation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in transform endpoint: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to transform text"
        )


@router.post("/job-pack", response_model=JobPackResponse)
def generate_job_pack(
    request: JobPackRequest = Body(...),
    current_user: User = Depends(get_current_user_obj),
    db: Session = Depends(get_db)
):
    """
    Generate a complete application pack for a job.
    
    Creates and saves to Drive:
    - Tailored resume (JD-optimized)
    - Cover letter
    - Outreach message (recruiter followup)
    - Interview pack (STAR answers, 30/60/90 plan)
    
    Requires authentication. Premium feature (or within free limits).
    """
    try:
        # Enforce usage limits (each component counts)
        # For now, allow premium users and check limits per component
        # Free users: limit to 1 job pack per day (4 AI calls)
        enforce_ai_limit(db, current_user)  # Check initial limit
        
        result = generate_application_pack(
            db=db,
            user=current_user,
            resume_id=request.resume_id,
            job_id=request.job_id,
            resume_text=request.resume_text,
            jd_text=request.jd_text,
            company=request.company,
            job_title=request.job_title
        )
        
        # Increment usage for job pack (counts as 1 call, not 4)
        increment_ai_usage(db, current_user.id)
        
        logger.info(f"Job pack generated: user_id={current_user.id}, job_id={request.job_id}, docs={len([d for d in [result['resume_doc_id'], result['cover_letter_doc_id'], result['outreach_doc_id'], result['interview_pack_doc_id']] if d])}")
        
        return JobPackResponse(**result)
        
    except ValueError as e:
        logger.warning(f"Invalid request for job pack: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating job pack: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate job pack"
        )


@router.post("/company-pack", response_model=CompanyPackResponse)
def generate_company_pack_endpoint(
    request: CompanyPackRequest = Body(...),
    current_user: User = Depends(get_current_user_obj),
    db: Session = Depends(get_db)
):
    """
    Generate company research pack for a job.
    
    Creates comprehensive research including:
    - Company overview
    - Competitors
    - Interview angles
    - Questions to ask
    - Role risks
    - 30-60-90 day plan
    
    Requires authentication. Premium feature (or within free limits).
    """
    try:
        # Enforce usage limits
        enforce_ai_limit(db, current_user)
        
        # Generate company pack
        result = generate_company_pack(
            db=db,
            user=current_user,
            job_id=request.job_id,
            company=request.company,
            job_title=request.job_title,
            jd_text=request.jd_text,
            save_to_drive=request.save_to_drive,
        )
        
        # Increment usage
        increment_ai_usage(db, current_user.id)
        
        logger.info(f"Company pack generated: user_id={current_user.id}, job_id={request.job_id}, doc_id={result.get('document_id')}")
        
        return CompanyPackResponse(**result)
        
    except ValueError as e:
        logger.warning(f"Invalid request for company pack: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating company pack: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate company pack"
        )
