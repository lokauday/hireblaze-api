from fastapi import APIRouter
from app.services.ai_engine import extract_skills_from_jd

router = APIRouter(prefix="/jd", tags=["Job Description"])

@router.post("/skills")
def extract_skills(jd_text: str):
    skills = extract_skills_from_jd(jd_text)
    return {"skills": skills}
