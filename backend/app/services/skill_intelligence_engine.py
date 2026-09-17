import logging
import json
import re
from pathlib import Path
from typing import Dict, Set, List, Optional

from backend.app.schemas.candidate_intelligence import CandidateIntelligence
from backend.app.schemas.job_description import JobDescription
from backend.app.schemas.skill_analysis import SkillAnalysis
from backend.app.config.settings import settings

logger = logging.getLogger("app.services.skill_intelligence_engine")

class SkillIntelligenceEngine:
    """Engine to perform synonym-aware, case-insensitive, deterministic skill analysis

    without any scoring, heuristics, or percentages.
    """

    def __init__(self, synonyms_path: Optional[Path] = None) -> None:
        self.synonyms_path: Path = (
            synonyms_path
            if synonyms_path is not None
            else Path(settings.SKILL_SYNONYMS_PATH)
        )
        self.synonym_map = self._load_synonyms()

    def _load_synonyms(self) -> Dict[str, str]:
        """Loads synonym mapping configuration from the configured JSON file."""
        try:
            if not self.synonyms_path.exists():
                logger.warning(
                    "Synonyms file not found, using empty mappings",
                    extra={"synonyms_path": str(self.synonyms_path)}
                )
                return {}
            
            with open(self.synonyms_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                logger.error(
                    "Invalid synonyms config format, expected a dictionary",
                    extra={"synonyms_path": str(self.synonyms_path)}
                )
                return {}
            
            cleaned_map: Dict[str, str] = {}
            for k, v in data.items():
                if isinstance(k, str) and isinstance(v, str):
                    cleaned_map[self.clean_text(k)] = self.clean_text(v)
            
            logger.info(
                "Synonym mapping configuration loaded successfully",
                extra={"synonyms_path": str(self.synonyms_path), "mapping_count": len(cleaned_map)}
            )
            return cleaned_map
        except Exception as e:
            logger.error(
                "Failed to load synonyms configuration",
                extra={"synonyms_path": str(self.synonyms_path), "error": str(e)}
            )
            return {}

    def clean_text(self, text: str) -> str:
        """Normalizes whitespace, replaces dashes/hyphens with spaces, and downcases text."""
        if not text:
            return ""
        processed = text.replace("-", " ")
        cleaned = re.sub(r"\s+", " ", processed)
        return cleaned.strip().lower()

    def normalize_skill(self, skill: str) -> str:
        """Normalizes a skill name by cleaning and applying the synonym mapping."""
        cleaned = self.clean_text(skill)
        mapped = self.synonym_map.get(cleaned, cleaned)
        return self.clean_text(mapped)

    def analyze(self, candidate: CandidateIntelligence, jd: JobDescription) -> SkillAnalysis:
        """Analyzes skill alignment between candidate intelligence and job description.

        Args:
            candidate: Parsed candidate intelligence model.
            jd: Parsed job description model.

        Returns:
            SkillAnalysis containing exact/synonym matches, missing, and additional skills.
        """
        logger.info("SKILL ANALYSIS START")
        logger.info(
            "Starting skill intelligence analysis",
            extra={
                "candidate_id": candidate.candidate_id,
                "jd_title": jd.title,
                "candidate_skill_count": len(candidate.skills),
                "jd_required_count": len(jd.requirements),
                "jd_preferred_count": len(jd.preferred_skills),
            }
        )

        # 1. Gather raw candidate skills (Candidate has skills: List[SkillSchema] where each has name)
        raw_candidate_skills = [s.name for s in candidate.skills]
        raw_candidate_certs = [c.name for c in candidate.certifications] if candidate.certifications else []
        raw_required = jd.requirements
        raw_preferred = jd.preferred_skills

        # 2. Map canonical names to raw skills to find matches and preserve determinism
        candidate_norm_to_raw_skills: Dict[str, Set[str]] = {}
        for skill in raw_candidate_skills:
            norm = self.normalize_skill(skill)
            if norm:
                candidate_norm_to_raw_skills.setdefault(norm, set()).add(skill)

        candidate_norm_to_raw_certs: Dict[str, Set[str]] = {}
        for cert in raw_candidate_certs:
            norm = self.clean_text(cert)  # Keep cert norm separate from general synonyms
            if norm:
                candidate_norm_to_raw_certs.setdefault(norm, set()).add(cert)

        required_norm_to_raw: Dict[str, Set[str]] = {}
        for skill in raw_required:
            norm = self.normalize_skill(skill)
            if norm:
                required_norm_to_raw.setdefault(norm, set()).add(skill)

        preferred_norm_to_raw: Dict[str, Set[str]] = {}
        for skill in raw_preferred:
            norm = self.normalize_skill(skill)
            if norm:
                preferred_norm_to_raw.setdefault(norm, set()).add(skill)

        normalized_candidate = sorted(list(candidate_norm_to_raw_skills.keys()) + list(candidate_norm_to_raw_certs.keys()))
        normalized_required = sorted(list(required_norm_to_raw.keys()))
        normalized_preferred = sorted(list(preferred_norm_to_raw.keys()))

        # Determine matches:
        exact_matches: Set[str] = set()
        synonym_matches: Set[str] = set()

        from backend.app.ranking.ranking_engine import SkillMatchEvaluator
        
        def is_text_match(skill: str, requirement: str, is_cert_req: bool) -> bool:
            if is_cert_req:
                req_can = SkillMatchEvaluator.CERTIFICATION_ALIAS_MAP.get(requirement, requirement)
                skill_can = SkillMatchEvaluator.CERTIFICATION_ALIAS_MAP.get(skill, skill)
                for canon, aliases in SkillMatchEvaluator.CERTIFICATION_ALIAS_MAP.items():
                    if requirement == canon or requirement in aliases:
                        req_can = canon
                    if skill == canon or skill in aliases:
                        skill_can = canon
                return req_can == skill_can
                
            if not skill:
                return False
            if " " in skill:
                return skill in requirement
            pattern = ""
            if skill[0].isalnum():
                pattern += r"\b"
            pattern += re.escape(skill)
            if skill[-1].isalnum():
                pattern += r"\b"
            return bool(re.search(pattern, requirement))

        # Check matches against required and preferred skills
        for norm_r in required_norm_to_raw:
            is_cert = bool(SkillMatchEvaluator.CERT_SIGNAL_RE.search(norm_r))
            if is_cert:
                for norm_c in candidate_norm_to_raw_certs:
                    if is_text_match(norm_c, norm_r, True):
                        exact_matches.add(norm_c)
            else:
                for norm_c in candidate_norm_to_raw_skills:
                    if is_text_match(norm_c, norm_r, False):
                        has_exact = False
                        for raw_c in candidate_norm_to_raw_skills[norm_c]:
                            clean_raw_c = self.clean_text(raw_c)
                            if is_text_match(clean_raw_c, norm_r, False):
                                has_exact = True
                                break
                        if has_exact:
                            exact_matches.add(norm_c)
                        else:
                            synonym_matches.add(norm_c)

        for norm_p in preferred_norm_to_raw:
            is_cert = bool(SkillMatchEvaluator.CERT_SIGNAL_RE.search(norm_p))
            if is_cert:
                for norm_c in candidate_norm_to_raw_certs:
                    if is_text_match(norm_c, norm_p, True):
                        exact_matches.add(norm_c)
            else:
                for norm_c in candidate_norm_to_raw_skills:
                    if is_text_match(norm_c, norm_p, False):
                        has_exact = False
                        for raw_c in candidate_norm_to_raw_skills[norm_c]:
                            clean_raw_c = self.clean_text(raw_c)
                            if is_text_match(clean_raw_c, norm_p, False):
                                has_exact = True
                                break
                        if has_exact:
                            exact_matches.add(norm_c)
                        else:
                            if norm_c not in exact_matches:
                                synonym_matches.add(norm_c)

        # 3. Compute missing and additional skills
        all_matched = exact_matches.union(synonym_matches)

        # Correctly evaluate missing required and preferred skills lines using text patterns
        missing_required = []
        for norm_r in normalized_required:
            is_cert_req = bool(SkillMatchEvaluator.CERT_SIGNAL_RE.search(norm_r))
            matched_any = False
            for match in all_matched:
                if is_text_match(match, norm_r, is_cert_req):
                    matched_any = True
                    break
            if not matched_any:
                missing_required.append(norm_r)
        missing_required = sorted(list(set(missing_required)))

        missing_preferred = []
        for norm_p in normalized_preferred:
            is_cert_req = bool(SkillMatchEvaluator.CERT_SIGNAL_RE.search(norm_p))
            matched_any = False
            for match in all_matched:
                if is_text_match(match, norm_p, is_cert_req):
                    matched_any = True
                    break
            if not matched_any:
                missing_preferred.append(norm_p)
        missing_preferred = sorted(list(set(missing_preferred)))

        all_jd_normalized = set(normalized_required).union(set(normalized_preferred))
        additional_candidate = sorted(list(set(normalized_candidate) - all_jd_normalized))

        analysis = SkillAnalysis(
            normalized_candidate_skills=normalized_candidate,
            normalized_required_skills=normalized_required,
            normalized_preferred_skills=normalized_preferred,
            exact_matches=sorted(list(exact_matches)),
            synonym_matches=sorted(list(synonym_matches)),
            missing_required_skills=missing_required,
            missing_preferred_skills=missing_preferred,
            additional_candidate_skills=additional_candidate
        )

        logger.info("SKILL ANALYSIS END")
        logger.info(
            "Skill intelligence analysis completed",
            extra={
                "candidate_id": candidate.candidate_id,
                "exact_match_count": len(analysis.exact_matches),
                "synonym_match_count": len(analysis.synonym_matches),
                "missing_required_count": len(analysis.missing_required_skills),
                "missing_preferred_count": len(analysis.missing_preferred_skills),
                "additional_skills_count": len(analysis.additional_candidate_skills)
            }
        )

        return analysis
