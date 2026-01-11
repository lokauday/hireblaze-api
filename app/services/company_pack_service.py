"""
Company Pack Service.
Generates comprehensive company research pack for a job.
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.db.models.job import Job
from app.db.models.job_posting import JobPosting
from app.db.models.document import Document
from app.llm.runner import LLMRunner

logger = logging.getLogger(__name__)


def generate_company_pack(
    db: Session,
    user: User,
    job_id: Optional[int] = None,
    company: Optional[str] = None,
    job_title: Optional[str] = None,
    jd_text: Optional[str] = None,
    save_to_drive: bool = True,
) -> Dict[str, Any]:
    """
    Generate company research pack for a job.
    
    Creates comprehensive research including:
    - Company overview
    - Competitors
    - Interview angles
    - Questions to ask
    - Role risks
    - 30-60-90 day plan
    
    Args:
        db: Database session
        user: User object
        job_id: Optional job ID
        company: Company name
        job_title: Job title
        jd_text: Job description text
        save_to_drive: Whether to save to Drive
        
    Returns:
        Dictionary with pack content and document ID if saved
    """
    # Get job information
    if job_id:
        # Try JobPosting first, then Job
        job_posting = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == user.id).first()
        if job_posting:
            company = job_posting.company or company
            job_title = job_posting.job_title or job_title
            jd_text = job_posting.jd_text or jd_text
        else:
            job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
            if job:
                company = job.company or company
                job_title = job.title or job_title
    
    if not company or not job_title:
        raise ValueError("Company and job title are required")
    
    # Prepare context for LLM
    context = {
        "company": company,
        "job_title": job_title,
        "jd_text": jd_text or "",
    }
    
    # Initialize LLM runner
    try:
        runner = LLMRunner()
    except ValueError:
        # Fallback to rule-based if LLM not available
        logger.warning("LLM not available, using rule-based company pack")
        return _generate_rule_based_company_pack(company, job_title, jd_text or "")
    
    # Generate pack using LLM
    try:
        plan = user.plan or "free"
        result = runner.run(
            feature="company_pack",
            user_id=user.id,
            db=db,
            context=context,
            job_id=job_id,
            prompt_version="v1",
            plan=plan,
        )
        
        # Format result into standard structure
        pack_content = {
            "company_overview": result.get("title") or result.get("company_overview") or f"Company overview for {company}",
            "summary": result.get("summary") or "",
            "content": result.get("content") or "",
            "competitors": result.get("bullets") or result.get("competitors") or [],
            "interview_angles": result.get("interview_angles") or [],
            "questions_to_ask": result.get("questions_to_ask") or [],
            "role_risks": result.get("warnings") or result.get("role_risks") or [],
            "plan_30_60_90": result.get("plan_30_60_90") or {
                "days_30": "",
                "days_60": "",
                "days_90": "",
            },
            "next_actions": result.get("next_actions") or [],
        }
        
        # Save to Drive if requested
        document_id = None
        if save_to_drive:
            # Format pack as markdown
            pack_markdown = _format_company_pack_markdown(pack_content, company, job_title)
            
            doc = Document(
                user_id=user.id,
                title=f"Company Research Pack - {company} - {job_title}",
                type="company_pack",
                content_text=pack_markdown,
                tags=["company-pack", "research", company.lower()],
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            document_id = doc.id
            
            logger.info(f"Company pack saved to Drive: doc_id={doc.id}, user_id={user.id}, job_id={job_id}")
        
        return {
            "document_id": document_id,
            "content": pack_content,
            "preview": pack_content["company_overview"][:200] + "..." if len(pack_content["company_overview"]) > 200 else pack_content["company_overview"],
        }
        
    except Exception as e:
        logger.error(f"Error generating company pack: {e}", exc_info=True)
        db.rollback()
        # Fallback to rule-based
        return _generate_rule_based_company_pack(company, job_title, jd_text or "")


def _format_company_pack_markdown(content: Dict[str, Any], company: str, job_title: str) -> str:
    """Format company pack content as markdown."""
    lines = [
        f"# Company Research Pack: {company}",
        f"## Position: {job_title}",
        "",
        "## Company Overview",
        content.get("company_overview", ""),
        "",
    ]
    
    if content.get("competitors"):
        lines.extend([
            "## Competitors",
            "",
        ])
        for competitor in content["competitors"]:
            lines.append(f"- {competitor}")
        lines.append("")
    
    if content.get("interview_angles"):
        lines.extend([
            "## Interview Angles",
            "",
        ])
        for angle in content["interview_angles"]:
            lines.append(f"- {angle}")
        lines.append("")
    
    if content.get("questions_to_ask"):
        lines.extend([
            "## Questions to Ask",
            "",
        ])
        for question in content["questions_to_ask"]:
            lines.append(f"- {question}")
        lines.append("")
    
    if content.get("role_risks"):
        lines.extend([
            "## Role Risks",
            "",
        ])
        for risk in content["role_risks"]:
            lines.append(f"- {risk}")
        lines.append("")
    
    plan = content.get("plan_30_60_90", {})
    if plan:
        lines.extend([
            "## 30-60-90 Day Plan",
            "",
        ])
        if plan.get("days_30"):
            lines.extend([
                "### 30 Days",
                plan["days_30"],
                "",
            ])
        if plan.get("days_60"):
            lines.extend([
                "### 60 Days",
                plan["days_60"],
                "",
            ])
        if plan.get("days_90"):
            lines.extend([
                "### 90 Days",
                plan["days_90"],
                "",
            ])
    
    return "\n".join(lines)


def _generate_rule_based_company_pack(company: str, job_title: str, jd_text: str) -> Dict[str, Any]:
    """Generate rule-based company pack as fallback."""
    return {
        "document_id": None,
        "content": {
            "company_overview": f"{company} is a company offering {job_title} positions.",
            "summary": f"Research pack for {company} - {job_title}",
            "content": f"Company research for {company}",
            "competitors": [],
            "interview_angles": [
                "Company culture and values",
                "Recent company news and developments",
                "Growth opportunities in the role",
            ],
            "questions_to_ask": [
                "What does success look like in this role?",
                "What are the biggest challenges facing the team?",
                "How does the company support professional development?",
            ],
            "role_risks": [],
            "plan_30_60_90": {
                "days_30": "Learn the systems, team, and processes",
                "days_60": "Start contributing to key projects",
                "days_90": "Establish yourself as a valuable team member",
            },
            "next_actions": [],
        },
        "preview": f"Company research for {company}",
    }
