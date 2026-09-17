import re
import logging
from typing import Dict, Any, List, Optional
from pydantic import ValidationError

from backend.app.schemas.candidate import CandidateSchema
from backend.app.schemas.candidate_intelligence import CandidateIntelligence

logger = logging.getLogger("app.services.candidate_intelligence_builder")

def normalize_text(text: Optional[str]) -> str:
    """Normalizes whitespace and converts text to lowercase.
    
    Collapses multiple whitespace characters (spaces, tabs, newlines) into a single space
    and strips leading/trailing space.
    """
    if not text:
        return ""
    # Collapse multiple whitespaces to a single space
    cleaned = re.sub(r"\s+", " ", text)
    return cleaned.strip().lower()

def normalize_raw_string(text: Optional[str]) -> str:
    """Normalizes whitespace but preserves original capitalization."""
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text)
    return cleaned.strip()

def normalize_and_deduplicate_list(items: List[str]) -> List[str]:
    """Normalizes capitalization and whitespace, then removes duplicate strings while preserving order."""
    seen = set()
    result = []
    for item in items:
        normalized = normalize_text(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result

class CandidateIntelligenceBuilder:
    """Service to parse, extract, and build CandidateIntelligence profiles from candidate records."""

    def __init__(self) -> None:
        pass

    def build_intelligence(self, candidate_data: CandidateSchema | Dict[str, Any]) -> CandidateIntelligence:
        """Processes candidate data and returns a structured CandidateIntelligence object."""
        # Convert dictionary to CandidateSchema if necessary
        if isinstance(candidate_data, dict):
            try:
                candidate = CandidateSchema(**candidate_data)
            except ValidationError as ve:
                logger.error(
                    "Pydantic validation failed for candidate data dictionary",
                    extra={"error": ve.errors()}
                )
                raise ve
        else:
            candidate = candidate_data

        logger.debug(
            "Building intelligence profile for candidate",
            extra={"candidate_id": candidate.candidate_id}
        )

        # 1. Extracted and normalized raw fields (preserving casing, normalizing whitespace)
        candidate_id = candidate.candidate_id
        name = normalize_raw_string(candidate.profile.anonymized_name)
        headline = normalize_raw_string(candidate.profile.headline)
        summary = normalize_raw_string(candidate.profile.summary)
        current_title = normalize_raw_string(candidate.profile.current_title)
        current_company = normalize_raw_string(candidate.profile.current_company)
        years_of_experience = candidate.profile.years_of_experience
        
        # Sub-schemas are already Pydantic-validated, we pass them as-is
        skills = candidate.skills
        education = candidate.education
        certifications = candidate.certifications
        languages = candidate.languages
        career_history = candidate.career_history
        behavioral_signals = candidate.redrob_signals
        
        notice_period = candidate.redrob_signals.notice_period_days
        
        # Location extraction and normalization
        location_parts = []
        if candidate.profile.location:
            location_parts.append(candidate.profile.location)
        if candidate.profile.country:
            location_parts.append(candidate.profile.country)
        location = normalize_raw_string(", ".join(location_parts))

        # Log warning if optional fields are missing
        if not certifications:
            logger.debug("No certifications found for candidate", extra={"candidate_id": candidate_id})
        if not languages:
            logger.debug("No languages found for candidate", extra={"candidate_id": candidate_id})

        # 2. Produce derived values only (lowercase, whitespace-trimmed, deduplicated)
        normalized_skills = normalize_and_deduplicate_list([s.name for s in skills])
        normalized_titles = normalize_and_deduplicate_list([job.title for job in career_history])

        # Concatenate work history details
        job_texts = []
        for job in career_history:
            job_details = f"{job.title} {job.company} {job.description}"
            job_texts.append(job_details)
        work_history_text = normalize_text(" ".join(job_texts))

        # Concatenate skills text
        skills_text = " ".join(normalized_skills)

        # Concatenate profile details
        raw_profile_text = f"{name} {headline} {summary} {current_title} {current_company}"
        profile_text = normalize_text(raw_profile_text)

        # Concatenate career text
        career_text = normalize_text(f"{profile_text} {work_history_text}")

        # Concatenate education details
        edu_texts = []
        for edu in education:
            edu_details = f"{edu.institution} {edu.degree} {edu.field_of_study} {edu.tier}"
            edu_texts.append(edu_details)
        education_text = normalize_text(" ".join(edu_texts))

        # Construct final Pydantic model
        intelligence = CandidateIntelligence(
            candidate_id=candidate_id,
            name=name,
            headline=headline,
            summary=summary,
            current_title=current_title,
            current_company=current_company,
            years_of_experience=years_of_experience,
            skills=skills,
            education=education,
            certifications=certifications,
            languages=languages,
            career_history=career_history,
            behavioral_signals=behavioral_signals,
            notice_period=notice_period,
            location=location,
            normalized_skills=normalized_skills,
            normalized_titles=normalized_titles,
            work_history_text=work_history_text,
            skills_text=skills_text,
            profile_text=profile_text,
            career_text=career_text,
            education_text=education_text
        )

        logger.debug(
            "Successfully built CandidateIntelligence profile",
            extra={"candidate_id": candidate_id}
        )

        return intelligence
