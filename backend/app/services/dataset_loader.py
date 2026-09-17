import os
import json
import logging
from typing import Generator, Dict, Any, Optional
from pathlib import Path
import docx
from pydantic import ValidationError

from backend.app.config.settings import settings
from backend.app.schemas.candidate import CandidateSchema

logger = logging.getLogger("app.services.dataset_loader")

class DatasetLoader:
    def __init__(self) -> None:
        self.challenge_root = settings.CHALLENGE_ROOT
        self.dataset_path = settings.CANDIDATE_DATASET_PATH
        self.jd_path = settings.JOB_DESCRIPTION_PATH
        self.offsets_path = getattr(settings, "CANDIDATE_OFFSETS_PATH", None)
        self._offsets = None
        
        # Internal count of malformed candidates detected during generation
        self._malformed_count = 0

        # Output path warnings if paths are missing
        if not self.challenge_root:
            logger.warning("DatasetLoader init warning: CHALLENGE_ROOT is missing from settings.")
        if not self.dataset_path:
            logger.warning("DatasetLoader init warning: CANDIDATE_DATASET_PATH is missing from settings.")
        if not self.jd_path:
            logger.warning("DatasetLoader init warning: JOB_DESCRIPTION_PATH is missing from settings.")

    def load_candidate_by_id(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """Loads a single candidate by ID using the precomputed byte offset index for O(1) speed."""
        if not self.dataset_path:
            logger.error("Dataset path is not configured.")
            return None

        offsets_dict = self._offsets
        if offsets_dict is None:
            if self.offsets_path and Path(self.offsets_path).exists():
                try:
                    with open(self.offsets_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            self._offsets = loaded
                        else:
                            self._offsets = {}
                except Exception as e:
                    logger.error(f"Failed to load candidate offsets map: {e}")
                    self._offsets = {}
            else:
                self._offsets = {}
            offsets_dict = self._offsets

        offset = offsets_dict.get(candidate_id)
        if offset is not None:
            try:
                with open(self.dataset_path, "rb") as f:
                    f.seek(offset)
                    line = f.readline()
                    if line:
                        parsed = json.loads(line.decode("utf-8"))
                        if isinstance(parsed, dict):
                            return parsed
            except Exception as e:
                logger.error(f"Error seeking/reading candidate {candidate_id} at offset {offset}: {e}")
                
        # Fallback to scanning if offset index is missing or lookup fails
        logger.warning(f"Offset lookup failed for candidate {candidate_id}. Falling back to full scan.")
        for cand in self.load_candidates():
            if cand.get("candidate_id") == candidate_id:
                return cand
        return None



    def load_candidate_schema(self) -> Dict[str, Any]:
        """Loads candidate_schema.json from CHALLENGE_ROOT if available."""
        if not self.challenge_root:
            logger.warning("Cannot load schema: CHALLENGE_ROOT is not set.")
            return {}
        
        schema_path = Path(self.challenge_root) / "candidate_schema.json"
        if not schema_path.exists():
            logger.warning(f"Schema file not found at: {schema_path}")
            return {}
            
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load candidate schema JSON: {e}")
            return {}

    def _validate_structural_schema(self, candidate: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Performs structural integrity validation against loaded candidate_schema.json."""
        if not schema:
            return True # If schema is unavailable, bypass this check and rely on Pydantic
            
        required_root_keys = schema.get("required", [])
        for key in required_root_keys:
            if key not in candidate:
                logger.warning(f"Candidate validation failed: Missing required root key '{key}'")
                return False
                
        # Validate profile inner structure requirements
        profile_schema = schema.get("properties", {}).get("profile", {})
        required_profile_keys = profile_schema.get("required", [])
        candidate_profile = candidate.get("profile", {})
        if not isinstance(candidate_profile, dict):
            logger.warning("Candidate validation failed: 'profile' key must be a dictionary.")
            return False
            
        for key in required_profile_keys:
            if key not in candidate_profile:
                logger.warning(f"Candidate validation failed: Missing required profile key '{key}'")
                return False
                
        return True

    def load_candidates(self) -> Generator[Dict[str, Any], None, None]:
        """Streams candidate profiles from JSONL dataset line-by-line using a generator."""
        self._malformed_count = 0 # Reset count
        
        if not self.dataset_path:
            logger.error("Cannot load candidates: CANDIDATE_DATASET_PATH is not configured.")
            return
            
        dataset_file = Path(self.dataset_path)
        if not dataset_file.exists():
            logger.error(f"Dataset file does not exist at: {dataset_file}")
            return

        schema = self.load_candidate_schema()
        
        try:
            with open(dataset_file, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f, 1):
                    line_str = line.strip()
                    if not line_str:
                        continue
                        
                    try:
                        candidate_data = json.loads(line_str)
                    except json.JSONDecodeError as jde:
                        logger.warning(f"Malformed candidate skipped: Line {line_idx} is not valid JSON. Error: {jde}")
                        self._malformed_count += 1
                        continue

                    # Validate against candidate_schema.json if loaded
                    if not self._validate_structural_schema(candidate_data, schema):
                        self._malformed_count += 1
                        continue

                    # Validate against Pydantic schema model
                    try:
                        CandidateSchema(**candidate_data)
                    except ValidationError as ve:
                        cid = candidate_data.get("candidate_id", "UNKNOWN")
                        logger.warning(f"Malformed candidate skipped: Candidate {cid} (Line {line_idx}) failed Pydantic validation. Errors: {ve.errors()}")
                        self._malformed_count += 1
                        continue

                    yield candidate_data
        except OSError as oe:
            logger.error(f"Failed to open or read candidates dataset: {oe}")

    def load_job_description(self) -> Dict[str, Any]:
        """Loads and returns text content from the job description file path."""
        if not self.jd_path:
            logger.error("Cannot load job description: JOB_DESCRIPTION_PATH is not configured.")
            return {}
            
        jd_file = Path(self.jd_path)
        if not jd_file.exists():
            logger.error(f"Job Description file does not exist at: {jd_file}")
            return {}
            
        try:
            suffix = jd_file.suffix.lower()
            if suffix == ".docx":
                doc = docx.Document(str(jd_file))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                return {"raw_text": "\n".join(paragraphs)}
            elif suffix in [".txt", ".md"]:
                with open(jd_file, "r", encoding="utf-8") as f:
                    return {"raw_text": f.read()}
            else:
                logger.error(f"Unsupported Job Description file format: {suffix}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load job description: {e}")
            return {}

    def get_dataset_statistics(self) -> Dict[str, Any]:
        """Iterates the candidates dataset stream once and calculates aggregate stats."""
        total_candidates = 0
        total_skills_count = 0
        total_experience_years = 0.0
        missing_summaries = 0
        missing_skills = 0
        missing_work_history = 0

        # Stream candidate stream line-by-line
        for candidate in self.load_candidates():
            total_candidates += 1
            
            profile = candidate.get("profile", {})
            summary = profile.get("summary", "")
            if not summary or not summary.strip():
                missing_summaries += 1
                
            years_exp = profile.get("years_of_experience", 0.0)
            total_experience_years += float(years_exp)
            
            skills_list = candidate.get("skills", [])
            total_skills_count += len(skills_list)
            if not skills_list:
                missing_skills += 1
                
            career_history = candidate.get("career_history", [])
            if not career_history:
                missing_work_history += 1

        avg_skills = (total_skills_count / total_candidates) if total_candidates > 0 else 0.0
        avg_experience = (total_experience_years / total_candidates) if total_candidates > 0 else 0.0

        return {
            "total candidates": total_candidates,
            "malformed candidates": self._malformed_count,
            "average skills": round(avg_skills, 2),
            "average experience": round(avg_experience, 2),
            "missing summaries": missing_summaries,
            "missing skills": missing_skills,
            "missing work history": missing_work_history
        }
