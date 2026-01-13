from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError
from pydantic import ValidationError
import logging
import re

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.subscription import Subscription
from app.core.security import hash_password, verify_password, create_access_token
from app.core.auth_dependency import get_current_user
from app.schemas.auth import SignupRequest, LoginRequest

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


# ✅ USER SIGNUP (Accepts both JSON and form-urlencoded)
@router.post("/signup")
async def signup(request: Request, db: Session = Depends(get_db)):
    """Signup endpoint that accepts both JSON and form-urlencoded data."""
    ct = request.headers.get("content-type", "").lower()
    
    # Track which fields are present (for logging - never log password)
    has_full_name = False
    has_email = False
    has_password = False
    has_visa_status = False
    
    try:
        # Detect content type and parse accordingly
        if "application/json" in ct:
            try:
                payload = await request.json()
                has_full_name = "full_name" in payload
                has_email = "email" in payload
                has_password = "password" in payload
                has_visa_status = "visa_status" in payload
                
                # Validate with Pydantic
                try:
                    data = SignupRequest(**payload)
                except ValidationError as e:
                    errors = e.errors()
                    error_messages = []
                    for error in errors:
                        field = error.get("loc", ["unknown"])[0]
                        msg = error.get("msg", "Invalid value")
                        if field == "password":
                            if "at least 8" in msg.lower():
                                error_messages.append("Password must be at least 8 characters")
                            elif "72 bytes" in msg.lower() or "too long" in msg.lower():
                                error_messages.append("Password too long (bcrypt limit 72 bytes)")
                            else:
                                error_messages.append(f"Password validation failed: {msg}")
                        else:
                            error_messages.append(f"{field}: {msg}")
                    
                    logger.warning(
                        "Signup validation failed (JSON)",
                        extra={
                            "content_type": ct,
                            "has_full_name": has_full_name,
                            "has_email": has_email,
                            "has_password": has_password,
                            "has_visa_status": has_visa_status,
                            "validation_errors": [str(e) for e in errors]
                        }
                    )
                    raise HTTPException(
                        status_code=422,
                        detail="; ".join(error_messages) if error_messages else "Validation failed"
                    )
            except ValueError as e:
                logger.warning(
                    "Signup JSON parse error",
                    extra={"content_type": ct, "error": str(e)}
                )
                raise HTTPException(status_code=400, detail="Invalid JSON format")
        else:
            # Form-urlencoded (default for backward compatibility)
            try:
                form = await request.form()
                full_name = form.get("full_name", "").strip()
                email = form.get("email", "").strip()
                password = form.get("password", "")
                visa_status = form.get("visa_status", None)
                
                has_full_name = bool(full_name)
                has_email = bool(email)
                has_password = bool(password)
                has_visa_status = visa_status is not None
                
                # Check for missing required fields
                missing_fields = []
                if not full_name:
                    missing_fields.append("full_name")
                if not email:
                    missing_fields.append("email")
                if not password:
                    missing_fields.append("password")
                
                if missing_fields:
                    logger.warning(
                        "Signup missing required fields (form)",
                        extra={
                            "content_type": ct,
                            "has_full_name": has_full_name,
                            "has_email": has_email,
                            "has_password": has_password,
                            "has_visa_status": has_visa_status,
                            "missing_fields": missing_fields
                        }
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing required fields: {', '.join(missing_fields)}"
                    )
                
                # Validate with Pydantic
                try:
                    data = SignupRequest(
                        full_name=full_name,
                        email=email.lower(),
                        password=password,
                        visa_status=visa_status
                    )
                except ValidationError as e:
                    errors = e.errors()
                    error_messages = []
                    for error in errors:
                        field = error.get("loc", ["unknown"])[0]
                        msg = error.get("msg", "Invalid value")
                        if field == "password":
                            if "at least 8" in msg.lower():
                                error_messages.append("Password must be at least 8 characters")
                            elif "72 bytes" in msg.lower() or "too long" in msg.lower():
                                error_messages.append("Password too long (bcrypt limit 72 bytes)")
                            else:
                                error_messages.append(f"Password validation failed: {msg}")
                        elif field == "email":
                            error_messages.append("Invalid email format")
                        else:
                            error_messages.append(f"{field}: {msg}")
                    
                    logger.warning(
                        "Signup validation failed (form)",
                        extra={
                            "content_type": ct,
                            "has_full_name": has_full_name,
                            "has_email": has_email,
                            "has_password": has_password,
                            "has_visa_status": has_visa_status,
                            "validation_errors": [str(e) for e in errors]
                        }
                    )
                    raise HTTPException(
                        status_code=422,
                        detail="; ".join(error_messages) if error_messages else "Validation failed"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "Signup form parse error",
                    extra={"content_type": ct, "error": str(e)},
                    exc_info=True
                )
                raise HTTPException(status_code=400, detail="Invalid form data")
        
        # Normalize email to lowercase
        email_lower = data.email.lower()
        
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == email_lower).first()
        if existing_user:
            logger.warning(f"Signup blocked: email exists - {email_lower}")
            raise HTTPException(status_code=409, detail="Email already registered. Please log in.")

        # Hash password (validation already done by Pydantic)
        try:
            hashed = hash_password(data.password)
        except ValueError as e:
            logger.error(f"Password hashing error: {e}")
            raise HTTPException(status_code=400, detail=str(e))

        # Create user
        user = User(
            full_name=data.full_name.strip(),
            email=email_lower,
            password_hash=hashed,
            visa_status=data.visa_status or "Citizen"
        )

        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Get user's plan (default to "free" if no subscription exists)
            # New users won't have a subscription yet, so default to "free"
            try:
                subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
                plan = subscription.plan_type if subscription else "free"
            except Exception as sub_error:
                # If subscription query fails, default to "free"
                logger.warning(f"Could not fetch subscription for new user {user.id}: {sub_error}")
                plan = "free"
            
            logger.info(f"Signup success: user_id={user.id}, email={email_lower}, plan={plan}")
        except Exception as e:
            db.rollback()
            logger.error(f"Database error during signup: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to create user. Please try again.")

        # Create access token for immediate login
        token = create_access_token({"sub": user.email})

        # Return response with user object for immediate login
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "plan": plan
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error in signup",
            extra={
                "content_type": ct,
                "has_full_name": has_full_name,
                "has_email": has_email,
                "has_password": has_password,
                "has_visa_status": has_visa_status,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error during signup")


# ✅ LOGIN (Accepts both JSON and form-urlencoded/OAuth2PasswordRequestForm)
@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """Login endpoint that accepts both JSON and form-urlencoded (OAuth2) data."""
    ct = request.headers.get("content-type", "").lower()
    
    # Track which fields are present (for logging - never log password)
    has_email = False
    has_username = False
    has_password = False
    
    try:
        email = None
        password = None
        
        # Detect content type and parse accordingly
        if "application/json" in ct:
            try:
                payload = await request.json()
                has_email = "email" in payload
                has_password = "password" in payload
                
                # Check for missing required fields
                if not has_email or not has_password:
                    missing_fields = []
                    if not has_email:
                        missing_fields.append("email")
                    if not has_password:
                        missing_fields.append("password")
                    
                    logger.warning(
                        "Login missing required fields (JSON)",
                        extra={
                            "content_type": ct,
                            "has_email": has_email,
                            "has_password": has_password,
                            "missing_fields": missing_fields
                        }
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing required fields: {', '.join(missing_fields)}"
                    )
                
                # Validate with Pydantic
                try:
                    data = LoginRequest(
                        email=payload.get("email", ""),
                        password=payload.get("password", "")
                    )
                    email = data.email.lower()
                    password = data.password
                except ValidationError as e:
                    errors = e.errors()
                    error_messages = []
                    for error in errors:
                        field = error.get("loc", ["unknown"])[0]
                        msg = error.get("msg", "Invalid value")
                        if field == "email":
                            error_messages.append("Invalid email format")
                        else:
                            error_messages.append(f"{field}: {msg}")
                    
                    logger.warning(
                        "Login validation failed (JSON)",
                        extra={
                            "content_type": ct,
                            "has_email": has_email,
                            "has_password": has_password,
                            "validation_errors": [str(e) for e in errors]
                        }
                    )
                    raise HTTPException(
                        status_code=400,
                        detail="; ".join(error_messages) if error_messages else "Validation failed"
                    )
            except HTTPException:
                raise
            except ValueError as e:
                logger.warning(
                    "Login JSON parse error",
                    extra={"content_type": ct, "error": str(e)}
                )
                raise HTTPException(status_code=400, detail="Invalid JSON format")
        else:
            # Form-urlencoded (OAuth2PasswordRequestForm format or regular form)
            # Try OAuth2PasswordRequestForm first for backward compatibility
            try:
                form = await request.form()
                # OAuth2PasswordRequestForm uses 'username' field for email
                username_or_email = form.get("username", form.get("email", "")).strip()
                password = form.get("password", "")
                
                has_email = bool(username_or_email)
                has_username = "username" in form
                has_password = bool(password)
                
                if not username_or_email or not password:
                    missing_fields = []
                    if not username_or_email:
                        missing_fields.append("email/username")
                    if not password:
                        missing_fields.append("password")
                    
                    logger.warning(
                        "Login missing required fields (form)",
                        extra={
                            "content_type": ct,
                            "has_email": has_email,
                            "has_username": has_username,
                            "has_password": has_password,
                            "missing_fields": missing_fields
                        }
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing required fields: {', '.join(missing_fields)}"
                    )
                
                email = username_or_email.lower()
            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "Login form parse error",
                    extra={"content_type": ct, "error": str(e)},
                    exc_info=True
                )
                raise HTTPException(status_code=400, detail="Invalid form data")
        
        # Validate password length before hashing (security check)
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > 72:
            logger.warning(
                "Login attempt with password > 72 bytes",
                extra={"content_type": ct, "has_email": has_email, "has_password": has_password}
            )
            raise HTTPException(status_code=400, detail="Password cannot be longer than 72 bytes")

        # Look up user by email with defensive error handling
        try:
            user = db.query(User).filter(User.email == email).first()
        except ProgrammingError as db_error:
            # Database schema error (e.g., missing column) - log full traceback
            logger.error(
                "Database schema error during login user lookup",
                extra={"email": email, "error": str(db_error)},
                exc_info=True
            )
            raise HTTPException(status_code=500, detail="Login failed")
        except SQLAlchemyError as db_error:
            # Other database errors (connection, etc.)
            logger.error(
                "Database error during login user lookup",
                extra={"email": email, "error": str(db_error)},
                exc_info=True
            )
            raise HTTPException(status_code=500, detail="Login failed")

        # User not found - return 401 (not 404) for security
        if not user:
            logger.warning(f"Login attempt with non-existent email: {email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # User exists but has no password hash (shouldn't happen, but handle defensively)
        if not user.password_hash:
            logger.warning(f"User {user.id} has no password hash")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Verify password with defensive error handling
        try:
            password_valid = verify_password(password, user.password_hash)
        except Exception as verify_error:
            logger.error(
                "Password verification error",
                extra={"email": email, "user_id": user.id, "error": str(verify_error)},
                exc_info=True
            )
            raise HTTPException(status_code=500, detail="Login failed")

        if not password_valid:
            logger.warning(f"Login attempt with wrong password for: {email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Create access token with defensive error handling
        try:
            logger.info(f"User logged in successfully: {user.id} ({email})")
            token = create_access_token({"sub": user.email})
        except Exception as token_error:
            logger.error(
                "Token creation error",
                extra={"email": email, "user_id": user.id, "error": str(token_error)},
                exc_info=True
            )
            raise HTTPException(status_code=500, detail="Login failed")

        return {
            "access_token": token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error in login",
            extra={
                "content_type": ct,
                "has_email": has_email,
                "has_username": has_username,
                "has_password": has_password,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Login failed")


# ✅ GET /auth/me - Get current user info with plan and usage
@router.get("/me")
def get_me(
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information including plan and usage.
    
    Returns:
    - id: User ID
    - email: User email
    - full_name: User full name
    - plan: Current plan ("free" or "premium")
    - usage: Daily AI usage { used: int, limit: int }
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Get plan
    plan = user.plan or "free"
    
    # Get today's AI usage
    from app.core.gating import get_today_ai_usage
    from app.core.config import MAX_FREE_AI_CALLS_PER_DAY
    
    today_usage = get_today_ai_usage(db, user.id)
    usage_limit = MAX_FREE_AI_CALLS_PER_DAY if plan == "free" else 999999  # Unlimited for premium
    
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "plan": plan,
        "usage": {
            "used": today_usage,
            "limit": usage_limit,
        }
    }
