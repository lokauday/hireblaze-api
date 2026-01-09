"""
Integration tests for GET /me/usage endpoint.
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.models.user import User
from app.db.models.subscription import Subscription
from app.db.models.usage import Usage
from app.core.security import hash_password, create_access_token
from app.db.session import SessionLocal
from app.core.quota_guard import get_db


# Setup in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override get_db dependency for testing."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Create and drop tables for each test."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        full_name="Test User",
        email="test@example.com",
        password_hash=hash_password("testpass123"),
        visa_status="Citizen"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user):
    """Create JWT token for test user."""
    return create_access_token({"sub": test_user.email})


@pytest.fixture
def db_session():
    """Provide a database session for tests."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def free_subscription(db_session, test_user):
    """Create free plan subscription."""
    sub = Subscription(
        user_id=test_user.id,
        plan_type="free",
        status="active"
    )
    db_session.add(sub)
    db_session.commit()
    return sub


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_get_usage_free_plan_no_usage(client, test_user, test_user_token, free_subscription):
    """Test GET /me/usage returns correct structure for free plan with no usage."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = client.get("/me/usage", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["plan"] == "free"
    assert "month" in data
    assert "features" in data
    assert len(data["features"]) == 4
    
    # Check each feature has correct structure
    for feature in data["features"]:
        assert "feature" in feature
        assert "limit" in feature
        assert "used" in feature
        assert "remaining" in feature
        assert "unlimited" in feature
    
    # Check free plan limits
    ats_feature = next(f for f in data["features"] if f["feature"] == "ats_scan")
    assert ats_feature["limit"] == 10
    assert ats_feature["used"] == 0
    assert ats_feature["remaining"] == 10
    assert ats_feature["unlimited"] is False


def test_get_usage_with_existing_usage(client, test_user, test_user_token, free_subscription, db_session):
    """Test GET /me/usage returns correct usage counts."""
    # Add some usage
    usage1 = Usage(
        user_id=test_user.id,
        feature="ats_scan",
        amount=3,
        created_at=datetime.utcnow()
    )
    usage2 = Usage(
        user_id=test_user.id,
        feature="resume_tailor",
        amount=2,
        created_at=datetime.utcnow()
    )
    db_session.add_all([usage1, usage2])
    db_session.commit()
    
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = client.get("/me/usage", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    ats_feature = next(f for f in data["features"] if f["feature"] == "ats_scan")
    assert ats_feature["used"] == 3
    assert ats_feature["remaining"] == 7  # 10 - 3
    
    tailor_feature = next(f for f in data["features"] if f["feature"] == "resume_tailor")
    assert tailor_feature["used"] == 2
    assert tailor_feature["remaining"] == 3  # 5 - 2


def test_get_usage_elite_plan_unlimited(client, test_user, test_user_token, db_session):
    """Test GET /me/usage shows unlimited for elite plan."""
    # Create elite subscription
    sub = Subscription(
        user_id=test_user.id,
        plan_type="elite",
        status="active"
    )
    db_session.add(sub)
    db_session.commit()
    
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = client.get("/me/usage", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["plan"] == "elite"
    
    # Check all features are unlimited
    for feature in data["features"]:
        assert feature["unlimited"] is True
        assert feature["limit"] is None
        assert feature["remaining"] is None


def test_get_usage_unauthorized(client):
    """Test GET /me/usage requires authentication."""
    response = client.get("/me/usage")
    assert response.status_code == 403  # FastAPI returns 403 for missing auth


def test_get_usage_invalid_token(client):
    """Test GET /me/usage with invalid token."""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/me/usage", headers=headers)
    assert response.status_code == 401
