from pydantic import BaseModel, Field
from typing import List, Optional
from backend.app.schemas.candidate import (
    SkillSchema,
    EducationSchema,
    CertificationSchema,
    LanguageSchema,
    CareerHistorySchema,
    RedrobSignalsSchema
)

class CandidateIntelligence(BaseModel):
    # Preserved/extracted raw fields
    candidate_id: str = Field(..., pattern=r"^CAND_[0-9]{7}$")
    name: str
    headline: str
    summary: str
    current_title: str
    current_company: str
    years_of_experience: float = Field(ge=0, le=50)
    skills: List[SkillSchema]
    education: List[EducationSchema]
    certifications: Optional[List[CertificationSchema]] = None
    languages: Optional[List[LanguageSchema]] = None
    career_history: List[CareerHistorySchema]
    behavioral_signals: RedrobSignalsSchema
    notice_period: int = Field(ge=0, le=180)
    location: str

    # Derived normalized fields
    normalized_skills: List[str]
    normalized_titles: List[str]
    work_history_text: str
    skills_text: str
    profile_text: str
    career_text: str
    education_text: str
