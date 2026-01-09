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
    
    assert response.status_code == 400
    assert "at least 6 characters" in response.json()["detail"].lower()


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
