"""
History/Activity endpoints.

Provides timeline of user actions (AI feature usage, document operations, etc.).
"""
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.usage import UsageEvent
from app.core.auth_dependency import get_current_user
from app.schemas.history import (
    HistoryEntryResponse,
    HistoryListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["History"])


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_from_email(email: str, db: Session) -> User:
    """Fetch User object from email."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("", status_code=status.HTTP_200_OK, response_model=HistoryListResponse)
def get_history(
    feature: Optional[str] = Query(None, description="Filter by feature name"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get activity timeline for the authenticated user.
    
    Returns a paginated list of usage events/actions.
    Supports filtering by feature, date range.
    """
    try:
        user = get_user_from_email(email, db)
        
        # Base query - only user's events
        query = db.query(UsageEvent).filter(UsageEvent.user_id == user.id)
        
        # Apply filters
        if feature:
            query = query.filter(UsageEvent.feature == feature)
        
        if start_date:
            query = query.filter(UsageEvent.created_at >= start_date)
        
        if end_date:
            query = query.filter(UsageEvent.created_at <= end_date)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        events = query.order_by(desc(UsageEvent.created_at)).offset(offset).limit(page_size).all()
        
        logger.debug(f"History listed: user_id={user.id}, total={total}, page={page}")
        
        # Convert to response format
        # Note: UsageEvent doesn't have document_id or job_id yet
        # We can enhance the model later to support these fields
        entries = []
        for event in events:
            entries.append(HistoryEntryResponse(
                id=event.id,
                feature=event.feature,
                created_at=event.created_at,
                amount=event.amount,
                document_id=None,  # TODO: Add document_id to UsageEvent if needed
                job_id=None  # TODO: Add job_id to UsageEvent if needed
            ))
        
        return HistoryListResponse(
            entries=entries,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to get history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get history"
        )
