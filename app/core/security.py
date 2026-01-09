import logging
import bcrypt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)

# Use passlib context for backward compatibility with existing hashes
# But we'll use bcrypt directly for new hashes to avoid passlib issues
try:
    pwd_context = CryptContext(
        schemes=["bcrypt"],
        deprecated="auto",
    )
    logger.debug("Password context initialized")
except Exception as e:
    logger.warning(f"Failed to initialize passlib context: {e}, using bcrypt directly")
    pwd_context = None

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt directly (more reliable than passlib).
    
    Safety: Truncates passwords >72 bytes before hashing to prevent bcrypt errors.
    This is a safety net - validation should happen before calling this function.
    
    Args:
        password: Plain text password (max 72 bytes in UTF-8)
        
    Returns:
        Hashed password string (bcrypt format compatible with passlib)
        
    Raises:
        ValueError: If password cannot be hashed (should not happen with truncation)
    """
    try:
        # Safety: Truncate password to max 72 bytes BEFORE hashing (bcrypt hard limit)
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            logger.warning("Password exceeds 72 bytes, truncating before hashing (validation should have caught this)")
            # Truncate to 72 bytes (safe truncation)
            password_bytes = password_bytes[:72]
            # Try to decode, but if it breaks UTF-8 at the boundary, handle gracefully
            try:
                password = password_bytes.decode('utf-8')
            except UnicodeDecodeError:
                # If truncation breaks UTF-8, remove last byte(s) until valid
                for i in range(1, 4):  # UTF-8 char is max 4 bytes
                    try:
                        password = password_bytes[:-i].decode('utf-8')
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # Fallback: decode with error replacement
                    password = password_bytes.decode('utf-8', errors='replace')
                # Re-encode to ensure we have valid bytes
                password_bytes = password.encode('utf-8')
                # Ensure still within 72 bytes after re-encoding
                if len(password_bytes) > 72:
                    password_bytes = password_bytes[:72]
        
        # Use bcrypt directly (more reliable than passlib for new hashes)
        # This avoids passlib's auto-detection issues with newer bcrypt versions
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
        return hashed
    except ValueError as e:
        # Re-raise ValueError as-is (for "password too long" type errors)
        logger.error(f"Password hashing failed (ValueError): {e}")
        raise ValueError("Invalid password") from e
    except Exception as e:
        logger.error(f"Password hashing failed (Unexpected): {e}", exc_info=True)
        raise ValueError("Invalid password") from e

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
