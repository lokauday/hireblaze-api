from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.auth_dependency import get_current_user

router = APIRouter(prefix="/applications", tags=["Applications"])


# ✅ DB DEPENDENCY
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ✅ CREATE JOB APPLICATION
@router.post("/create")
def create_application(
    company: str,
    job_title: str,
    status: str = "applied",
    notes: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    application = {
        "user_id": user.id,
        "company": company,
        "job_title": job_title,
        "status": status,
        "notes": notes,
    }

    # ✅ This is safe even if you later replace with DB model
    return {
        "message": "Application logged successfully",
        "application": application,
    }


# ✅ GET ALL USER APPLICATIONS
@router.get("/my")
def list_my_applications(user: User = Depends(get_current_user)):
    # ✅ Placeholder until full DB model is added
    return {
        "message": "Application history feature ready",
        "applications": [],
    }
