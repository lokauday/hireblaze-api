"""
Job Description Parser Service.

Extracts structured data from job description text (JD parsing).
"""
import logging
import json
import re
from typing import Dict, Any, Optional, List
from app.core.config import OPENAI_API_KEY
from app.services.ai_service import _use_openai

logger = logging.getLogger(__name__)

# Initialize OpenAI client (reuse from ai_service if available)
try:
    from openai import OpenAI
    if OPENAI_API_KEY and _use_openai():
        client = OpenAI(api_key=OPENAI_API_KEY)
    else:
        client = None
except ImportError:
    client = None


def parse_job_description(jd_text: str) -> Dict[str, Any]:
    """
    Parse job description text and extract structured data.
    
    Returns:
        Dictionary with:
        - job_title: str
        - company: str
        - location: str
        - skills: List[str]
        - requirements: List[str]
        - responsibilities: List[str]
        - experience_level: str (e.g., "entry", "mid", "senior")
        - salary_range: Optional[str]
        - summary: str
    """
    if not _use_openai() or not client:
        logger.warning("OpenAI not configured - using rule-based JD parsing")
        return _parse_jd_rule_based(jd_text)
    
    system_prompt = """You are a job description parser. Extract structured information from job descriptions.

Return a JSON object with these fields:
- job_title: string (e.g., "Software Engineer", "Product Manager")
- company: string (company name if mentioned)
- location: string (city, state, or remote)
- skills: array of strings (technical skills, tools, technologies)
- requirements: array of strings (education, experience requirements)
- responsibilities: array of strings (key job responsibilities)
- experience_level: string (one of: "entry", "mid", "senior", "executive")
- salary_range: string or null (if mentioned)
- summary: string (1-2 sentence summary of the role)

Extract only information explicitly stated in the job description. Be accurate and specific."""

    user_prompt = f"""Parse this job description and extract structured information:

{jd_text[:4000]}

Return ONLY valid JSON, no markdown or extra text."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        output = response.choices[0].message.content.strip()
        parsed_data = json.loads(output)
        
        # Validate and normalize
        result = {
            "job_title": parsed_data.get("job_title", "").strip(),
            "company": parsed_data.get("company", "").strip(),
            "location": parsed_data.get("location", "").strip(),
            "skills": parsed_data.get("skills", []),
            "requirements": parsed_data.get("requirements", []),
            "responsibilities": parsed_data.get("responsibilities", []),
            "experience_level": parsed_data.get("experience_level", "mid"),
            "salary_range": parsed_data.get("salary_range"),
            "summary": parsed_data.get("summary", "").strip()
        }
        
        # Ensure lists are lists
        if not isinstance(result["skills"], list):
            result["skills"] = []
        if not isinstance(result["requirements"], list):
            result["requirements"] = []
        if not isinstance(result["responsibilities"], list):
            result["responsibilities"] = []
        
        logger.info(f"JD parsed successfully: job_title={result['job_title']}, company={result['company']}, skills_count={len(result['skills'])}")
        return result
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON from AI response: {e}, falling back to rule-based")
        return _parse_jd_rule_based(jd_text)
    except Exception as e:
        logger.error(f"Error parsing JD with AI: {e}", exc_info=True)
        return _parse_jd_rule_based(jd_text)


def _parse_jd_rule_based(jd_text: str) -> Dict[str, Any]:
    """Rule-based fallback JD parser."""
    text_lower = jd_text.lower()
    lines = jd_text.split('\n')
    
    # Extract job title (often first line or after "Position:", "Title:", etc.)
    job_title = ""
    for line in lines[:10]:
        line_stripped = line.strip()
        if line_stripped and len(line_stripped) < 100:
            if any(word in line_lower for word in ["engineer", "developer", "manager", "analyst", "specialist", "director"]):
                job_title = line_stripped
                break
    
    # Extract company (often after "Company:", "at", or in email domain)
    company = ""
    for line in lines[:5]:
        if "company:" in line.lower() or "at " in line.lower():
            parts = re.split(r"[:\s]+", line, maxsplit=1)
            if len(parts) > 1:
                company = parts[-1].strip()
                break
    
    # Extract location
    location = ""
    for line in lines[:10]:
        if any(word in line.lower() for word in ["remote", "hybrid", "on-site", "location:", "city:", "state:"]):
            location = line.strip()
            break
    
    # Extract skills (common tech keywords)
    common_skills = ["python", "javascript", "react", "node", "java", "sql", "aws", "docker", "kubernetes", 
                     "git", "mongodb", "postgresql", "redis", "typescript", "angular", "vue", "spring", 
                     "django", "flask", "fastapi", "express", "terraform", "jenkins", "ci/cd"]
    skills = [skill for skill in common_skills if skill in text_lower]
    
    # Extract experience level
    experience_level = "mid"
    if any(word in text_lower for word in ["entry", "junior", "0-2 years", "1-2 years"]):
        experience_level = "entry"
    elif any(word in text_lower for word in ["senior", "sr.", "5+ years", "lead", "principal"]):
        experience_level = "senior"
    elif any(word in text_lower for word in ["executive", "vp", "c-level", "chief"]):
        experience_level = "executive"
    
    # Generate summary
    first_paragraph = lines[0].strip() if lines else ""
    summary = first_paragraph[:200] if first_paragraph else "Job description parsed"
    
    return {
        "job_title": job_title or "Software Engineer",
        "company": company,
        "location": location or "Not specified",
        "skills": skills[:15],  # Limit to 15
        "requirements": [],
        "responsibilities": [],
        "experience_level": experience_level,
        "salary_range": None,
        "summary": summary
    }
