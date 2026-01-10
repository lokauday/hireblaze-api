"""
Pydantic schemas for authentication endpoints.
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    """Request schema for user signup."""
    full_name: str = Field(..., min_length=1, max_length=200, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password (min 8 characters)")
    visa_status: Optional[str] = Field(default=None, description="Visa status (optional)")
    
    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        """Validate password length in bytes (bcrypt limit is 72 bytes)."""
        password_bytes = v.encode("utf-8")
        if len(password_bytes) > 72:
            raise ValueError("Password too long (bcrypt limit 72 bytes)")
        if len(password_bytes) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Doe",
                "email": "john.doe@example.com",
                "password": "SecurePass123",
                "visa_status": "Citizen"
            }
        }


class LoginRequest(BaseModel):
    """Request schema for user login."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePass123"
            }
        }
