from fastapi import APIRouter, Depends
from app.services.ats_engine import ats_score
from app.core.quota_guard import require_quota
from app.db.models.user import User

router = APIRouter(prefix="/ats", tags=["ATS"])

@router.post("/score")
def score(
    resume_text: str,
    jd_text: str,
    user: User = Depends(require_quota("ats_scan"))
):
    score, missing = ats_score(resume_text, jd_text)
    return {"score": score, "missing_keywords": missing}
