"""
Unit tests for quota guard system.
Tests quota enforcement, usage tracking, and plan limits.
"""
import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.user import User
from app.db.models.subscription import Subscription
from app.db.models.usage import Usage
from app.core.quota_guard import (
    get_user_plan,
    get_current_month_usage,
    require_quota,
    get_user_from_email,
)
from app.core.plan_limits import get_plan_limit, PLAN_LIMITS


# Setup in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def test_user(db):
    """Create a test user."""
    from app.core.security import hash_password
    
    user = User(
        full_name="Test User",
        email="test@example.com",
        password_hash=hash_password("testpass123"),
        visa_status="Citizen"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def free_user_subscription(db, test_user):
    """Create a free plan subscription for test user."""
    sub = Subscription(
        user_id=test_user.id,
        plan_type="free",
        status="active"
    )
    db.add(sub)
    db.commit()
    return sub


@pytest.fixture
def pro_user_subscription(db, test_user):
    """Create a pro plan subscription for test user."""
    sub = Subscription(
        user_id=test_user.id,
        plan_type="pro",
        status="active"
    )
    db.add(sub)
    db.commit()
    return sub


@pytest.fixture
def elite_user_subscription(db, test_user):
    """Create an elite plan subscription for test user."""
    sub = Subscription(
        user_id=test_user.id,
        plan_type="elite",
        status="active"
    )
    db.add(sub)
    db.commit()
    return sub


def test_get_user_plan_free(db, test_user, free_user_subscription):
    """Test getting user plan returns 'free' when subscription exists."""
    plan = get_user_plan(test_user.id, db)
    assert plan == "free"


def test_get_user_plan_no_subscription(db, test_user):
    """Test getting user plan returns 'free' when no subscription exists."""
    plan = get_user_plan(test_user.id, db)
    assert plan == "free"


def test_get_user_plan_pro(db, test_user, pro_user_subscription):
    """Test getting user plan returns 'pro'."""
    plan = get_user_plan(test_user.id, db)
    assert plan == "pro"


def test_get_current_month_usage_empty(db, test_user):
    """Test getting usage when no usage records exist."""
    usage = get_current_month_usage(test_user.id, "ats_scan", db)
    assert usage == 0


def test_get_current_month_usage_with_records(db, test_user):
    """Test getting usage with existing records."""
    # Add usage records
    usage1 = Usage(
        user_id=test_user.id,
        feature="ats_scan",
        amount=5,
        created_at=datetime.utcnow()
    )
    usage2 = Usage(
        user_id=test_user.id,
        feature="ats_scan",
        amount=3,
        created_at=datetime.utcnow()
    )
    db.add_all([usage1, usage2])
    db.commit()
    
    usage = get_current_month_usage(test_user.id, "ats_scan", db)
    assert usage == 8


def test_get_current_month_usage_excludes_other_features(db, test_user):
    """Test that usage only counts for the specified feature."""
    # Add usage for different features
    usage1 = Usage(
        user_id=test_user.id,
        feature="ats_scan",
        amount=5,
        created_at=datetime.utcnow()
    )
    usage2 = Usage(
        user_id=test_user.id,
        feature="resume_tailor",
        amount=10,
        created_at=datetime.utcnow()
    )
    db.add_all([usage1, usage2])
    db.commit()
    
    usage = get_current_month_usage(test_user.id, "ats_scan", db)
    assert usage == 5


def test_plan_limits_free():
    """Test free plan limits."""
    assert get_plan_limit("free", "ats_scan") == 10
    assert get_plan_limit("free", "resume_tailor") == 5
    assert get_plan_limit("free", "cover_letter") == 3
    assert get_plan_limit("free", "jd_parse") == 20


def test_plan_limits_pro():
    """Test pro plan limits."""
    assert get_plan_limit("pro", "ats_scan") == 100
    assert get_plan_limit("pro", "resume_tailor") == 50


def test_plan_limits_elite():
    """Test elite plan has unlimited limits."""
    assert get_plan_limit("elite", "ats_scan") is None
    assert get_plan_limit("elite", "resume_tailor") is None


def test_require_quota_free_plan_under_limit(db, test_user, free_user_subscription):
    """Test quota check passes when under free plan limit."""
    # Mock get_current_user dependency to return test user email
    def mock_get_current_user():
        return test_user.email
    
    # Create quota dependency
    quota_checker = require_quota("ats_scan", amount=1)
    
    # Get the dependency (bypass FastAPI dependency injection for testing)
    # We need to manually pass the dependencies
    from unittest.mock import MagicMock
    mock_depends = MagicMock()
    mock_depends.return_value = test_user.email
    
    # Call quota_checker function directly (bypassing FastAPI Depends)
    # Note: require_quota returns a function that expects FastAPI dependencies
    # For proper testing, we'd need to use TestClient, but for unit tests
    # we test the core logic functions directly
    
    # Test the underlying logic
    from app.core.quota_guard import get_user_from_email
    user = get_user_from_email(test_user.email, db)
    plan = get_user_plan(user.id, db)
    current_usage = get_current_month_usage(user.id, "ats_scan", db)
    limit = get_plan_limit(plan, "ats_scan")
    
    # Should be allowed
    assert current_usage + 1 <= limit


def test_require_quota_free_plan_exceeds_limit(db, test_user, free_user_subscription):
    """Test quota check fails when exceeding free plan limit."""
    # Add usage up to the limit
    for _ in range(10):
        usage = Usage(
            user_id=test_user.id,
            feature="ats_scan",
            amount=1,
            created_at=datetime.utcnow()
        )
        db.add(usage)
    db.commit()
    
    # Try to use one more - should exceed limit
    current_usage = get_current_month_usage(test_user.id, "ats_scan", db)
    limit = get_plan_limit("free", "ats_scan")
    
    assert current_usage == 10
    assert current_usage + 1 > limit


def test_require_quota_elite_unlimited(db, test_user, elite_user_subscription):
    """Test elite plan users have unlimited quota."""
    # Add many usage records
    for _ in range(1000):
        usage = Usage(
            user_id=test_user.id,
            feature="ats_scan",
            amount=1,
            created_at=datetime.utcnow()
        )
        db.add(usage)
    db.commit()
    
    # Should still be allowed (unlimited)
    plan = get_user_plan(test_user.id, db)
    limit = get_plan_limit(plan, "ats_scan")
    assert limit is None


def test_get_user_from_email_success(db, test_user):
    """Test getting user from email succeeds."""
    user = get_user_from_email(test_user.email, db)
    assert user.id == test_user.id
    assert user.email == test_user.email


def test_get_user_from_email_not_found(db):
    """Test getting user from non-existent email raises exception."""
    with pytest.raises(HTTPException) as exc_info:
        get_user_from_email("nonexistent@example.com", db)
    assert exc_info.value.status_code == 404
