"""
Simple tests for feature gating (manual verification).

Run with: python -m pytest tests/test_gating_simple.py -v
Or: python tests/test_gating_simple.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    print("pytest not available - skipping structured tests")


def test_free_user_limit():
    """Test that free users have a daily limit."""
    from app.core.config import MAX_FREE_AI_CALLS_PER_DAY
    
    assert MAX_FREE_AI_CALLS_PER_DAY > 0, "Free user limit should be > 0"
    assert MAX_FREE_AI_CALLS_PER_DAY <= 10, "Free user limit should be reasonable"
    
    print(f"Free user daily limit: {MAX_FREE_AI_CALLS_PER_DAY}")


def test_gating_functions_exist():
    """Test that gating functions are importable."""
    from app.core.gating import (
        get_user_plan,
        is_premium,
        get_today_ai_usage,
        increment_ai_usage,
        enforce_ai_limit
    )
    
    assert callable(get_user_plan)
    assert callable(is_premium)
    assert callable(get_today_ai_usage)
    assert callable(increment_ai_usage)
    assert callable(enforce_ai_limit)
    
    print("All gating functions are importable")


if __name__ == "__main__":
    print("Running simple gating tests...")
    test_free_user_limit()
    test_gating_functions_exist()
    print("\nAll simple tests passed!")
