from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

from backend.app.schemas.candidate import (
    SkillSchema,
    CareerHistorySchema,
    EducationSchema,
    RedrobSignalsSchema
)

class HealthResponse(BaseModel):
    status: str = "healthy"

class PrecomputeResponse(BaseModel):
    status: str
    message: str

class RankResponseItem(BaseModel):
    candidate_id: str
    rank: int
    score: float
    reasoning: str
    years_of_experience: Optional[float] = None
    location: Optional[str] = None
    is_honeypot: Optional[bool] = None
    open_to_work: Optional[bool] = None
    notice_period_days: Optional[int] = None
    skills: Optional[List[str]] = None
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    name: Optional[str] = None
    score_breakdown: Optional["ScoreBreakdown"] = None
    critical_skills_matched: Optional[List[str]] = None
    important_skills_matched: Optional[List[str]] = None
    nice_to_have_skills_matched: Optional[List[str]] = None
    missing_critical_skills: Optional[List[str]] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None


class RankResponse(BaseModel):
    success: bool
    candidates: List[RankResponseItem]

class ScoreBreakdown(BaseModel):
    skill_score: float
    experience_score: float
    education_score: float
    project_score: float
    behavior_score: float
    availability_score: float
    engagement_bonus: float
    final_score: float

class CandidateDetailResponse(BaseModel):
    candidate_id: str
    name: str
    headline: str
    summary: str
    current_title: str
    current_company: str
    years_of_experience: float
    location: str
    is_honeypot: bool
    score_breakdown: ScoreBreakdown
    reasoning: str
    skills: Optional[List[SkillSchema]] = None
    career_history: Optional[List[CareerHistorySchema]] = None
    education: Optional[List[EducationSchema]] = None
    behavioral_signals: Optional[RedrobSignalsSchema] = None
    critical_skills_matched: Optional[List[str]] = None
    important_skills_matched: Optional[List[str]] = None
    nice_to_have_skills_matched: Optional[List[str]] = None
    missing_critical_skills: Optional[List[str]] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None

class AnalyticsResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    candidate_count: int
    indexed_candidates: int
    embedding_dimension: int
    faiss_loaded: bool
    tfidf_loaded: bool
    model_loaded: bool
    latest_retrieval_latency_ms: Optional[float] = None
    latest_pipeline_runtime_ms: Optional[float] = None
    latest_honeypot_rate: Optional[float] = None
    sqlite_connected: bool = False
    latest_cohort_size: Optional[int] = None
    latest_honeypots_count: Optional[int] = None
    top_universities: Optional[List[Dict[str, Any]]] = None
    top_locations: Optional[List[Dict[str, Any]]] = None
    top_missing_skills: Optional[List[Dict[str, Any]]] = None
    work_mode_distribution: Optional[List[Dict[str, Any]]] = None
    education_distribution: Optional[List[Dict[str, Any]]] = None



class PrecomputeStatusResponse(BaseModel):
    status: str
    progress: int
    message: str


