"""
Tests for user signup endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.models.user import User
from app.db.session import SessionLocal

client = TestClient(app)


@pytest.fixture
def db():
    """Database session fixture."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_signup_success(db: Session):
    """Test successful user registration."""
    # Clean up any existing test user
    test_email = "test_signup@example.com"
    existing = db.query(User).filter(User.email == test_email).first()
    if existing:
        db.delete(existing)
        db.commit()
    
    # Register new user
    response = client.post(
        "/auth/signup",
        data={
            "full_name": "Test User",
            "email": test_email,
            "password": "testpass123",
            "visa_status": "Citizen"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 201
    assert "message" in response.json()
    assert "user_id" in response.json()
    assert response.json()["message"] == "User created successfully"
    
    # Verify user exists in database
    user = db.query(User).filter(User.email == test_email).first()
    assert user is not None
    assert user.full_name == "Test User"
    assert user.email == test_email
    
    # Cleanup
    db.delete(user)
    db.commit()


def test_signup_duplicate_email(db: Session):
    """Test signup with duplicate email returns 409."""
    test_email = "test_duplicate@example.com"
    
    # Create existing user
    existing_user = db.query(User).filter(User.email == test_email).first()
    if not existing_user:
        from app.core.security import hash_password
        existing_user = User(
            full_name="Existing User",
            email=test_email,
            password_hash=hash_password("password123"),
            visa_status="Citizen"
        )
        db.add(existing_user)
        db.commit()
    
    # Try to register with same email
    response = client.post(
        "/auth/signup",
        data={
            "full_name": "New User",
            "email": test_email,
            "password": "newpass123",
            "visa_status": "Citizen"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 409
    assert "Email already registered" in response.json()["detail"]
    
    # Cleanup
    db.delete(existing_user)
    db.commit()


def test_signup_missing_fields(db: Session):
    """Test signup with missing required fields."""
    # Missing full_name
    response = client.post(
        "/auth/signup",
        data={
            "email": "test@example.com",
            "password": "testpass123"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 422  # Validation error
    assert "detail" in response.json()


def test_signup_short_password(db: Session):
    """Test signup with password too short."""
    test_email = "test_short_pass@example.com"
    
    # Clean up
    existing = db.query(User).filter(User.email == test_email).first()
    if existing:
        db.delete(existing)
        db.commit()
    
    response = client.post(
        "/auth/signup",
        data={
            "full_name": "Test User",
            "email": test_email,
            "password": "12345"  # Too short
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 422
    assert "at least 6 characters" in response.json()["detail"].lower()


def test_signup_password_too_long(db: Session):
    """Test signup with password exceeding 72-byte limit."""
    test_email = "test_long_pass@example.com"
    
    # Clean up
    existing = db.query(User).filter(User.email == test_email).first()
    if existing:
        db.delete(existing)
        db.commit()
    
    # Create a password that's 73 bytes when UTF-8 encoded
    # Each emoji is typically 4 bytes in UTF-8
    # 18 emojis = 72 bytes, 19 = 76 bytes (over limit)
    long_password = "a" * 73  # 73 characters = 73 bytes in UTF-8
    
    response = client.post(
        "/auth/signup",
        data={
            "full_name": "Test User",
            "email": test_email,
            "password": long_password
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 422
    assert "72 characters or fewer" in response.json()["detail"]


def test_signup_password_exactly_72_bytes(db: Session):
    """Test signup with password exactly 72 bytes (should succeed)."""
    test_email = "test_72byte_pass@example.com"
    
    # Clean up
    existing = db.query(User).filter(User.email == test_email).first()
    if existing:
        db.delete(existing)
        db.commit()
    
    # Create a password that's exactly 72 bytes when UTF-8 encoded
    password_72_bytes = "a" * 72  # 72 characters = 72 bytes in UTF-8
    
    response = client.post(
        "/auth/signup",
        data={
            "full_name": "Test User",
            "email": test_email,
            "password": password_72_bytes
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 201
    assert "message" in response.json()
    
    # Cleanup
    user = db.query(User).filter(User.email == test_email).first()
    if user:
        db.delete(user)
        db.commit()


def test_signup_password_unicode_72_bytes(db: Session):
    """Test signup with password containing Unicode that's exactly 72 bytes."""
    test_email = "test_unicode_72byte@example.com"
    
    # Clean up
    existing = db.query(User).filter(User.email == test_email).first()
    if existing:
        db.delete(existing)
        db.commit()
    
    # Each emoji is 4 bytes, so 18 emojis = 72 bytes exactly
    password_unicode = "🚀" * 18  # 18 emojis = 72 bytes in UTF-8
    
    response = client.post(
        "/auth/signup",
        data={
            "full_name": "Test User",
            "email": test_email,
            "password": password_unicode
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 201
    assert "message" in response.json()
    
    # Cleanup
    user = db.query(User).filter(User.email == test_email).first()
    if user:
        db.delete(user)
        db.commit()


def test_signup_password_unicode_over_72_bytes(db: Session):
    """Test signup with password containing Unicode exceeding 72 bytes."""
    test_email = "test_unicode_over@example.com"
    
    # Clean up
    existing = db.query(User).filter(User.email == test_email).first()
    if existing:
        db.delete(existing)
        db.commit()
    
    # 19 emojis = 76 bytes (over 72-byte limit)
    password_unicode = "🚀" * 19  # 19 emojis = 76 bytes in UTF-8
    
    response = client.post(
        "/auth/signup",
        data={
            "full_name": "Test User",
            "email": test_email,
            "password": password_unicode
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 422
    assert "72 characters or fewer" in response.json()["detail"]


def test_signup_optional_visa_status(db: Session):
    """Test signup with optional visa_status field."""
    test_email = "test_optional_visa@example.com"
    
    # Clean up
    existing = db.query(User).filter(User.email == test_email).first()
    if existing:
        db.delete(existing)
        db.commit()
    
    # Register without visa_status (should default to "Citizen")
    response = client.post(
        "/auth/signup",
        data={
            "full_name": "Test User",
            "email": test_email,
            "password": "testpass123"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 201
    
    # Verify default visa_status
    user = db.query(User).filter(User.email == test_email).first()
    assert user.visa_status == "Citizen"
    
    # Cleanup
    db.delete(user)
    db.commit()
