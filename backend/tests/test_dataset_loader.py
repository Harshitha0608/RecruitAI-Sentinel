import pytest
import json
from pathlib import Path
from backend.app.services.dataset_loader import DatasetLoader
from backend.app.config.settings import settings

@pytest.fixture
def temp_dataset(tmp_path: Path):
    # Create mock schema
    schema_data = {
        "required": ["candidate_id", "profile", "career_history", "education", "skills", "redrob_signals"],
        "properties": {
            "profile": {
                "required": ["anonymized_name", "headline", "summary", "years_of_experience"]
            }
        }
    }
    schema_file = tmp_path / "candidate_schema.json"
    schema_file.write_text(json.dumps(schema_data))

    # Create mock candidates file
    candidates = [
        # Valid Candidate 1
        {
            "candidate_id": "CAND_0000001",
            "profile": {
                "anonymized_name": "Ira Vora",
                "headline": "Backend Engineer",
                "summary": "Experienced python developer.",
                "location": "Toronto",
                "country": "Canada",
                "years_of_experience": 5.0,
                "current_title": "Backend Engineer",
                "current_company": "Mindtree",
                "current_company_size": "10001+",
                "current_industry": "IT Services"
            },
            "career_history": [
                {
                    "company": "Mindtree",
                    "title": "Backend Engineer",
                    "start_date": "2024-03-08",
                    "end_date": None,
                    "duration_months": 27,
                    "is_current": True,
                    "industry": "IT Services",
                    "company_size": "10001+",
                    "description": "Building Python backend service API."
                }
            ],
            "education": [
                {
                    "institution": "LPU",
                    "degree": "B.E.",
                    "field_of_study": "Computer Science",
                    "start_year": 2017,
                    "end_year": 2020,
                    "grade": "8.24 CGPA",
                    "tier": "tier_3"
                }
            ],
            "skills": [
                {"name": "Python", "proficiency": "advanced", "endorsements": 10, "duration_months": 36},
                {"name": "FastAPI", "proficiency": "advanced", "endorsements": 5, "duration_months": 24}
            ],
            "redrob_signals": {
                "profile_completeness_score": 86.9,
                "signup_date": "2025-10-16",
                "last_active_date": "2026-05-20",
                "open_to_work_flag": True,
                "profile_views_received_30d": 23,
                "applications_submitted_30d": 2,
                "recruiter_response_rate": 0.85,
                "avg_response_time_hours": 12.0,
                "skill_assessment_scores": {"Python": 90.0},
                "connection_count": 356,
                "endorsements_received": 35,
                "notice_period_days": 30,
                "expected_salary_range_inr_lpa": {"min": 15.0, "max": 25.0},
                "preferred_work_mode": "hybrid",
                "willing_to_relocate": True,
                "github_activity_score": 85.0,
                "search_appearance_30d": 249,
                "saved_by_recruiters_30d": 4,
                "interview_completion_rate": 0.90,
                "offer_acceptance_rate": 0.80,
                "verified_email": True,
                "verified_phone": True,
                "linkedin_connected": True
            }
        },
        # Valid Candidate 2: Missing Summary & Empty Skills/Work
        {
            "candidate_id": "CAND_0000002",
            "profile": {
                "anonymized_name": "Saanvi Sethi",
                "headline": "Frontend Dev",
                "summary": "  ", # Empty summary
                "location": "Chennai",
                "country": "India",
                "years_of_experience": 3.0,
                "current_title": "Developer",
                "current_company": "Wipro",
                "current_company_size": "10001+",
                "current_industry": "IT Services"
            },
            "career_history": [], # Missing work history
            "education": [],
            "skills": [], # Missing skills
            "redrob_signals": {
                "profile_completeness_score": 50.0,
                "signup_date": "2025-07-28",
                "last_active_date": "2025-11-12",
                "open_to_work_flag": True,
                "profile_views_received_30d": 7,
                "applications_submitted_30d": 1,
                "recruiter_response_rate": 0.29,
                "avg_response_time_hours": 171.6,
                "skill_assessment_scores": {},
                "connection_count": 179,
                "endorsements_received": 3,
                "notice_period_days": 60,
                "expected_salary_range_inr_lpa": {"min": 8.0, "max": 12.0},
                "preferred_work_mode": "remote",
                "willing_to_relocate": False,
                "github_activity_score": -1.0,
                "search_appearance_30d": 50,
                "saved_by_recruiters_30d": 1,
                "interview_completion_rate": 0.70,
                "offer_acceptance_rate": -1.0,
                "verified_email": True,
                "verified_phone": False,
                "linkedin_connected": False
            }
        },
        # Malformed Candidate (Non-JSON line)
        "invalid json string",
        # Malformed Candidate (Missing profile root key)
        {
            "candidate_id": "CAND_0000003"
            # Missing other root keys
        }
    ]

    dataset_file = tmp_path / "candidates.jsonl"
    with open(dataset_file, "w", encoding="utf-8") as f:
        for item in candidates:
            if isinstance(item, str):
                f.write(item + "\n")
            else:
                f.write(json.dumps(item) + "\n")

    # Create mock job description
    jd_file = tmp_path / "job_description.txt"
    jd_file.write_text("Looking for Senior Python Developer with 5 years experience.")

    return {
        "root": str(tmp_path),
        "dataset": str(dataset_file),
        "jd": str(jd_file)
    }

def test_dataset_loader(temp_dataset):
    # Override settings configuration paths
    settings.CHALLENGE_ROOT = temp_dataset["root"]
    settings.CANDIDATE_DATASET_PATH = temp_dataset["dataset"]
    settings.JOB_DESCRIPTION_PATH = temp_dataset["jd"]

    loader = DatasetLoader()

    # Verify schema loading
    schema = loader.load_candidate_schema()
    assert "required" in schema
    assert "profile" in schema["properties"]

    # Verify job description loading
    jd = loader.load_job_description()
    assert jd == {"raw_text": "Looking for Senior Python Developer with 5 years experience."}

    # Verify candidate streaming using generator
    candidates = list(loader.load_candidates())
    assert len(candidates) == 2 # 2 valid, 2 skipped/malformed
    assert candidates[0]["candidate_id"] == "CAND_0000001"
    assert candidates[1]["candidate_id"] == "CAND_0000002"

    # Verify dataset statistics
    stats = loader.get_dataset_statistics()
    assert stats["total candidates"] == 2
    assert stats["malformed candidates"] == 2
    assert stats["average skills"] == 1.0 # 2 skills for Cand 1, 0 skills for Cand 2
    assert stats["average experience"] == 4.0 # (5.0 + 3.0) / 2
    assert stats["missing summaries"] == 1 # Cand 2 has empty summary
    assert stats["missing skills"] == 1 # Cand 2 has no skills
    assert stats["missing work history"] == 1 # Cand 2 has empty history
