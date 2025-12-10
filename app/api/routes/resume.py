from fastapi import APIRouter, UploadFile, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.resume import Resume
from app.services.resume_parser import parse_resume
from app.core.auth_dependency import get_current_user

router = APIRouter(prefix="/resume", tags=["Resume"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload")
async def upload_resume(
    user_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    file_path = f"uploads/{file.filename}"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    parsed_text = parse_resume(file_path)

    resume = Resume(
        user_id=user_id,
        original_file=file.filename,
        parsed_text=parsed_text
    )
    db.add(resume)
    db.commit()

    return {"message": "Resume uploaded securely"}
