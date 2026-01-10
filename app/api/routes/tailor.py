from fastapi import APIRouter, Depends
from app.services.ai_engine import tailor_resume
from app.core.quota_guard import require_quota
from app.db.models.user import User

router = APIRouter(prefix="/tailor", tags=["Resume Tailoring"])

@router.post("/resume")
def tailor(
    resume_text: str,
    jd_text: str,
    user: User = Depends(require_quota("resume_tailor"))
):
    tailored = tailor_resume(resume_text, jd_text)
    return {"tailored_resume": tailored}
