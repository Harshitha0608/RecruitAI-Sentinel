import pytest
from pydantic import ValidationError
from typing import Dict, Any

from backend.app.schemas.candidate import CandidateSchema
from backend.app.schemas.candidate_intelligence import CandidateIntelligence
from backend.app.services.candidate_intelligence_builder import CandidateIntelligenceBuilder

@pytest.fixture
def mock_candidate_data() -> Dict[str, Any]:
    return {
        "candidate_id": "CAND_1234567",
        "profile": {
            "anonymized_name": "  Alice  Smith  ",
            "headline": "Senior Software Engineer\nPython Developer",
            "summary": "Experienced in building scalable API services. Passionate about machine learning.",
            "location": "Bangalore",
            "country": "India",
            "years_of_experience": 8.5,
            "current_title": "Senior Software Engineer",
            "current_company": "Tech Corp",
            "current_company_size": "500-1000",
            "current_industry": "Software Development"
        },
        "career_history": [
            {
                "company": "Tech Corp",
                "title": "Senior Software Engineer",
                "start_date": "2022-01-01",
                "end_date": None,
                "duration_months": 53,
                "is_current": True,
                "industry": "Software Development",
                "company_size": "500-1000",
                "description": "Led the backend engineering team. Built microservices with FastAPI and Python."
            },
            {
                "company": "Startup Inc",
                "title": "Software Engineer",
                "start_date": "2019-01-01",
                "end_date": "2021-12-31",
                "duration_months": 36,
                "is_current": False,
                "industry": "Software Development",
                "company_size": "10-50",
                "description": "Developed backend systems. Managed databases."
            }
        ],
        "education": [
            {
                "institution": "IIT Madras",
                "degree": "B.Tech",
                "field_of_study": "Computer Science",
                "start_year": 2014,
                "end_year": 2018,
                "grade": "8.5 CGPA",
                "tier": "tier_1"
            }
        ],
        "skills": [
            {"name": "Python", "proficiency": "advanced", "endorsements": 15, "duration_months": 96},
            {"name": "Python", "proficiency": "advanced", "endorsements": 5, "duration_months": 48},  # Duplicate skill
            {"name": "FastAPI", "proficiency": "intermediate", "endorsements": 10, "duration_months": 36},
            {"name": "  Docker  ", "proficiency": "intermediate", "endorsements": 3, "duration_months": 24}
        ],
        "certifications": [
            {
                "name": "AWS Certified Solutions Architect",
                "issuer": "Amazon Web Services",
                "year": 2023
            }
        ],
        "languages": [
            {
                "language": "English",
                "proficiency": "native"
            }
        ],
        "redrob_signals": {
            "profile_completeness_score": 95.0,
            "signup_date": "2020-05-01",
            "last_active_date": "2026-06-25",
            "open_to_work_flag": True,
            "profile_views_received_30d": 45,
            "applications_submitted_30d": 5,
            "recruiter_response_rate": 0.9,
            "avg_response_time_hours": 6.5,
            "skill_assessment_scores": {"Python": 95.0, "FastAPI": 88.0},
            "connection_count": 520,
            "endorsements_received": 42,
            "notice_period_days": 15,
            "expected_salary_range_inr_lpa": {"min": 25.0, "max": 35.0},
            "preferred_work_mode": "remote",
            "willing_to_relocate": False,
            "github_activity_score": 78.5,
            "search_appearance_30d": 150,
            "saved_by_recruiters_30d": 8,
            "interview_completion_rate": 1.0,
            "offer_acceptance_rate": 0.85,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True
        }
    }

def test_builder_from_dict(mock_candidate_data: Dict[str, Any]):
    builder = CandidateIntelligenceBuilder()
    intel = builder.build_intelligence(mock_candidate_data)

    assert isinstance(intel, CandidateIntelligence)
    assert intel.candidate_id == "CAND_1234567"
    assert intel.name == "Alice Smith"  # Whitespace normalized
    assert intel.headline == "Senior Software Engineer Python Developer"  # Newline converted to space
    assert intel.years_of_experience == 8.5
    assert intel.notice_period == 15
    assert intel.location == "Bangalore, India"

    # Test raw arrays preserved
    assert len(intel.skills) == 4
    assert len(intel.education) == 1
    assert len(intel.career_history) == 2
    assert intel.certifications is not None
    assert len(intel.certifications) == 1
    assert intel.languages is not None
    assert len(intel.languages) == 1
    
    # Test derived fields
    # 1. Deduplication and normalization
    # Python is duplicated, Docker has trailing whitespace
    assert intel.normalized_skills == ["python", "fastapi", "docker"]
    assert intel.normalized_titles == ["senior software engineer", "software engineer"]

    # 2. skills_text
    assert intel.skills_text == "python fastapi docker"

    # 3. profile_text
    # Combination of name, headline, summary, current_title, current_company (all normalized)
    expected_profile = "alice smith senior software engineer python developer experienced in building scalable api services. passionate about machine learning. senior software engineer tech corp"
    assert intel.profile_text == expected_profile

    # 4. work_history_text
    expected_work = (
        "senior software engineer tech corp led the backend engineering team. built microservices with fastapi and python. "
        "software engineer startup inc developed backend systems. managed databases."
    ).lower()
    assert intel.work_history_text == expected_work

    # 5. career_text
    expected_career = f"{expected_profile} {expected_work}"
    assert intel.career_text == expected_career

    # 6. education_text
    expected_edu = "iit madras b.tech computer science tier_1"
    assert intel.education_text == expected_edu

def test_builder_from_schema(mock_candidate_data: Dict[str, Any]):
    builder = CandidateIntelligenceBuilder()
    candidate = CandidateSchema(**mock_candidate_data)
    intel = builder.build_intelligence(candidate)

    assert isinstance(intel, CandidateIntelligence)
    assert intel.candidate_id == "CAND_1234567"
    assert intel.name == "Alice Smith"

def test_builder_validation_error():
    builder = CandidateIntelligenceBuilder()
    invalid_data = {
        "candidate_id": "INVALID_ID",  # Fails pattern
        "profile": {}
    }
    with pytest.raises(ValidationError):
        builder.build_intelligence(invalid_data)
