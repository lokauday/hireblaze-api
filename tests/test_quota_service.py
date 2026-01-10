"""
Unit tests for quota service.
Tests quota checking, usage recording, and plan limits.
"""
import pytest
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.user import User
from app.db.models.subscription import Subscription
from app.db.models.usage import UsageEvent
from app.services.quota_service import (
    get_plan_for_user,
    get_month_usage,
    check_and_consume,
    get_usage_for_response,
)
from app.core.security import hash_password


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


def test_get_plan_for_user_free(db, test_user, free_user_subscription):
    """Test getting user plan returns 'free' when subscription exists."""
    plan = get_plan_for_user(db, test_user.id)
    assert plan == "free"


def test_get_plan_for_user_no_subscription(db, test_user):
    """Test getting user plan returns 'free' when no subscription exists."""
    plan = get_plan_for_user(db, test_user.id)
    assert plan == "free"


def test_get_plan_for_user_pro(db, test_user, pro_user_subscription):
    """Test getting user plan returns 'pro'."""
    plan = get_plan_for_user(db, test_user.id)
    assert plan == "pro"


def test_get_month_usage_empty(db, test_user):
    """Test getting usage when no usage records exist."""
    month_key = UsageEvent.get_month_key()
    usage = get_month_usage(db, test_user.id, month_key)
    assert usage == {}


def test_get_month_usage_with_records(db, test_user):
    """Test getting usage with existing records."""
    month_key = UsageEvent.get_month_key()
    
    # Add usage records
    usage1 = UsageEvent(
        user_id=test_user.id,
        feature="ats_scan",
        amount=5,
        month_key=month_key,
        created_at=datetime.utcnow()
    )
    usage2 = UsageEvent(
        user_id=test_user.id,
        feature="ats_scan",
        amount=3,
        month_key=month_key,
        created_at=datetime.utcnow()
    )
    db.add_all([usage1, usage2])
    db.commit()
    
    usage = get_month_usage(db, test_user.id, month_key)
    assert usage["ats_scan"] == 8


def test_check_and_consume_free_plan_under_limit(db, test_user, free_user_subscription):
    """Test quota check allows when under free plan limit."""
    # Free plan: ats_scan limit is 2
    used, limit, remaining = check_and_consume(db, test_user.id, "ats_scan", amount=1)
    
    assert used == 1
    assert limit == 2
    assert remaining == 1
    
    # Verify usage was recorded
    month_key = UsageEvent.get_month_key()
    usage = get_month_usage(db, test_user.id, month_key)
    assert usage["ats_scan"] == 1


def test_check_and_consume_free_plan_exceeds_limit(db, test_user, free_user_subscription):
    """Test quota check blocks when exceeding free plan limit."""
    month_key = UsageEvent.get_month_key()
    
    # Add usage up to the limit (2 for free plan ats_scan)
    for _ in range(2):
        usage = UsageEvent(
            user_id=test_user.id,
            feature="ats_scan",
            amount=1,
            month_key=month_key,
            created_at=datetime.utcnow()
        )
        db.add(usage)
    db.commit()
    
    # Try to use one more - should exceed limit
    used, limit, remaining = check_and_consume(db, test_user.id, "ats_scan", amount=1)
    
    assert used == 2  # Current usage (not increased)
    assert limit == 2
    assert remaining == 0  # Signal exceeded
    
    # Verify usage was NOT recorded (should still be 2)
    usage = get_month_usage(db, test_user.id, month_key)
    assert usage["ats_scan"] == 2  # Should not have increased


def test_check_and_consume_elite_unlimited(db, test_user, elite_user_subscription):
    """Test elite plan users have unlimited quota."""
    # Add many usage records
    month_key = UsageEvent.get_month_key()
    for _ in range(1000):
        usage = UsageEvent(
            user_id=test_user.id,
            feature="ats_scan",
            amount=1,
            month_key=month_key,
            created_at=datetime.utcnow()
        )
        db.add(usage)
    db.commit()
    
    # Should still be allowed (unlimited)
    used, limit, remaining = check_and_consume(db, test_user.id, "ats_scan", amount=1)
    assert limit is None  # Unlimited
    assert remaining == -1  # Signal unlimited
    
    # Verify usage was recorded (should be 1001 now)
    usage = get_month_usage(db, test_user.id, month_key)
    assert usage["ats_scan"] == 1001


def test_get_usage_for_response_free_plan(db, test_user, free_user_subscription):
    """Test get_usage_for_response returns correct structure for free plan."""
    month_key = UsageEvent.get_month_key()
    
    # Add some usage
    usage = UsageEvent(
        user_id=test_user.id,
        feature="ats_scan",
        amount=1,
        month_key=month_key,
        created_at=datetime.utcnow()
    )
    db.add(usage)
    db.commit()
    
    result = get_usage_for_response(db, test_user.id)
    
    assert result["plan"] == "free"
    assert result["month_key"] == month_key
    assert "features" in result
    
    # Check ats_scan feature
    ats_feature = result["features"]["ats_scan"]
    assert ats_feature["limit"] == 2
    assert ats_feature["used"] == 1
    assert ats_feature["remaining"] == 1
    assert ats_feature["unlimited"] is False


def test_get_usage_for_response_elite_plan(db, test_user, elite_user_subscription):
    """Test get_usage_for_response shows unlimited for elite plan."""
    result = get_usage_for_response(db, test_user.id)
    
    assert result["plan"] == "elite"
    
    # Check all features are unlimited
    for feature_name, feature_data in result["features"].items():
        assert feature_data["unlimited"] is True
        assert feature_data["limit"] is None
        assert feature_data["remaining"] is None
