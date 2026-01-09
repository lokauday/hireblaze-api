import logging
from fastapi import APIRouter, Depends, HTTPException, Form, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.security import hash_password, verify_password, create_access_token, validate_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ✅ Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ✅ USER SIGNUP with proper error handling
@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    visa_status: str = Form("Citizen"),
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    
    Accepts form-urlencoded data with:
    - full_name: User's full name (required)
    - email: User's email address (required, must be unique)
    - password: User's password (required, min 6 characters, max 72 bytes UTF-8)
    - visa_status: User's visa status (optional, defaults to "Citizen")
    
    Returns:
    - 201: User created successfully
    - 409: Email already registered
    - 422: Validation error (invalid input data, password too short/long)
    - 500: Server error
    """
    try:
        # Check for duplicate email
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            logger.warning(f"Signup attempt with existing email: {email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        # Validate input
        if not full_name or not full_name.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Full name is required"
            )
        
        if not email or not email.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Email is required"
            )
        
        # Password validation: min length, max 72 bytes (bcrypt limit)
        if not password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password is required"
            )
        
        if len(password) < 6:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be at least 6 characters"
            )
        
        # Validate password length (72-byte bcrypt limit)
        try:
            validate_password(password)
        except ValueError as e:
            # Password validation failed (too long or invalid)
            logger.warning(f"Password validation failed during signup: {str(e)}, email={email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too long or invalid"
            )
        
        # Hash password with error handling
        try:
            hashed = hash_password(password)
        except ValueError as e:
            # Password hashing failed (validation or bcrypt error)
            logger.error(f"Password hashing failed during signup: {str(e)}, email={email}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too long or invalid"
            )
        except Exception as e:
            # Unexpected error during password hashing (should not happen)
            logger.error(f"Unexpected password hashing error during signup: {type(e).__name__}, email={email}", exc_info=True)
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too long or invalid"
            )

        # Create user
        user = User(
            full_name=full_name.strip(),
            email=email.strip().lower(),
            password_hash=hashed,
            visa_status=visa_status.strip() if visa_status else "Citizen"
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"User created successfully: user_id={user.id}, email={email}")

        return {
            "message": "User created successfully",
            "user_id": user.id
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 409 for duplicate email)
        raise
    except IntegrityError as e:
        # Handle database constraint violations (e.g., unique constraint on email)
        db.rollback()
        logger.error(f"Database integrity error during signup: {e}, email={email}")
        
        # Check if it's a duplicate email constraint
        if "email" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Generic integrity error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data provided"
        )
    except Exception as e:
        # Handle any other unexpected errors
        db.rollback()
        logger.error(f"Unexpected error during signup: {e}, email={email}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user. Please try again later."
        )


# ✅ ✅ ✅ FIXED OAUTH2 LOGIN FOR SWAGGER + JWT ✅ ✅ ✅
@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Swagger sends "username", but we treat it as email
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.email})

    return {
        "access_token": token,
        "token_type": "bearer"
    }
