"""
Document endpoints for AI Drive.

Provides CRUD operations for user documents (resumes, cover letters, etc.).
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.document import Document
from app.core.auth_dependency import get_current_user
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


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


def is_binary_content(content: str) -> bool:
    """
    Check if content appears to be binary/corrupted data.
    
    Returns True if content looks like binary (ZIP files, PDFs, etc.)
    """
    if not content:
        return False
    
    # Check for common binary file signatures
    binary_signatures = [
        b'PK',  # ZIP files (including .docx, .xlsx)
        b'\x00',  # Null bytes
        b'\xff\xd8\xff',  # JPEG
        b'%PDF',  # PDF
    ]
    
    # Check first 100 bytes for binary patterns
    content_bytes = content.encode('utf-8', errors='ignore')[:100]
    
    # Check for ZIP signature (most common issue)
    if content.startswith('PK'):
        return True
    
    # Check for null bytes (binary indicator)
    if '\x00' in content[:1000]:
        return True
    
    # Check for high ratio of non-printable characters
    if len(content) > 100:
        non_printable = sum(1 for c in content[:1000] if ord(c) < 32 and c not in '\n\r\t')
        if non_printable > len(content[:1000]) * 0.1:  # More than 10% non-printable
            return True
    
    return False


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DocumentResponse)
def create_document(
    document_data: DocumentCreate,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new document.
    
    Requires authentication. Document will be associated with the authenticated user.
    """
    try:
        user = get_user_from_email(email, db)
        
        # Validate content is not binary
        if document_data.content_text and is_binary_content(document_data.content_text):
            logger.warning(f"Rejected binary content for document creation: user_id={user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document content appears to be binary or corrupted. Please use text content only."
            )
        
        document = Document(
            user_id=user.id,
            title=document_data.title,
            type=document_data.type,
            content_text=document_data.content_text,
            tags=document_data.tags or []
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        logger.info(f"Document created: document_id={document.id}, user_id={user.id}, type={document.type}")
        
        return DocumentResponse.model_validate(document)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document"
        )


@router.get("", status_code=status.HTTP_200_OK, response_model=DocumentListResponse)
def list_documents(
    type: Optional[str] = Query(None, description="Filter by document type"),
    tags: Optional[str] = Query(None, description="Comma-separated list of tags"),
    search: Optional[str] = Query(None, description="Search in title and content"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List documents for the authenticated user.
    
    Supports filtering by type, tags, and search query.
    Returns paginated results.
    """
    try:
        user = get_user_from_email(email, db)
        
        # Base query - only user's documents
        query = db.query(Document).filter(Document.user_id == user.id)
        
        # Apply filters
        if type:
            query = query.filter(Document.type == type)
        
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]
            # Filter documents that have any of the specified tags
            for tag in tag_list:
                query = query.filter(Document.tags.contains([tag]))
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Document.title.ilike(search_term),
                    Document.content_text.ilike(search_term)
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        documents = query.order_by(Document.created_at.desc()).offset(offset).limit(page_size).all()
        
        logger.debug(f"Documents listed: user_id={user.id}, total={total}, page={page}")
        
        return DocumentListResponse(
            documents=[DocumentResponse.model_validate(doc) for doc in documents],
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list documents"
        )


@router.get("/{document_id}", status_code=status.HTTP_200_OK, response_model=DocumentResponse)
def get_document(
    document_id: int,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific document by ID.
    
    Returns 404 if document not found or user doesn't have access.
    """
    try:
        user = get_user_from_email(email, db)
        
        document = db.query(Document).filter(
            and_(
                Document.id == document_id,
                Document.user_id == user.id
            )
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return DocumentResponse.model_validate(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document"
        )


@router.put("/{document_id}", status_code=status.HTTP_200_OK, response_model=DocumentResponse)
def update_document(
    document_id: int,
    document_data: DocumentUpdate,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing document.
    
    Validates that content is not binary/corrupted before saving.
    Only updates provided fields. Returns 404 if document not found or user doesn't have access.
    """
    try:
        user = get_user_from_email(email, db)
        
        document = db.query(Document).filter(
            and_(
                Document.id == document_id,
                Document.user_id == user.id
            )
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Validate content is not binary before updating
        if document_data.content_text is not None and is_binary_content(document_data.content_text):
            logger.warning(f"Rejected binary content for document update: document_id={document_id}, user_id={user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document content appears to be binary or corrupted. Please use text content only."
            )
        
        # Update only provided fields
        update_data = document_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(document, field, value)
        
        db.commit()
        db.refresh(document)
        
        logger.info(f"Document updated: document_id={document.id}, user_id={user.id}")
        
        return DocumentResponse.model_validate(document)
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document"
        )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document.
    
    Returns 404 if document not found or user doesn't have access.
    """
    try:
        user = get_user_from_email(email, db)
        
        document = db.query(Document).filter(
            and_(
                Document.id == document_id,
                Document.user_id == user.id
            )
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        db.delete(document)
        db.commit()
        
        logger.info(f"Document deleted: document_id={document_id}, user_id={user.id}")
        
        return None
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )
