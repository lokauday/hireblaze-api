from fastapi import APIRouter
from app.services.ai_engine import tailor_resume

router = APIRouter(prefix="/tailor", tags=["Resume Tailoring"])

@router.post("/resume")
def tailor(resume_text: str, jd_text: str):
    tailored = tailor_resume(resume_text, jd_text)
    return {"tailored_resume": tailored}
