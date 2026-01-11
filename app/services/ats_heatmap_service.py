"""
ATS Heatmap Service.
Provides visual keyword highlighting and analysis for resume vs JD.
"""
import logging
import re
from typing import Dict, Any, List, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


def generate_ats_heatmap(
    resume_text: str,
    jd_text: str,
) -> Dict[str, Any]:
    """
    Generate ATS heatmap data for resume vs JD.
    
    Returns:
        Dictionary with:
        - keywords: list of keywords from JD
        - resume_highlights: list of highlight objects {text, match_type, keyword}
        - missing_keywords: list of missing keywords
        - suggested_rewrites: list of suggested bullet rewrites
        - match_score: overall match score (0-100)
    """
    # Extract keywords from JD (skills, tools, technologies)
    jd_keywords = _extract_keywords(jd_text)
    
    # Extract keywords from resume
    resume_keywords = _extract_keywords(resume_text)
    
    # Categorize keywords
    must_have = jd_keywords.get("must_have", [])
    nice_to_have = jd_keywords.get("nice_to_have", [])
    tools = jd_keywords.get("tools", [])
    
    all_jd_keywords = set(must_have + nice_to_have + tools)
    
    # Find matches
    matched_keywords = all_jd_keywords & set(resume_keywords.get("all", []))
    missing_keywords = list(all_jd_keywords - matched_keywords)
    
    # Generate highlights
    highlights = _generate_highlights(resume_text, matched_keywords, must_have, nice_to_have, tools)
    
    # Calculate match score
    match_score = _calculate_match_score(matched_keywords, all_jd_keywords)
    
    # Generate suggested rewrites (simple suggestions)
    suggested_rewrites = _generate_suggested_rewrites(resume_text, missing_keywords[:5])
    
    return {
        "keywords": {
            "must_have": must_have,
            "nice_to_have": nice_to_have,
            "tools": tools,
            "matched": list(matched_keywords),
            "missing": missing_keywords,
        },
        "resume_highlights": highlights,
        "missing_keywords": missing_keywords,
        "suggested_rewrites": suggested_rewrites,
        "match_score": match_score,
    }


def _extract_keywords(text: str) -> Dict[str, List[str]]:
    """Extract keywords from text."""
    text_lower = text.lower()
    
    # Common technical keywords
    tech_keywords = [
        "python", "javascript", "java", "react", "node", "sql", "aws", "docker",
        "kubernetes", "git", "typescript", "vue", "angular", "django", "flask",
        "mongodb", "postgresql", "redis", "elasticsearch", "kafka", "terraform",
        "jenkins", "ci/cd", "microservices", "rest", "graphql", "api",
    ]
    
    # Tools and frameworks
    tools = [
        "github", "gitlab", "jira", "confluence", "slack", "datadog", "new relic",
        "splunk", "grafana", "prometheus", "ansible", "chef", "puppet",
    ]
    
    # Extract found keywords
    found_tech = [kw for kw in tech_keywords if kw in text_lower]
    found_tools = [kw for kw in tools if kw in text_lower]
    
    # Extract other capitalized terms (likely proper nouns/technologies)
    capitalized = re.findall(r'\b[A-Z][a-z]+\b', text)
    capitalized = [c for c in capitalized if len(c) > 3][:20]  # Limit
    
    return {
        "must_have": found_tech[:10],  # Top tech keywords
        "nice_to_have": capitalized[:10],
        "tools": found_tools,
        "all": found_tech + found_tools + capitalized,
    }


def _generate_highlights(
    resume_text: str,
    matched_keywords: set,
    must_have: List[str],
    nice_to_have: List[str],
    tools: List[str],
) -> List[Dict[str, Any]]:
    """Generate highlight data for resume text."""
    highlights = []
    resume_lower = resume_text.lower()
    
    # Categorize matched keywords
    for keyword in matched_keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in [k.lower() for k in must_have]:
            match_type = "must_have"  # Green
        elif keyword_lower in [k.lower() for k in tools]:
            match_type = "tool"  # Blue
        elif keyword_lower in [k.lower() for k in nice_to_have]:
            match_type = "nice_to_have"  # Yellow
        else:
            match_type = "matched"  # Default
        
        # Find all occurrences
        pattern = re.compile(re.escape(keyword_lower), re.IGNORECASE)
        for match in pattern.finditer(resume_text):
            highlights.append({
                "start": match.start(),
                "end": match.end(),
                "text": match.group(),
                "match_type": match_type,
                "keyword": keyword,
            })
    
    # Sort by position
    highlights.sort(key=lambda x: x["start"])
    
    return highlights


def _calculate_match_score(matched: set, total: set) -> float:
    """Calculate match score (0-100)."""
    if not total:
        return 0.0
    return (len(matched) / len(total)) * 100.0


def _generate_suggested_rewrites(resume_text: str, missing_keywords: List[str]) -> List[str]:
    """Generate suggested bullet rewrites to include missing keywords."""
    suggestions = []
    
    for keyword in missing_keywords[:5]:
        suggestions.append(
            f"Consider adding '{keyword}' to your resume - try: 'Utilized {keyword} to...' or 'Developed using {keyword}...'"
        )
    
    return suggestions


def fix_top_ats_issues(
    resume_text: str,
    jd_text: str,
    top_n: int = 5,
) -> str:
    """
    Fix top N ATS issues by suggesting keyword additions.
    
    Returns:
        Modified resume text with suggested improvements
    """
    heatmap = generate_ats_heatmap(resume_text, jd_text)
    
    missing = heatmap["missing_keywords"][:top_n]
    
    # Simple approach: add missing keywords to skills section if exists
    # Or suggest additions at the end
    
    # Try to find skills section
    skills_pattern = re.compile(r'(?:skills|technologies|tools?)(?::|[\s\n]+)(.*?)(?:\n\n|\n##|\Z)', re.IGNORECASE | re.DOTALL)
    skills_match = skills_pattern.search(resume_text)
    
    if skills_match:
        # Add to existing skills section
        skills_section = skills_match.group(0)
        new_keywords = ", ".join(missing)
        modified = resume_text.replace(skills_section, skills_section.rstrip() + f", {new_keywords}\n\n")
        return modified
    else:
        # Append skills section
        new_keywords = ", ".join(missing)
        return resume_text + f"\n\n## Skills\n{new_keywords}\n"