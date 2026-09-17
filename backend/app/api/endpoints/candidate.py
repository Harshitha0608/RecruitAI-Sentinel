import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, status

from backend.app.config.settings import settings
from backend.app.services.dataset_loader import DatasetLoader
from backend.app.services.candidate_intelligence_builder import CandidateIntelligenceBuilder
from backend.app.services.jd_parser import JDParser
from backend.app.ranking.ranking_engine import RankingEngine
from backend.app.explainability.explainability_engine import ExplainabilityEngine
from backend.app.schemas.api_responses import CandidateDetailResponse, ScoreBreakdown

logger = logging.getLogger("app.api.endpoints.candidate")
router = APIRouter()

@router.get("/candidate/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate_detail(candidate_id: str) -> CandidateDetailResponse:
    try:
        loader = DatasetLoader()
        
        target_candidate = loader.load_candidate_by_id(candidate_id)
                
        if not target_candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID {candidate_id} not found in the dataset."
            )
            
        builder = CandidateIntelligenceBuilder()
        candidate = builder.build_intelligence(target_candidate)
        
        # Check for persistent ranking_results.json artifact first
        results_file = Path(settings.CANDIDATE_IDS_PATH).parent / "ranking_results.json"
        saved_record = None
        if results_file.exists():
            try:
                import json
                with open(results_file, "r", encoding="utf-8") as rf:
                    results_data = json.load(rf)
                    saved_record = results_data.get(candidate_id)
            except Exception as e:
                logger.warning(f"Could not read ranking_results.json: {e}")

        critical_matched = None
        important_matched = None
        nice_to_have_matched = None
        missing_critical = None
        matched_skills = None
        missing_skills = None

        if saved_record and "score_breakdown" in saved_record:
            logger.info(f"Loaded candidate {candidate_id} evaluation from persistent ranking_results.json artifact.")
            sb = saved_record["score_breakdown"]
            breakdown = ScoreBreakdown(
                skill_score=sb.get("skill_score", 0.0),
                experience_score=sb.get("experience_score", 0.0),
                education_score=sb.get("education_score", 0.0),
                project_score=sb.get("project_score", 0.0),
                behavior_score=sb.get("behavior_score", 0.0),
                availability_score=sb.get("availability_score", 0.0),
                engagement_bonus=sb.get("engagement_bonus", 0.0),
                final_score=saved_record.get("final_score", sb.get("final_score", 0.0))
            )
            is_honeypot = saved_record.get("is_honeypot", False)
            reasoning = saved_record.get("reasoning", "Candidate evaluation complete.")
            critical_matched = saved_record.get("critical_skills_matched", [])
            important_matched = saved_record.get("important_skills_matched", [])
            nice_to_have_matched = saved_record.get("nice_to_have_skills_matched", [])
            missing_critical = saved_record.get("missing_critical_skills", [])
            
            matched_skills = saved_record.get("matched_skills", [])
            missing_skills = saved_record.get("missing_skills", [])
        else:
            jd_path = settings.JOB_DESCRIPTION_PATH
            jd = None
            if jd_path and Path(jd_path).exists():
                try:
                    parser = JDParser()
                    jd = parser.parse()
                except Exception as e:
                    logger.warning(f"Could not automatically load and parse JD: {e}")
                    
            if jd:
                ranker = RankingEngine()
                evaluation = ranker.evaluate_candidate(candidate, jd)
                
                explainability = ExplainabilityEngine()
                reasoning = explainability.generate_explanation(candidate, evaluation, jd)
                
                breakdown = ScoreBreakdown(
                    skill_score=evaluation["skill_score"],
                    experience_score=evaluation["experience_score"],
                    education_score=evaluation["education_score"],
                    project_score=evaluation["project_score"],
                    behavior_score=evaluation["behavior_score"],
                    availability_score=evaluation["availability_score"],
                    engagement_bonus=evaluation.get("engagement_bonus", 0.0),
                    final_score=evaluation["final_score"]
                )
                is_honeypot = evaluation["is_honeypot"]
                sb_dict = evaluation.get("scoring_breakdown", {})
                critical_matched = sb_dict.get("critical_skills_matched", [])
                important_matched = sb_dict.get("important_skills_matched", [])
                nice_to_have_matched = sb_dict.get("nice_to_have_skills_matched", [])
                missing_critical = sb_dict.get("missing_critical_skills", [])
                
                c_matched = sb_dict.get("critical_skills_matched", [])
                i_matched = sb_dict.get("important_skills_matched", [])
                n_matched = sb_dict.get("nice_to_have_skills_matched", [])
                matched_skills = list(dict.fromkeys(c_matched + i_matched + n_matched))
                missing_skills = sb_dict.get("missing_critical_skills", [])
            else:
                breakdown = ScoreBreakdown(
                    skill_score=0.0,
                    experience_score=0.0,
                    education_score=0.0,
                    project_score=0.0,
                    behavior_score=0.0,
                    availability_score=0.0,
                    engagement_bonus=0.0,
                    final_score=0.0
                )
                is_honeypot = False
                reasoning = "Job description is not configured or could not be loaded."

            
        return CandidateDetailResponse(
            candidate_id=candidate.candidate_id,
            name=candidate.name,
            headline=candidate.headline,
            summary=candidate.summary,
            current_title=candidate.current_title,
            current_company=candidate.current_company,
            years_of_experience=candidate.years_of_experience,
            location=candidate.location,
            is_honeypot=is_honeypot,
            score_breakdown=breakdown,
            reasoning=reasoning,
            skills=candidate.skills,
            career_history=candidate.career_history,
            education=candidate.education,
            behavioral_signals=candidate.behavioral_signals,
            critical_skills_matched=critical_matched,
            important_skills_matched=important_matched,
            nice_to_have_skills_matched=nice_to_have_matched,
            missing_critical_skills=missing_critical,
            matched_skills=matched_skills,
            missing_skills=missing_skills
        )
    except HTTPException as he:
        raise he
    except FileNotFoundError as fnfe:
        logger.error(f"Required file not found during candidate details retrieval: {fnfe}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Candidate details file is missing: {str(fnfe)}"
        )
    except Exception as e:
        logger.error(f"Unexpected exception during candidate details retrieval: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
