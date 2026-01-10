from fastapi import APIRouter, Depends
from app.services.ai_engine import generate_cover_letter
from app.core.quota_guard import require_quota
from app.db.models.user import User

router = APIRouter(prefix="/cover-letter", tags=["Cover Letter"])

@router.post("/generate")
def generate(
    resume_text: str,
    jd_text: str,
    user: User = Depends(require_quota("cover_letter"))
):
    letter = generate_cover_letter(resume_text, jd_text)
    return {"cover_letter": letter}
