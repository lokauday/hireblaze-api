from fastapi import APIRouter
from sqlalchemy import text
from app.db.session import SessionLocal

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/health")
def system_health():
    db_ok = True
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_ok = False

    return {
        "status": "ok",
        "database": "connected" if db_ok else "error",
        "api_version": "1.0.0",
        "service": "Hireblaze API"
    }
