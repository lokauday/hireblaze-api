from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging
import re

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.security import hash_password, verify_password, create_access_token

logger = logging.getLogger(__name__)

# Email validation regex (basic but effective)
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

router = APIRouter(prefix="/auth", tags=["Auth"])


# ✅ Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ✅ Password validation helper
def validate_password(password: str) -> str:
    """Validate password length and return validated password."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password cannot be longer than 72 bytes (approximately 72 characters)"
        )
    if len(password_bytes) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long"
        )
    return password


# ✅ USER SIGNUP (Fixed - accepts form data to match frontend)
@router.post("/signup")
def signup(
    full_name: str = Form(..., min_length=1, max_length=200),
    email: str = Form(...),
    password: str = Form(...),
    visa_status: str = Form(default="Citizen"),
    db: Session = Depends(get_db)
):
    # Validate password
    try:
        validate_password(password)
    except HTTPException:
        raise
    
    # Validate email format
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    try:
        hashed = hash_password(password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create user
    user = User(
        full_name=full_name,
        email=email,
        password_hash=hashed,
        visa_status=visa_status
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during signup: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user. Please try again.")

    # Create access token for immediate login
    token = create_access_token({"sub": user.email})

    return {
        "message": "User created successfully",
        "user_id": user.id,
        "access_token": token,
        "token_type": "bearer"
    }


# ✅ ✅ ✅ FIXED OAUTH2 LOGIN FOR SWAGGER + JWT ✅ ✅ ✅
@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Validate password length before hashing
    password_bytes = form_data.password.encode("utf-8")
    if len(password_bytes) > 72:
        raise HTTPException(status_code=400, detail="Password cannot be longer than 72 bytes")

    # Swagger sends "username", but we treat it as email
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user.email})

    return {
        "access_token": token,
        "token_type": "bearer"
    }
