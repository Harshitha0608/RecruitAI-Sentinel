from pydantic import BaseModel
from typing import List

class SkillAnalysis(BaseModel):
    normalized_candidate_skills: List[str]
    normalized_required_skills: List[str]
    normalized_preferred_skills: List[str]
    exact_matches: List[str]
    synonym_matches: List[str]
    missing_required_skills: List[str]
    missing_preferred_skills: List[str]
    additional_candidate_skills: List[str]
