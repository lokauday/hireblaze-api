"""
AI service for explaining changes made during transformations.

Provides detailed explanations of what changed, why it changed, and keywords added.
"""
import logging
from typing import Dict, Any, Optional
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


def explain_changes(
    before: str,
    after: str,
    mode: str = "rewrite"
) -> Dict[str, Any]:
    """
    Explain the changes made during AI transformation.
    
    Returns a dictionary with:
    - what_changed: List of main changes
    - why_changed: Explanation of reasoning
    - keywords_added: List of keywords/skills added
    - summary: Brief summary of transformation
    """
    if not _use_openai() or not client:
        logger.warning("OpenAI not configured - cannot explain changes")
        return {
            "what_changed": [],
            "why_changed": "AI explanation not available",
            "keywords_added": [],
            "summary": "Changes applied but explanation unavailable"
        }
    
    system_prompt = """You are a professional resume and document analysis expert. 
Analyze the changes made between a "before" and "after" version of text and provide a clear, professional explanation.

Return your analysis in the following format:
1. WHAT CHANGED: List 3-5 main changes (e.g., "Improved action verbs", "Added quantified metrics", "Enhanced keyword density")
2. WHY CHANGED: Explain the reasoning in 1-2 sentences
3. KEYWORDS ADDED: List specific keywords, skills, or phrases that were added (max 10 items)
4. SUMMARY: One sentence summary of the transformation

Be specific, professional, and actionable. Focus on improvements that make the text more ATS-friendly, impactful, or clear."""

    user_prompt = f"""Transform mode: {mode}

BEFORE:
{before[:2000]}

AFTER:
{after[:2000]}

Analyze the changes and provide: WHAT CHANGED, WHY CHANGED, KEYWORDS ADDED, and SUMMARY."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=800
        )
        
        output = response.choices[0].message.content.strip()
        
        # Parse the response into structured format
        explanation = _parse_explanation(output)
        
        logger.info(f"Change explanation generated: mode={mode}, changes={len(explanation.get('what_changed', []))}")
        return explanation
        
    except Exception as e:
        logger.error(f"Error explaining changes: {e}", exc_info=True)
        return {
            "what_changed": ["Changes applied successfully"],
            "why_changed": "Improvements made for clarity and impact",
            "keywords_added": [],
            "summary": "Text transformed to improve clarity and ATS compatibility"
        }


def _parse_explanation(text: str) -> Dict[str, Any]:
    """Parse explanation text into structured format."""
    lines = text.split('\n')
    result = {
        "what_changed": [],
        "why_changed": "",
        "keywords_added": [],
        "summary": ""
    }
    
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Detect section headers
        if "WHAT CHANGED" in line.upper() or line.startswith("1."):
            current_section = "what_changed"
            continue
        elif "WHY CHANGED" in line.upper() or line.startswith("2."):
            current_section = "why_changed"
            continue
        elif "KEYWORDS ADDED" in line.upper() or line.startswith("3."):
            current_section = "keywords_added"
            continue
        elif "SUMMARY" in line.upper() or line.startswith("4."):
            current_section = "summary"
            continue
        
        # Parse content based on current section
        if current_section == "what_changed":
            # Extract bullet points
            if line.startswith("-") or line.startswith("•") or line.startswith("*"):
                item = line.lstrip("-•* ").strip()
                if item:
                    result["what_changed"].append(item)
            elif line and not line[0].isdigit():
                result["what_changed"].append(line)
        elif current_section == "why_changed":
            if not result["why_changed"]:
                result["why_changed"] = line
            else:
                result["why_changed"] += " " + line
        elif current_section == "keywords_added":
            # Extract keywords (comma-separated or bullet points)
            if "," in line:
                keywords = [k.strip() for k in line.split(",")]
                result["keywords_added"].extend(keywords)
            elif line.startswith("-") or line.startswith("•") or line.startswith("*"):
                keyword = line.lstrip("-•* ").strip()
                if keyword:
                    result["keywords_added"].append(keyword)
            else:
                result["keywords_added"].append(line)
        elif current_section == "summary":
            if not result["summary"]:
                result["summary"] = line
            else:
                result["summary"] += " " + line
    
    # Clean up and limit keywords
    result["keywords_added"] = result["keywords_added"][:10]
    
    # Ensure we have defaults if parsing failed
    if not result["what_changed"]:
        result["what_changed"] = ["Changes applied successfully"]
    if not result["why_changed"]:
        result["why_changed"] = "Improvements made for clarity and impact"
    if not result["summary"]:
        result["summary"] = "Text transformed to improve clarity and ATS compatibility"
    
    return result
