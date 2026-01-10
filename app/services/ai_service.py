"""
AI Service layer for FinalRoundAI++ features.

Handles all AI operations with proper error handling, validation, and logging.
Returns validated Pydantic models for all responses.
Uses OpenAI if available, otherwise falls back to rule-based analysis.
"""
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Try to import OpenAI (optional)
try:
    from openai import OpenAI, APIError
    from app.core.config import OPENAI_API_KEY
    OPENAI_AVAILABLE = bool(OPENAI_API_KEY)
    client = None
    if OPENAI_AVAILABLE:
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}, falling back to rule-based")
            OPENAI_AVAILABLE = False
    else:
        logger.info("OPENAI_API_KEY not configured - using rule-based AI (works without API key)")
except ImportError:
    logger.info("OpenAI package not available - using rule-based AI")
    OPENAI_AVAILABLE = False
    client = None
    OPENAI_API_KEY = None



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

def _use_openai() -> bool:
    """Check if OpenAI is available and configured."""
    return OPENAI_AVAILABLE and client is not None


def _call_openai_safe(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.7) -> str:
    """
    Safely call OpenAI API with error handling. Falls back to rule-based if OpenAI not available.
    
    Returns:
        Generated text content
        
    Raises:
        HTTPException: 502 if AI call fails and no fallback available
    """
    from fastapi import HTTPException, status
    
    if not _use_openai():
        # Fallback to rule-based (will be handled by individual functions)
        raise ValueError("OpenAI not available, using rule-based fallback")
    
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
    Uses OpenAI if available, otherwise falls back to rule-based analysis.
    """
    # Try OpenAI first if available
    if _use_openai():
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
            
            match_score = float(result.get("match_score", 50))
            match_score = max(0, min(100, match_score))
            
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
            logger.warning(f"OpenAI call failed, using rule-based fallback: {e}")
            # Fall through to rule-based
    
    # Rule-based fallback (simple keyword matching)
    logger.info("Using rule-based job match analysis")
    import re
    from collections import Counter
    
    resume_lower = resume_text.lower()
    jd_lower = jd_text.lower()
    
    # Extract common tech keywords
    tech_keywords = ["python", "java", "javascript", "react", "node", "sql", "aws", "docker", "git"]
    resume_keywords = [kw for kw in tech_keywords if kw in resume_lower]
    jd_keywords = [kw for kw in tech_keywords if kw in jd_lower]
    
    overlap_skills = list(set(resume_keywords) & set(jd_keywords))
    missing_skills = list(set(jd_keywords) - set(resume_keywords))
    
    # Simple match score calculation
    if len(jd_keywords) == 0:
        match_score = 70.0  # Default if no keywords found
    else:
        match_score = min(100.0, (len(overlap_skills) / len(jd_keywords)) * 100)
    
    return MatchScoreResponse(
        match_score=round(match_score, 1),
        overlap={"skills": overlap_skills, "technical_skills": overlap_skills},
        missing={"skills": missing_skills[:10], "technical_skills": missing_skills[:8]},
        risks={"flags": [] if len(missing_skills) <= 3 else [f"Missing {len(missing_skills)} key skills"], "concerns": []},
        improvement_plan={"actions": [f"Add experience with: {', '.join(missing_skills[:3])}"] if missing_skills else ["Resume looks well-matched"]},
        recruiter_lens={"summary": f"Match score: {match_score:.0f}% - {'Strong candidate' if match_score >= 75 else 'Partial match'}", "decision": "yes" if match_score >= 75 else ("maybe" if match_score >= 60 else "no")}
    )


def generate_recruiter_lens(resume_text: str, jd_text: str) -> RecruiterLensResponse:
    """Generate recruiter perspective analysis. Uses OpenAI if available, otherwise rule-based."""
    if _use_openai():
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
            logger.warning(f"OpenAI call failed, using rule-based fallback: {e}")
    
    # Rule-based fallback
    logger.info("Using rule-based recruiter lens analysis")
    resume_lower = resume_text.lower()
    jd_lower = jd_text.lower()
    
    # Simple keyword matching for score estimation
    tech_keywords = ["python", "java", "javascript", "react", "node", "sql", "aws"]
    resume_keywords = [kw for kw in tech_keywords if kw in resume_lower]
    jd_keywords = [kw for kw in tech_keywords if kw in jd_lower]
    overlap_count = len(set(resume_keywords) & set(jd_keywords))
    score = min(100.0, (overlap_count / max(1, len(jd_keywords))) * 100) if jd_keywords else 65.0
    
    strengths = ["Strong technical background"] if len(resume_keywords) >= 3 else ["Relevant experience"]
    if len(resume_text) > 1000:
        strengths.append("Comprehensive resume")
    
    red_flags = [] if score >= 60 else ["Limited match with required qualifications"]
    if len(resume_text) < 500:
        red_flags.append("Resume may be too brief")
    
    return RecruiterLensResponse(
        first_impression=f"Candidate shows approximately {score:.0f}% match with role requirements. {'Strong technical background' if score >= 70 else 'Some gaps in required skills'}.",
        red_flags=red_flags,
        strengths=strengths,
        shortlist_decision="yes" if score >= 75 else ("maybe" if score >= 60 else "no"),
        fixes=["Add more relevant skills to resume", "Highlight quantifiable achievements"] if score < 70 else ["Continue highlighting relevant experience"]
    )


def generate_interview_pack(resume_text: str, jd_text: str) -> InterviewPackResponse:
    """Generate interview preparation pack. Uses OpenAI if available, otherwise rule-based templates."""
    if _use_openai():
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
            logger.warning(f"OpenAI call failed, using rule-based fallback: {e}")
    
    # Rule-based fallback with common interview questions
    logger.info("Using rule-based interview pack generation")
    questions = [
        "Tell me about yourself and your background.",
        "Why are you interested in this position?",
        "What are your greatest strengths?",
        "What is your biggest weakness and how are you working to improve it?",
        "Tell me about a challenging project you worked on.",
        "How do you handle working under pressure?",
        "Describe a time when you had to learn something new quickly.",
        "Tell me about a time you disagreed with a team member or manager.",
        "Where do you see yourself in 5 years?",
        "Do you have any questions for us?"
    ]
    
    star_outlines = {f"q{i+1}": "Situation: [Context]\nTask: [What needed to be done]\nAction: [What you did]\nResult: [Outcome]" for i in range(10)}
    
    return InterviewPackResponse(
        questions=questions,
        star_outlines=star_outlines,
        plan_30_60_90={
            "30_days": "Complete onboarding, meet team, learn tools and processes, start contributing to smaller tasks.",
            "60_days": "Take ownership of projects, establish relationships, implement improvements, deliver first milestones.",
            "90_days": "Fully integrated, leading initiatives, mentoring others, demonstrating measurable impact."
        },
        additional_prep={"company_research": ["Research company news and products", "Understand mission and values", "Review team structure"], "role_preparation": ["Review job requirements", "Prepare examples for each requirement", "Research common interview questions"]}
    )


def generate_outreach_message(
    message_type: str,
    resume_text: str,
    jd_text: str,
    company: str = "",
    job_title: str = ""
) -> OutreachResponse:
    """Generate outreach message. Uses OpenAI if available, otherwise rule-based templates."""
    if _use_openai():
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
            logger.warning(f"OpenAI call failed, using rule-based fallback: {e}")
    
    # Rule-based templates
    logger.info(f"Using rule-based outreach message generation for type: {message_type}")
    import re
    name_match = re.search(r"^([A-Z][a-z]+ [A-Z][a-z]+)", resume_text[:200])
    candidate_name = name_match.group(1) if name_match else "[Your Name]"
    
    templates = {
        "recruiter_followup": {
            "subject": f"Following up on {job_title or 'position'} at {company or '[Company]'}",
            "message": f"Dear Hiring Manager,\n\nI hope this message finds you well. I wanted to follow up on my application for the {job_title or 'position'} at {company or 'your company'}.\n\nI'm particularly excited about this opportunity and believe my background aligns well with the role. I've attached my resume for your review and would welcome the opportunity to discuss how my experience can contribute to your team.\n\nThank you for considering my application.\n\nBest regards,\n{candidate_name}",
            "tone": "professional and courteous"
        },
        "linkedin_dm": {
            "subject": None,
            "message": f"Hi [Name],\n\nI noticed you're connected to {company or 'this company'}. I recently applied for the {job_title or 'position'} and was hoping to connect.\n\nI have relevant experience and would love to learn more about the role and team. Would you be open to a brief conversation?\n\nThanks!\n{candidate_name}",
            "tone": "casual but professional"
        },
        "thank_you": {
            "subject": f"Thank you - {job_title or 'Interview'}",
            "message": f"Dear [Interviewer Name],\n\nThank you for taking the time to speak with me today about the {job_title or 'position'} at {company or 'your company'}. I truly enjoyed our conversation.\n\nI'm excited about the possibility of contributing to your team and look forward to hearing from you about next steps.\n\nBest regards,\n{candidate_name}",
            "tone": "grateful and professional"
        },
        "referral_ask": {
            "subject": f"Referral Request - {job_title or 'Position'} at {company or '[Company]'}",
            "message": f"Hi [Name],\n\nHope you're doing well! I'm reaching out because {company or 'your company'} has an opening for a {job_title or 'position'} that seems like a great fit for my background.\n\nI've been working in this field and would be grateful if you'd be willing to refer me or provide any insights about the company culture.\n\nI've attached my resume for your review. Let me know if you'd be open to helping.\n\nThanks so much!\n{candidate_name}",
            "tone": "friendly and respectful"
        }
    }
    
    template = templates.get(message_type.lower(), templates["recruiter_followup"])
    return OutreachResponse(
        message=template["message"],
        subject=template.get("subject"),
        tone=template["tone"]
    )


def transform_text(mode: str, text: str, context: Dict[str, Any] = None) -> str:
    """
    Transform text content using AI based on mode.
    
    Uses OpenAI ChatGPT if available, otherwise returns friendly error.
    
    Args:
        mode: Transformation mode (rewrite, shorten, expand, ats_optimize, fix_grammar, add_keywords)
        text: Text content to transform (markdown)
        context: Optional context dict with job_title, company, job_description, seniority
        
    Returns:
        Transformed markdown text
        
    Raises:
        HTTPException: 500 if AI not configured (OPENAI_API_KEY missing)
        HTTPException: 502 if AI call fails
    """
    if context is None:
        context = {}
    
    # Check if OpenAI is configured - return clear 500 error if missing
    if not OPENAI_AVAILABLE or not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not configured - cannot perform AI transformation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI not configured"
        )
    
    if client is None:
        logger.error("OpenAI client not initialized - cannot perform AI transformation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI not configured"
        )
    
    # Build system prompt based on mode
    mode_prompts = {
        "rewrite": """You are a professional recruiter and resume expert. Rewrite the following text to improve clarity, impact, and professionalism. Use stronger action verbs, quantify achievements where natural, and make it more ATS-friendly. Preserve all markdown formatting. Output ONLY the transformed markdown text, no explanations.""",
        
        "shorten": """You are a professional recruiter. Make the following text more concise by removing filler words, redundancy, and unnecessary details while keeping all core facts and achievements. Preserve all markdown formatting. Output ONLY the shortened markdown text, no explanations.""",
        
        "expand": """You are a professional recruiter. Expand the following text with more detail and impact. Add [metric] placeholders where numbers would strengthen claims, but DO NOT invent specific facts. Enhance descriptions while maintaining accuracy. Preserve all markdown formatting. Output ONLY the expanded markdown text, no explanations.""",
        
        "ats_optimize": """You are an ATS optimization expert. Optimize the following text for applicant tracking systems by improving headings, using standard formatting, naturally incorporating relevant keywords from the context, and structuring content for easy parsing. Preserve markdown structure. Output ONLY the optimized markdown text, no explanations.""",
        
        "fix_grammar": """You are a professional copy editor. Fix grammar, spelling, and punctuation errors in the following text. Make minimal edits - only correct errors, don't rewrite. Preserve all markdown formatting and original meaning. Output ONLY the corrected markdown text, no explanations.""",
        
        "add_keywords": """You are a professional recruiter. Add relevant skills and keywords to the following text naturally, either by enhancing existing sections or adding a skills section if appropriate. Do not bloat the text - integrate keywords seamlessly. Preserve all markdown formatting. Output ONLY the enhanced markdown text, no explanations."""
    }
    
    system_prompt = mode_prompts.get(mode, mode_prompts["rewrite"])
    
    # Build user prompt with context if provided
    user_prompt = text
    if context:
        context_parts = []
        if context.get("job_title"):
            context_parts.append(f"Job Title: {context['job_title']}")
        if context.get("company"):
            context_parts.append(f"Company: {context['company']}")
        if context.get("job_description"):
            context_parts.append(f"Job Description: {context['job_description'][:1000]}")
        if context.get("seniority"):
            context_parts.append(f"Seniority Level: {context['seniority']}")
        
        if context_parts:
            user_prompt = f"Context:\n" + "\n".join(context_parts) + "\n\nText to transform:\n" + text
    
    # Call OpenAI
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        output = response.choices[0].message.content.strip()
        
        # Ensure output is not empty
        if not output:
            raise ValueError("AI returned empty response")
        
        logger.info(f"Text transformed successfully: mode={mode}, input_len={len(text)}, output_len={len(output)}")
        return output
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"OpenAI API error in transform_text: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service temporarily unavailable. Please try again later."
        )
