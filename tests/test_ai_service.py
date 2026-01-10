"""
Minimal tests for AI service response validation.
"""
import pytest
from app.services.ai_service import (
    MatchScoreResponse,
    RecruiterLensResponse,
    InterviewPackResponse,
    OutreachResponse
)


def test_match_score_response_validation():
    """Test MatchScoreResponse model validation."""
    # Valid response
    response = MatchScoreResponse(
        match_score=75.5,
        overlap={"skills": ["Python", "Docker"]},
        missing={"skills": ["Kubernetes"]},
        risks={"flags": ["No cloud experience"]},
        improvement_plan={"actions": ["Learn Kubernetes"]},
        recruiter_lens={"summary": "Good fit", "decision": "yes"}
    )
    assert response.match_score == 75.5
    assert isinstance(response.overlap, dict)
    
    # Score clamped to 0-100
    response_low = MatchScoreResponse(match_score=-10, overlap={}, missing={}, risks={}, improvement_plan={}, recruiter_lens={})
    assert response_low.match_score >= 0
    
    response_high = MatchScoreResponse(match_score=150, overlap={}, missing={}, risks={}, improvement_plan={}, recruiter_lens={})
    assert response_high.match_score <= 100


def test_recruiter_lens_response_validation():
    """Test RecruiterLensResponse model validation."""
    response = RecruiterLensResponse(
        first_impression="Strong candidate",
        red_flags=["Gap in employment"],
        strengths=["5 years experience"],
        shortlist_decision="yes",
        fixes=["Address employment gap"]
    )
    assert response.shortlist_decision in ["yes", "no", "maybe"]
    assert isinstance(response.red_flags, list)


def test_interview_pack_response_validation():
    """Test InterviewPackResponse model validation."""
    response = InterviewPackResponse(
        questions=["Question 1", "Question 2"],
        star_outlines={"q1": "Situation: ..."},
        plan_30_60_90={"30_days": "Onboard", "60_days": "Contribute", "90_days": "Lead"},
        additional_prep={"company_research": "..."}
    )
    assert len(response.questions) >= 0
    assert "30_days" in response.plan_30_60_90


def test_outreach_response_validation():
    """Test OutreachResponse model validation."""
    response = OutreachResponse(
        message="Hello, I'm interested in this role.",
        subject="Application Follow-up",
        tone="professional"
    )
    assert len(response.message) > 0
    assert response.tone in ["professional", "casual", "friendly"]
