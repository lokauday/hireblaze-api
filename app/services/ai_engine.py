from openai import OpenAI
from app.core.config import OPENAI_API_KEY
import logging

logger = logging.getLogger(__name__)

# Initialize OpenAI client only if API key is available
client = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAI client: {e}")
        client = None
else:
    logger.warning("OPENAI_API_KEY not set. AI features will not be available.")


# Helper function for OpenAI API calls
def call_openai(prompt: str, model: str = "gpt-4o-mini") -> str:
    """Call OpenAI API with error handling."""
    if not client:
        raise ValueError("OpenAI client not initialized. Set OPENAI_API_KEY environment variable.")
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        raise ValueError(f"Failed to generate AI response: {str(e)}")


# ✅ JD SKILL EXTRACTION
def extract_skills_from_jd(jd_text: str):
    prompt = f"""
Extract all required technical and soft skills from this job description as a clean bullet list:

{jd_text}
"""
    return call_openai(prompt)


# ✅ COVER LETTER GENERATOR
def generate_cover_letter(resume_text: str, jd_text: str):
    prompt = f"""
Write a professional, human-sounding cover letter using this resume and job description.

Resume:
{resume_text}

Job Description:
{jd_text}
"""
    return call_openai(prompt)


# ✅ RESUME TAILORING
def tailor_resume(resume_text: str, jd_text: str):
    prompt = f"""
Rewrite this resume so it is perfectly tailored to this job description with optimized ATS keywords.

Resume:
{resume_text}

Job Description:
{jd_text}
"""
    return call_openai(prompt)


# ✅ LIVE INTERVIEW ANSWER (COPILOT)
def generate_live_answer(question: str, resume_text: str, jd_text: str):
    prompt = f"""
You are a real-time interview copilot.
Give a short, confident SPOKEN answer to this interview question.

Question:
{question}

Candidate Resume:
{resume_text}

Job Description:
{jd_text}
"""
    return call_openai(prompt)


# ✅ STAR FORMATTER
def star_formatter(question: str, resume_text: str):
    prompt = f"""
Convert this interview question into a STAR-formatted behavioral answer.

Question:
{question}

Resume:
{resume_text}
"""
    return call_openai(prompt)



def evaluate_interview_performance(transcript: str, jd_text: str):
    prompt = f"""
You are an AI interviewer and hiring manager.

Evaluate this interview based on:
- Communication
- Technical depth
- Confidence
- Role fit

Provide:
1. Communication score (0-10)
2. Technical score (0-10)
3. Confidence score (0-10)
4. Role Fit score (0-100)
5. Top strengths
6. Key weaknesses
7. Actionable improvement plan

Interview Transcript:
{transcript}

Job Description:
{jd_text}

Return result in clear structured text.
"""
    return call_openai(prompt)


def generate_auto_coach_plan(communication, technical, confidence, role_fit):
    weakest = min([
        ("communication", communication),
        ("technical", technical),
        ("confidence", confidence),
        ("role_fit", role_fit)
    ], key=lambda x: x[1])[0]

    prompt = f"""
    You are an elite career coach.
    The user's weakest area is: {weakest}.
    Generate:
    - A 7-day improvement plan
    - 5 targeted practice drills
    - 5 mock interview questions
    - Mindset coaching tips
    """

    return call_openai(prompt)

def generate_weekly_progress_report(previous, latest):
    improvements = {
        "communication": latest["communication"] - previous["communication"],
        "technical": latest["technical"] - previous["technical"],
        "confidence": latest["confidence"] - previous["confidence"],
        "role_fit": latest["role_fit"] - previous["role_fit"],
    }

    weakest = min(latest, key=latest.get)

    prompt = f"""
    Generate a professional weekly career progress report.

    Previous Scores: {previous}
    Latest Scores: {latest}

    Improvements: {improvements}

    Weakest Area: {weakest}

    Provide:
    - Executive summary
    - Key improvements
    - Current weaknesses
    - Focus plan for next week
    - Recruiter-grade performance insight
    """

    return call_openai(prompt)
