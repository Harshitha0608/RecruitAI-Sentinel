from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ExperienceRequirement(BaseModel):
    raw_text: str
    min_years: Optional[float] = None
    max_years: Optional[float] = None

class JobDescription(BaseModel):
    title: str
    company: str
    location: str
    employment_type: str
    experience_requirement: ExperienceRequirement
    education: str = "unknown"
    summary: str
    requirements: List[str]          # Core needs / Required skills
    preferred_skills: List[str]      # Nice-to-haves
    responsibilities: List[str]      # Core tasks / duties
    disqualifiers: List[str]         # Exclusions
    keywords: List[str]              # Extracted key terms (lowercase, normalized, unique)
    
    # New structured fields for Hackathon evaluations (FIX 1)
    technical_skills: Optional[List[str]] = []
    programming_languages: Optional[List[str]] = []
    frameworks: Optional[List[str]] = []
    libraries: Optional[List[str]] = []
    cloud_platforms: Optional[List[str]] = []
    databases: Optional[List[str]] = []
    vector_databases: Optional[List[str]] = []
    ai_technologies: Optional[List[str]] = []
    soft_skills: Optional[List[str]] = []
    certifications: Optional[List[str]] = []
    nice_to_have: Optional[List[str]] = []
    kpis: Optional[List[str]] = []
    work_mode: Optional[str] = "unknown"
    relocation: Optional[str] = "unknown"
    notice_preference: Optional[str] = "unknown"
    salary: Optional[str] = "unknown"

    # Extraction confidence metrics
    low_confidence: bool = False
    warnings: List[str] = []

