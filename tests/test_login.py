"""
Smoke tests for user login endpoint.
Tests successful login, wrong password, and non-existent user scenarios.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.models.user import User
from app.db.session import SessionLocal
from app.core.security import hash_password

client = TestClient(app)


@pytest.fixture
def db():
    """Database session fixture."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db: Session):
    """Create a test user for login tests."""
    test_email = "test_login@example.com"
    test_password = "testpass123"
    
    # Clean up any existing test user
    existing = db.query(User).filter(User.email == test_email).first()
    if existing:
        db.delete(existing)
        db.commit()
    
    # Create test user
    user = User(
        full_name="Test Login User",
        email=test_email,
        password_hash=hash_password(test_password),
        visa_status="Citizen"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    yield {"email": test_email, "password": test_password, "user": user}
    
    # Cleanup
    db.delete(user)
    db.commit()


def test_login_success(test_user, db: Session):
    """Test successful login with correct credentials."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["email"],  # OAuth2PasswordRequestForm uses 'username'
            "password": test_user["password"]
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


def test_login_success_with_email_field(test_user, db: Session):
    """Test successful login using 'email' field instead of 'username'."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "email": test_user["email"],
            "password": test_user["password"]
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_success_json(test_user, db: Session):
    """Test successful login with JSON payload."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": test_user["password"]
        },
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(test_user, db: Session):
    """Test login with wrong password returns 401."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["email"],
            "password": "wrong_password_123"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "Invalid email or password" in data["detail"]


def test_login_nonexistent_email(db: Session):
    """Test login with non-existent email returns 401."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "somepassword123"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "Invalid email or password" in data["detail"]


def test_login_missing_fields(db: Session):
    """Test login with missing required fields."""
    # Missing password
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Missing required fields" in data["detail"]


def test_login_invalid_email_format(db: Session):
    """Test login with invalid email format."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "not-an-email",
            "password": "somepassword123"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    # Should return 400 for validation error
    assert response.status_code in [400, 422]
    data = response.json()
    assert "detail" in data
