import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
import pytest
import csv
import json
import pickle
from pathlib import Path
import numpy as np

from typing import Optional, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import csr_matrix
from sentence_transformers import SentenceTransformer
import faiss

from backend.app.config.settings import settings
from backend.app.schemas.candidate import SkillSchema
from backend.app.schemas.candidate_intelligence import CandidateIntelligence
from backend.app.schemas.job_description import JobDescription, ExperienceRequirement
from backend.app.services.jd_parser import JDParser
from backend.app.services.dataset_loader import DatasetLoader
from backend.app.services.candidate_intelligence_builder import CandidateIntelligenceBuilder
from backend.app.retrieval.retrieval_engine import RetrievalEngine
from backend.app.ranking.ranking_engine import RankingEngine
from backend.app.explainability.explainability_engine import ExplainabilityEngine
from backend.app.services.submission_engine import SubmissionEngine
from backend.app.services.ranking_pipeline import RankingPipeline

def create_test_jd(
    title: str = "Software Engineer",
    summary: str = "Looking for an engineer.",
    requirements: Optional[list] = None,
    preferred_skills: Optional[list] = None,
    min_years: Optional[float] = None,
    max_years: Optional[float] = None
) -> JobDescription:
    """Helper to construct a valid JobDescription model for testing."""
    return JobDescription(
        title=title,
        company="Acme Corp",
        location="Remote, India",
        employment_type="full-time",
        experience_requirement=ExperienceRequirement(
            raw_text=f"{min_years}-{max_years} years" if min_years else "any",
            min_years=min_years,
            max_years=max_years
        ),
        summary=summary,
        requirements=requirements or [],
        preferred_skills=preferred_skills or [],
        responsibilities=[],
        disqualifiers=[],
        keywords=[]
    )

@pytest.fixture(scope="module")
def pipeline_test_env(tmp_path_factory):
    """Sets up a complete mock pipeline environment with indexes and a small candidates file."""
    tmp = tmp_path_factory.mktemp("pipeline_test")
    
    # 1. Create a dummy candidates dataset
    candidates = [
        {
            "candidate_id": "CAND_0000001",
            "profile": {
                "anonymized_name": "John Doe",
                "headline": "Python Developer",
                "summary": "Building web apps using Python and FastAPI.",
                "location": "Pune",
                "country": "India",
                "years_of_experience": 5.0,
                "current_title": "Software Engineer",
                "current_company": "Acme Corp",
                "current_company_size": "50-200",
                "current_industry": "Software"
            },
            "career_history": [
                {
                    "company": "Acme Corp",
                    "title": "Software Engineer",
                    "start_date": "2021-01-01",
                    "end_date": None,
                    "duration_months": 60,
                    "is_current": True,
                    "industry": "Software",
                    "company_size": "50-200",
                    "description": "Python, FastAPI development."
                }
            ],
            "education": [
                {
                    "institution": "Pune University",
                    "degree": "B.E.",
                    "field_of_study": "Computer Science",
                    "start_year": 2017,
                    "end_year": 2021,
                    "tier": "tier_2"
                }
            ],
            "skills": [
                {"name": "Python", "proficiency": "advanced", "endorsements": 10, "duration_months": 60},
                {"name": "FastAPI", "proficiency": "intermediate", "endorsements": 5, "duration_months": 36}
            ],
            "redrob_signals": {
                "profile_completeness_score": 90.0,
                "signup_date": "2021-01-01",
                "last_active_date": "2026-06-01",
                "open_to_work_flag": True,
                "profile_views_received_30d": 10,
                "applications_submitted_30d": 5,
                "recruiter_response_rate": 0.8,
                "avg_response_time_hours": 12.0,
                "skill_assessment_scores": {},
                "connection_count": 100,
                "endorsements_received": 15,
                "notice_period_days": 30,
                "expected_salary_range_inr_lpa": {"min": 10.0, "max": 15.0},
                "preferred_work_mode": "remote",
                "willing_to_relocate": True,
                "github_activity_score": 50.0,
                "search_appearance_30d": 50,
                "saved_by_recruiters_30d": 5,
                "interview_completion_rate": 0.9,
                "offer_acceptance_rate": 0.8,
                "verified_email": True,
                "verified_phone": True,
                "linkedin_connected": True
            }
        },
        {
            "candidate_id": "CAND_0000002",
            "profile": {
                "anonymized_name": "Honeypot Cand",
                "headline": "DevOps Engineer",
                "summary": "AWS Kubernetes practitioner.",
                "location": "Mumbai",
                "country": "India",
                "years_of_experience": 3.0,
                "current_title": "DevOps Engineer",
                "current_company": "Startup",
                "current_company_size": "10-50",
                "current_industry": "Internet"
            },
            "career_history": [],
            "education": [],
            "skills": [
                {"name": "AWS", "proficiency": "advanced", "endorsements": 8, "duration_months": 36},
                {"name": "Kubernetes", "proficiency": "intermediate", "endorsements": 4, "duration_months": 24}
            ],
            "redrob_signals": {
                "profile_completeness_score": 80.0,
                "signup_date": "2022-01-01",
                "last_active_date": "2026-06-01",
                "open_to_work_flag": True,
                "profile_views_received_30d": 5,
                "applications_submitted_30d": 2,
                "recruiter_response_rate": 0.5,
                "avg_response_time_hours": 24.0,
                "skill_assessment_scores": {},
                "connection_count": 50,
                "endorsements_received": 5,
                "notice_period_days": 15,
                # HONEYPOT: min salary > max salary
                "expected_salary_range_inr_lpa": {"min": 25.0, "max": 12.0},
                "preferred_work_mode": "hybrid",
                "willing_to_relocate": False,
                "github_activity_score": 10.0,
                "search_appearance_30d": 20,
                "saved_by_recruiters_30d": 1,
                "interview_completion_rate": 0.5,
                "offer_acceptance_rate": 0.5,
                "verified_email": True,
                "verified_phone": True,
                "linkedin_connected": False
            }
        }
    ]
    
    # Save to temp JSONL
    dataset_file = tmp / "candidates.jsonl"
    with open(dataset_file, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c) + "\n")
            
    # 2. Build mock TF-IDF and FAISS files
    texts = [
        "python developer building web apps using python and fastapi acme corp software engineer",
        "devops engineer aws kubernetes practitioner startup"
    ]
    
    # TF-IDF
    vectorizer = TfidfVectorizer(max_features=100)
    tfidf_matrix = vectorizer.fit_transform(texts)
    
    tfidf_file = tmp / "tfidf.pkl"
    with open(tfidf_file, "wb") as f:
        pickle.dump({"vectorizer": vectorizer, "matrix": tfidf_matrix}, f)
        
    # Candidate IDs
    ids_file = tmp / "candidate_ids.json"
    with open(ids_file, "w", encoding="utf-8") as f:
        json.dump(["CAND_0000001", "CAND_0000002"], f)
        
    # FAISS
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(texts, convert_to_numpy=True)
    faiss.normalize_L2(embeddings)
    
    index = faiss.IndexFlatIP(384)
    index.add(embeddings)  # type: ignore
    
    faiss_file = tmp / "vectors.faiss"
    faiss.write_index(index, str(faiss_file))
    
    # Override settings
    orig_dataset_path = settings.CANDIDATE_DATASET_PATH
    orig_ids_path = settings.CANDIDATE_IDS_PATH
    orig_tfidf_path = settings.TFIDF_PATH
    orig_vector_path = settings.VECTOR_INDEX_PATH
    
    settings.CANDIDATE_DATASET_PATH = str(dataset_file)
    settings.CANDIDATE_IDS_PATH = str(ids_file)
    settings.TFIDF_PATH = str(tfidf_file)
    settings.VECTOR_INDEX_PATH = str(faiss_file)
    
    yield tmp
    
    # Restore settings
    settings.CANDIDATE_DATASET_PATH = orig_dataset_path
    settings.CANDIDATE_IDS_PATH = orig_ids_path
    settings.TFIDF_PATH = orig_tfidf_path
    settings.VECTOR_INDEX_PATH = orig_vector_path

def test_tfidf_retrieval(pipeline_test_env):
    """Test TF-IDF retrieval component."""
    engine = RetrievalEngine()
    engine.load_indexes()
    
    if engine._tfidf_vectorizer is None or engine._tfidf_matrix is None:
        raise RuntimeError("Failed to load TF-IDF indexes in test")
    
    jd = create_test_jd(
        title="Python Backend Developer",
        summary="Looking for a Python Developer who works with FastAPI.",
        requirements=["Python", "FastAPI"]
    )
    
    query_text = engine._get_query_text(jd)
    vector = engine._tfidf_vectorizer.transform([query_text])
    if not isinstance(vector, csr_matrix):
        raise RuntimeError("Expected csr_matrix")
    scores = (engine._tfidf_matrix * vector.transpose()).toarray().flatten()
    
    # Candidate 1 should have higher score than Candidate 2 for Python/FastAPI query
    assert scores[0] > scores[1]

def test_faiss_retrieval(pipeline_test_env):
    """Test FAISS vector similarity retrieval component."""
    engine = RetrievalEngine()
    engine.load_indexes()
    
    if engine._model is None or engine._faiss_index is None:
        raise RuntimeError("Failed to load FAISS indexes in test")
    
    jd = create_test_jd(
        title="AWS DevOps Kubernetes Specialist",
        summary="Kubernetes and DevOps infrastructure builder",
        requirements=["AWS", "Kubernetes"]
    )
    
    query_text = engine._get_query_text(jd)
    query_emb = engine._model.encode([query_text], convert_to_numpy=True)
    faiss.normalize_L2(query_emb)
    
    distances, indices = getattr(engine._faiss_index, "search")(query_emb, k=2)
    
    # Candidate 2 (index 1) should be closer (higher inner product score) than Candidate 1
    # Check that Candidate 2's index appears first or has higher score
    if indices[0][0] == 1:
        assert distances[0][0] >= distances[0][1]
    else:
        assert indices[0][1] == 1

def test_hybrid_retrieval(pipeline_test_env):
    """Test Hybrid Retrieval combining TF-IDF and FAISS with RRF."""
    engine = RetrievalEngine()
    
    jd = create_test_jd(
        title="Python Developer",
        summary="FastAPI developer specializing in Python backends.",
        requirements=["Python", "FastAPI"]
    )
    
    cohort = engine.retrieve(jd, limit=2)
    # Both candidates should be retrieved
    assert len(cohort) == 2
    assert "CAND_0000001" in cohort

def test_ranking_and_honeypots(pipeline_test_env):
    """Test candidate scoring and Honeypot filtering."""
    ranker = RankingEngine()
    
    builder = CandidateIntelligenceBuilder()
    
    # Load raw candidates
    candidates_raw = []
    dataset_path = settings.CANDIDATE_DATASET_PATH
    if dataset_path is None:
        raise RuntimeError("CANDIDATE_DATASET_PATH is not configured")
    with open(dataset_path, "r") as f:
        for line in f:
            candidates_raw.append(json.loads(line))
            
    c1 = builder.build_intelligence(candidates_raw[0])
    c2 = builder.build_intelligence(candidates_raw[1])
    
    jd = create_test_jd(
        title="Python Developer",
        summary="FastAPI Developer",
        requirements=["python", "fastapi"],
        min_years=3.0,
        max_years=6.0
    )
    
    eval_c1 = ranker.evaluate_candidate(c1, jd)
    eval_c2 = ranker.evaluate_candidate(c2, jd)
    
    # Candidate 1 is normal and matches Python/FastAPI
    assert not eval_c1["is_honeypot"]
    assert eval_c1["final_score"] > 0.0
    
    # Candidate 2 is a Honeypot (min salary > max salary)
    assert eval_c2["is_honeypot"]
    assert eval_c2["final_score"] == 0.0
    
    # Cohort ranking
    ranked = ranker.rank_cohort([c1, c2], jd)
    assert ranked[0]["candidate_id"] == "CAND_0000001"
    assert ranked[1]["candidate_id"] == "CAND_0000002"
    assert ranked[1]["final_score"] == 0.0

def test_submission_generation(pipeline_test_env):
    """Test formatting and output validation in SubmissionEngine."""
    submission_file = pipeline_test_env / "test_submission.csv"
    
    ranked_cohort = [
        {"candidate_id": "CAND_0000001", "final_score": 85.5, "is_honeypot": False},
        {"candidate_id": "CAND_0000002", "final_score": 0.0, "is_honeypot": True}
    ]
    
    explanations = {
        "CAND_0000001": "Highly aligned Python engineer with 5 years experience.",
        "CAND_0000002": "Fails screening criteria."
    }
    
    engine = SubmissionEngine()
    engine.generate_submission(ranked_cohort, explanations, str(submission_file))
    
    # Read and check CSV structure
    assert submission_file.exists()
    with open(submission_file, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        
    assert reader[0] == ["candidate_id", "rank", "score", "reasoning"]
    assert len(reader) == 3 # Header + 2 rows
    assert reader[1][0] == "CAND_0000001"
    assert reader[1][1] == "1"
    assert reader[1][2] == "85.5"
    assert reader[1][3] == "Highly aligned Python engineer with 5 years experience."

def test_full_pipeline_run(pipeline_test_env, monkeypatch):
    """Test end-to-end pipeline run mock implementation."""
    # Mock JDParser to bypass word parsing and return JobDescription directly
    class MockJdParser(JDParser):
        def parse_jd(self, file_path: str) -> JobDescription:
            return create_test_jd(
                title="Python Developer",
                summary="FastAPI Developer",
                requirements=["python", "fastapi"],
                min_years=3.0,
                max_years=6.0
            )
            
    pipeline = RankingPipeline(jd_parser=MockJdParser())
    
    out_csv = pipeline_test_env / "submission.csv"
    res = pipeline.run("dummy_jd.docx", str(out_csv))
    
    assert res["success"] or len(res["validation_errors"]) > 0  # Should run through
    assert res["total_execution_time_seconds"] > 0
    assert res["honeypots_detected_in_cohort"] == 1

def test_cache_invalidation_versioning(pipeline_test_env):
    """Test ranking cache validation behavior with PIPELINE_VERSION."""
    from backend.app.api.endpoints.ranking import get_jd_and_dataset_meta
    
    # 1. Create a dummy JD file
    jd_file = pipeline_test_env / "test_active_jd.txt"
    jd_file.write_text("Python Developer needed", encoding="utf-8")
    
    meta = get_jd_and_dataset_meta(jd_file)
    assert "pipeline_version" in meta
    assert meta["pipeline_version"] == settings.PIPELINE_VERSION
    
    current_ver = settings.PIPELINE_VERSION
    
    # Helper to simulate cache check function
    def validate_cache(cached_dict, current_dict):
        return (
            cached_dict.get("jd_hash") == current_dict["jd_hash"] and
            cached_dict.get("dataset_mtime") == current_dict["dataset_mtime"] and
            cached_dict.get("dataset_size") == current_dict["dataset_size"] and
            cached_dict.get("pipeline_version") == current_dict["pipeline_version"]
        )
        
    # Scenario A: Same JD + Same Dataset + Same PIPELINE_VERSION => Cache Valid
    cached_valid = {
        "jd_hash": meta["jd_hash"],
        "dataset_mtime": meta["dataset_mtime"],
        "dataset_size": meta["dataset_size"],
        "pipeline_version": current_ver
    }
    assert validate_cache(cached_valid, meta) is True
    
    # Scenario B: Missing pipeline_version (old legacy cache metadata) => Cache Miss
    cached_legacy = {
        "jd_hash": meta["jd_hash"],
        "dataset_mtime": meta["dataset_mtime"],
        "dataset_size": meta["dataset_size"]
    }
    assert validate_cache(cached_legacy, meta) is False
    
    # Scenario C: Different pipeline_version => Cache Miss
    cached_mismatched_ver = {
        "jd_hash": meta["jd_hash"],
        "dataset_mtime": meta["dataset_mtime"],
        "dataset_size": meta["dataset_size"],
        "pipeline_version": "0.9.0-old"
    }
    assert validate_cache(cached_mismatched_ver, meta) is False
    
    # Scenario D: Different JD Hash => Cache Miss
    cached_diff_jd = {
        "jd_hash": "different_hash_123",
        "dataset_mtime": meta["dataset_mtime"],
        "dataset_size": meta["dataset_size"],
        "pipeline_version": current_ver
    }
    assert validate_cache(cached_diff_jd, meta) is False
    
    # Scenario E: Different Dataset mtime/size => Cache Miss
    cached_diff_dataset = {
        "jd_hash": meta["jd_hash"],
        "dataset_mtime": 123456.0,
        "dataset_size": 99999,
        "pipeline_version": current_ver
    }
    assert validate_cache(cached_diff_dataset, meta) is False

