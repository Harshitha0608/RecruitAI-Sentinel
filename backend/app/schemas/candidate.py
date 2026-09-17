from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import date

class ProfileSchema(BaseModel):
    anonymized_name: str
    headline: str
    summary: str
    location: str
    country: str
    years_of_experience: float = Field(ge=0, le=50)
    current_title: str
    current_company: str
    current_company_size: str
    current_industry: str

class CareerHistorySchema(BaseModel):
    company: str
    title: str
    start_date: str
    end_date: Optional[str] = None
    duration_months: int = Field(ge=0)
    is_current: bool
    industry: str
    company_size: str
    description: str

class EducationSchema(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_year: int = Field(ge=1970, le=2030)
    end_year: int = Field(ge=1970, le=2035)
    grade: Optional[str] = None
    tier: str

class SkillSchema(BaseModel):
    name: str
    proficiency: str
    endorsements: int = Field(ge=0)
    duration_months: Optional[int] = Field(default=0, ge=0)

class CertificationSchema(BaseModel):
    name: str
    issuer: str
    year: int

class LanguageSchema(BaseModel):
    language: str
    proficiency: str

class ExpectedSalarySchema(BaseModel):
    min: float = Field(ge=0)
    max: float = Field(ge=0)

class RedrobSignalsSchema(BaseModel):
    profile_completeness_score: float = Field(ge=0, le=100)
    signup_date: str
    last_active_date: str
    open_to_work_flag: bool
    profile_views_received_30d: int = Field(ge=0)
    applications_submitted_30d: int = Field(ge=0)
    recruiter_response_rate: float = Field(ge=0.0, le=1.0)
    avg_response_time_hours: float = Field(ge=0.0)
    skill_assessment_scores: Dict[str, float]
    connection_count: int = Field(ge=0)
    endorsements_received: int = Field(ge=0)
    notice_period_days: int = Field(ge=0, le=180)
    expected_salary_range_inr_lpa: ExpectedSalarySchema
    preferred_work_mode: str
    willing_to_relocate: bool
    github_activity_score: float = Field(ge=-1.0, le=100.0)
    search_appearance_30d: int = Field(ge=0)
    saved_by_recruiters_30d: int = Field(ge=0)
    interview_completion_rate: float = Field(ge=0.0, le=1.0)
    offer_acceptance_rate: float = Field(ge=-1.0, le=1.0)
    verified_email: bool
    verified_phone: bool
    linkedin_connected: bool

class CandidateSchema(BaseModel):
    candidate_id: str = Field(pattern=r"^CAND_[0-9]{7}$")
    profile: ProfileSchema
    career_history: List[CareerHistorySchema]
    education: List[EducationSchema]
    skills: List[SkillSchema]
    certifications: Optional[List[CertificationSchema]] = None
    languages: Optional[List[LanguageSchema]] = None
    redrob_signals: RedrobSignalsSchema
