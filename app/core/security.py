import logging
import bcrypt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)

# Configure passlib context for bcrypt (production-safe)
try:
    pwd_context = CryptContext(
        schemes=["bcrypt"],
        deprecated="auto",
    )
    logger.debug("Password context initialized")
except Exception as e:
    logger.warning(f"Failed to initialize passlib context: {e}, using bcrypt directly")
    pwd_context = None


def validate_password(password: str) -> None:
    """
    Validate password length against bcrypt's 72-byte hard limit.
    
    Args:
        password: Plain text password to validate
        
    Raises:
        ValueError: If password exceeds 72 bytes when UTF-8 encoded
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        logger.warning(f"Password validation failed: exceeds 72-byte limit (got {len(password_bytes)} bytes)")
        raise ValueError("Password exceeds maximum length of 72 bytes")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt (production-safe).
    
    Validates password length first, then hashes using bcrypt directly
    to avoid passlib compatibility issues.
    
    Args:
        password: Plain text password (will be validated for 72-byte limit)
        
    Returns:
        Hashed password string (bcrypt format)
        
    Raises:
        ValueError: If password validation fails or hashing fails
    """
    # Validate password length first (raises ValueError if invalid)
    validate_password(password)
    
    try:
        # Encode to bytes for bcrypt (already validated to be <= 72 bytes)
        password_bytes = password.encode('utf-8')
        
        # Use bcrypt directly (avoids passlib auto-detection issues)
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
        logger.debug("Password hashed successfully")
        return hashed
    except ValueError:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        # Catch any unexpected errors (should not happen with validated input)
        logger.error(f"Password hashing failed unexpectedly: {type(e).__name__}", exc_info=True)
        raise ValueError("Password is too long or invalid") from e

def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against its hash.
    
    Supports both bcrypt-native hashes and passlib-wrapped hashes for backward compatibility.
    
    Args:
        password: Plain text password
        hashed: Hashed password string
        
    Returns:
        True if password matches hash, False otherwise
    """
    try:
        # Try bcrypt directly first (for new hashes)
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        hashed_bytes = hashed.encode('utf-8')
        try:
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except (ValueError, TypeError):
            # If direct bcrypt fails, try passlib (for backward compatibility with old hashes)
            if pwd_context:
                return pwd_context.verify(password, hashed)
            return False
    except Exception as e:
        logger.error(f"Password verification failed: {e}", exc_info=True)
        return False

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=60))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
