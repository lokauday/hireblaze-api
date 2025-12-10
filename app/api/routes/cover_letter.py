from fastapi import APIRouter
from app.services.ai_engine import generate_cover_letter

router = APIRouter(prefix="/cover-letter", tags=["Cover Letter"])

@router.post("/generate")
def generate(resume_text: str, jd_text: str):
    letter = generate_cover_letter(resume_text, jd_text)
    return {"cover_letter": letter}
