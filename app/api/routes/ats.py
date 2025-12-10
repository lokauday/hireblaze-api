from fastapi import APIRouter
from app.services.ats_engine import ats_score

router = APIRouter(prefix="/ats", tags=["ATS"])

@router.post("/score")
def score(resume_text: str, jd_text: str):
    score, missing = ats_score(resume_text, jd_text)
    return {"score": score, "missing_keywords": missing}
