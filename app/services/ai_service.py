"""
AI Service layer for FinalRoundAI++ features.

Handles all AI operations with proper error handling, validation, and logging.
Returns validated Pydantic models for all responses.
"""
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from openai import OpenAI, APIError
from app.core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Initialize OpenAI client only if API key is available
client = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
else:
    logger.warning("OPENAI_API_KEY not configured - AI endpoints will return 501")


# ============================================
# Pydantic Response Models
# ============================================

class MatchScoreResponse(BaseModel):
    """Response model for job match analysis."""
    match_score: float = Field(..., ge=0, le=100, description="Overall match score 0-100")
    overlap: Dict[str, Any] = Field(default_factory=dict, description="Skills/experiences that match")
    missing: Dict[str, Any] = Field(default_factory=dict, description="Missing skills/requirements")
    risks: Dict[str, Any] = Field(default_factory=dict, description="Risk factors/red flags")
    improvement_plan: Dict[str, Any] = Field(default_factory=dict, description="Actionable improvement suggestions")
    recruiter_lens: Dict[str, Any] = Field(default_factory=dict, description="Recruiter perspective analysis")


class RecruiterLensResponse(BaseModel):
    """Response model for recruiter lens analysis."""
    first_impression: str = Field(..., description="First impression summary")
    red_flags: list = Field(default_factory=list, description="List of red flags")
    strengths: list = Field(default_factory=list, description="List of strengths")
    shortlist_decision: str = Field(..., description="Shortlist decision (yes/no/maybe)")
    fixes: list = Field(default_factory=list, description="Suggested fixes")


class InterviewPackResponse(BaseModel):
    """Response model for interview pack generation."""
    questions: list = Field(default_factory=list, description="List of interview questions")
    star_outlines: Dict[str, str] = Field(default_factory=dict, description="STAR format outlines for questions")
    plan_30_60_90: Dict[str, str] = Field(default_factory=dict, description="30/60/90 day plan")
    additional_prep: Dict[str, Any] = Field(default_factory=dict, description="Additional preparation materials")


class OutreachResponse(BaseModel):
    """Response model for outreach message generation."""
    message: str = Field(..., description="Generated outreach message")
    subject: Optional[str] = Field(None, description="Subject line if applicable")
    tone: str = Field(..., description="Tone of the message")


# ============================================
# AI Service Functions
# ============================================

def _check_ai_configured() -> None:
    """Check if AI is configured, raise HTTPException with 501 if not."""
    if not OPENAI_API_KEY or not client:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="AI service is not configured. Please set OPENAI_API_KEY environment variable."
        )


def _call_openai_safe(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.7) -> str:
    """
    Safely call OpenAI API with error handling.
    
    Returns:
        Generated text content
        
    Raises:
        HTTPException: 502 if AI call fails
    """
    from fastapi import HTTPException, status
    
    _check_ai_configured()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except APIError as e:
        logger.error(f"OpenAI API error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service temporarily unavailable. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error in AI call: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service error. Please try again later."
        )


def _parse_json_response(text: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
    """Parse JSON from AI response, with fallback to default."""
    import json
    import re
    
    if default is None:
        default = {}
    
    try:
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Try to parse entire response as JSON
        return json.loads(text)
    except (json.JSONDecodeError, AttributeError):
        logger.warning(f"Failed to parse JSON from AI response, using default: {text[:100]}")
        return default


def analyze_job_match(resume_text: str, jd_text: str) -> MatchScoreResponse:
    """
    Analyze match between resume and job description.
    
    Returns validated MatchScoreResponse with match score and analysis.
    """
    prompt = f"""
Analyze the match between this resume and job description. Return a JSON object with:
- match_score: number 0-100 (overall match percentage)
- overlap: {{skills: [], experiences: []}} (what matches)
- missing: {{skills: [], requirements: []}} (what's missing)
- risks: {{flags: [], concerns: []}} (potential issues)
- improvement_plan: {{actions: []}} (how to improve match)
- recruiter_lens: {{summary: "", decision: ""}} (recruiter perspective)

Resume:
{resume_text[:3000]}

Job Description:
{jd_text[:3000]}

Return ONLY valid JSON, no markdown or extra text.
"""
    
    try:
        response_text = _call_openai_safe(prompt)
        result = _parse_json_response(response_text, {
            "match_score": 50,
            "overlap": {},
            "missing": {},
            "risks": {},
            "improvement_plan": {},
            "recruiter_lens": {}
        })
        
        # Ensure match_score is a valid number
        match_score = float(result.get("match_score", 50))
        match_score = max(0, min(100, match_score))  # Clamp to 0-100
        
        return MatchScoreResponse(
            match_score=match_score,
            overlap=result.get("overlap", {}),
            missing=result.get("missing", {}),
            risks=result.get("risks", {}),
            improvement_plan=result.get("improvement_plan", {}),
            recruiter_lens=result.get("recruiter_lens", {})
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error in analyze_job_match: {e}", exc_info=True)
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to analyze job match. Please try again."
        )


def generate_recruiter_lens(resume_text: str, jd_text: str) -> RecruiterLensResponse:
    """
    Generate recruiter perspective analysis.
    
    Returns validated RecruiterLensResponse.
    """
    prompt = f"""
You are a senior recruiter reviewing this resume for this job. Provide a JSON response with:
- first_impression: brief summary (1-2 sentences)
- red_flags: array of concerning items
- strengths: array of positive points
- shortlist_decision: "yes", "no", or "maybe"
- fixes: array of suggested improvements

Resume:
{resume_text[:3000]}

Job Description:
{jd_text[:3000]}

Return ONLY valid JSON, no markdown or extra text.
"""
    
    try:
        response_text = _call_openai_safe(prompt)
        result = _parse_json_response(response_text, {
            "first_impression": "Initial review in progress",
            "red_flags": [],
            "strengths": [],
            "shortlist_decision": "maybe",
            "fixes": []
        })
        
        return RecruiterLensResponse(
            first_impression=str(result.get("first_impression", "")),
            red_flags=result.get("red_flags", []),
            strengths=result.get("strengths", []),
            shortlist_decision=str(result.get("shortlist_decision", "maybe")),
            fixes=result.get("fixes", [])
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error in generate_recruiter_lens: {e}", exc_info=True)
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate recruiter lens. Please try again."
        )


def generate_interview_pack(resume_text: str, jd_text: str) -> InterviewPackResponse:
    """
    Generate interview preparation pack.
    
    Returns validated InterviewPackResponse with questions, STAR outlines, and 30/60/90 plan.
    """
    prompt = f"""
Generate an interview preparation pack for this candidate and job. Return JSON with:
- questions: array of 10 interview questions (mix of technical, behavioral, role-specific)
- star_outlines: object mapping question keys to STAR format outlines
- plan_30_60_90: object with keys "30_days", "60_days", "90_days" and plan descriptions
- additional_prep: object with any other prep materials (company research, etc.)

Resume:
{resume_text[:3000]}

Job Description:
{jd_text[:3000]}

Return ONLY valid JSON, no markdown or extra text.
"""
    
    try:
        response_text = _call_openai_safe(prompt)
        result = _parse_json_response(response_text, {
            "questions": [],
            "star_outlines": {},
            "plan_30_60_90": {"30_days": "", "60_days": "", "90_days": ""},
            "additional_prep": {}
        })
        
        return InterviewPackResponse(
            questions=result.get("questions", []),
            star_outlines=result.get("star_outlines", {}),
            plan_30_60_90=result.get("plan_30_60_90", {"30_days": "", "60_days": "", "90_days": ""}),
            additional_prep=result.get("additional_prep", {})
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error in generate_interview_pack: {e}", exc_info=True)
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate interview pack. Please try again."
        )


def generate_outreach_message(
    message_type: str,
    resume_text: str,
    jd_text: str,
    company: str = "",
    job_title: str = ""
) -> OutreachResponse:
    """
    Generate outreach message based on type.
    
    Args:
        message_type: One of "recruiter_followup", "linkedin_dm", "thank_you", "referral_ask"
        resume_text: Candidate resume text
        jd_text: Job description text
        company: Company name (optional)
        job_title: Job title (optional)
        
    Returns validated OutreachResponse.
    """
    type_prompts = {
        "recruiter_followup": "Write a professional follow-up email to a recruiter after applying. Be concise and highlight key qualifications.",
        "linkedin_dm": "Write a brief, professional LinkedIn DM to connect about this role. Keep it under 200 words and personalized.",
        "thank_you": "Write a thank-you email after an interview. Express gratitude and reinforce interest.",
        "referral_ask": "Write a message asking for a referral for this position. Be respectful and provide context."
    }
    
    base_prompt = type_prompts.get(message_type, type_prompts["recruiter_followup"])
    
    prompt = f"""
{base_prompt}

Candidate Background:
{resume_text[:2000]}

Job Details:
Title: {job_title}
Company: {company}
Description: {jd_text[:2000]}

Return a JSON object with:
- message: the full message text
- subject: subject line (if email type)
- tone: description of the tone used

Return ONLY valid JSON, no markdown or extra text.
"""
    
    try:
        response_text = _call_openai_safe(prompt, temperature=0.8)
        result = _parse_json_response(response_text, {
            "message": "Message generation in progress...",
            "subject": "",
            "tone": "professional"
        })
        
        return OutreachResponse(
            message=str(result.get("message", "")),
            subject=result.get("subject"),
            tone=str(result.get("tone", "professional"))
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error in generate_outreach_message: {e}", exc_info=True)
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate outreach message. Please try again."
        )
