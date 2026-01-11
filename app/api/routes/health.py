"""
Health check endpoint for deployment monitoring.
"""
from fastapi import APIRouter
from datetime import datetime
from app.db.session import SessionLocal

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check():
    """
    Health check endpoint for deployment monitoring.
    
    Returns 200 if the API is healthy and database is accessible.
    """
    status = "healthy"
    
    # Check database connectivity
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        status = "degraded"
    
    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "version": "1.0.0",
    }
