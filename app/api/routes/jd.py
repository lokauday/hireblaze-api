from fastapi import APIRouter, Depends
from app.services.ai_engine import extract_skills_from_jd
from app.core.quota_guard import require_quota
from app.db.models.user import User

router = APIRouter(prefix="/jd", tags=["Job Description"])

@router.post("/skills")
def extract_skills(
    jd_text: str,
    user: User = Depends(require_quota("jd_parse"))
):
    skills = extract_skills_from_jd(jd_text)
    return {"skills": skills}
