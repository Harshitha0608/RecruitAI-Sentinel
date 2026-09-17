import logging
from fastapi import APIRouter

from backend.app.retrieval.retrieval_engine import RetrievalEngine
from backend.app.schemas.api_responses import AnalyticsResponse

logger = logging.getLogger("app.api.endpoints.analytics")
router = APIRouter()

@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics() -> AnalyticsResponse:
    import json
    from pathlib import Path
    from backend.app.config.settings import settings
    
    engine = RetrievalEngine()
    
    faiss_loaded = False
    tfidf_loaded = False
    model_loaded = False
    candidate_count = 0
    indexed_candidates = 0
    embedding_dimension = 0
    
    # 1. Inspect candidate count
    try:
        ids_path = Path(settings.CANDIDATE_IDS_PATH)
        if ids_path.exists():
            with open(ids_path, "r", encoding="utf-8") as f:
                cids = json.load(f)
                if isinstance(cids, list):
                    candidate_count = len(cids)
    except Exception as e:
        logger.warning(f"Could not inspect candidate IDs for analytics: {e}", exc_info=True)
        
    # 2. Inspect FAISS status
    try:
        faiss_path = Path(settings.VECTOR_INDEX_PATH)
        if faiss_path.exists():
            faiss_loaded = True
            if engine._faiss_index is not None:
                indexed_candidates = getattr(engine._faiss_index, "ntotal", 0)
                embedding_dimension = getattr(engine._faiss_index, "d", 0)
            else:
                indexed_candidates = candidate_count
                embedding_dimension = 384
    except Exception as e:
        logger.warning(f"Could not inspect FAISS stats for analytics: {e}", exc_info=True)
        
    # 3. Inspect TF-IDF status
    try:
        tfidf_path = Path(settings.TFIDF_PATH)
        if tfidf_path.exists():
            tfidf_loaded = True
    except Exception as e:
        logger.warning(f"Could not inspect TF-IDF stats for analytics: {e}", exc_info=True)
        
    # 4. Inspect Model status
    try:
        if engine._model is not None:
            model_loaded = True
    except Exception as e:
        logger.warning(f"Could not inspect model status for analytics: {e}", exc_info=True)
        
    # Read real run metrics if they exist
    metrics_path = Path(settings.CANDIDATE_IDS_PATH).parent / "run_metrics.json"
    latest_retrieval_latency_ms = None
    latest_pipeline_runtime_ms = None
    latest_honeypot_rate = None
    latest_cohort_size = None
    latest_honeypots_count = None
    
    if metrics_path.exists():
        try:
            with open(metrics_path, "r", encoding="utf-8") as f:
                run_data = json.load(f)
                
                ret_sec = run_data.get("retrieval_time_seconds")
                if ret_sec is not None:
                    latest_retrieval_latency_ms = float(ret_sec * 1000.0)
                    
                tot_sec = run_data.get("total_execution_time_seconds")
                if tot_sec is not None:
                    latest_pipeline_runtime_ms = float(tot_sec * 1000.0)
                    
                honeypots = run_data.get("honeypots_detected_in_cohort")
                if honeypots is not None:
                    latest_honeypots_count = int(honeypots)
                    cohort_sz = run_data.get("cohort_size", 1000)
                    latest_cohort_size = int(cohort_sz)
                    latest_honeypot_rate = float(honeypots / cohort_sz) if cohort_sz > 0 else 0.0
        except Exception as e:
            logger.warning(f"Failed to read run metrics from file: {e}")
            
    top_universities = None
    top_locations = None
    top_missing_skills = None
    work_mode_distribution = None
    education_distribution = None

    results_path = Path(settings.CANDIDATE_IDS_PATH).parent / "ranking_results.json"
    if results_path.exists():
        try:
            with open(results_path, "r", encoding="utf-8") as rf:
                results_data = json.load(rf)
                
            missing_counts = {}
            univ_counts = {}
            loc_counts = {}
            work_mode_counts = {}
            edu_tier_counts = {}

            from backend.app.services.dataset_loader import DatasetLoader
            from backend.app.services.candidate_intelligence_builder import CandidateIntelligenceBuilder

            loader = DatasetLoader()
            builder = CandidateIntelligenceBuilder()

            for cid, record in results_data.items():
                for skill in record.get("missing_skills", []):
                    missing_counts[skill] = missing_counts.get(skill, 0) + 1

                raw = loader.load_candidate_by_id(cid)
                if raw:
                    intel = builder.build_intelligence(raw)
                    if intel.location:
                        loc = intel.location.trim() if hasattr(intel.location, 'trim') else intel.location.strip()
                        if loc and loc.lower() not in ["unknown", "not specified"]:
                            loc_counts[loc] = loc_counts.get(loc, 0) + 1
                    
                    if intel.education:
                        for edu in intel.education:
                            inst = edu.institution.strip() if edu.institution else ""
                            if inst and inst.lower() not in ["unknown", "not specified"]:
                                univ_counts[inst] = univ_counts.get(inst, 0) + 1
                            if edu.tier is not None:
                                tier_label = f"Tier {edu.tier}"
                                edu_tier_counts[tier_label] = edu_tier_counts.get(tier_label, 0) + 1

                    if intel.behavioral_signals and intel.behavioral_signals.preferred_work_mode:
                        mode = intel.behavioral_signals.preferred_work_mode.strip()
                        if mode and mode.lower() not in ["unknown", "not specified"]:
                            pretty_mode = mode.capitalize()
                            work_mode_counts[pretty_mode] = work_mode_counts.get(pretty_mode, 0) + 1

            top_missing_skills = [
                {"name": name, "count": count}
                for name, count in sorted(missing_counts.items(), key=lambda x: -x[1])[:5]
            ]
            top_universities = [
                {"name": name, "count": count}
                for name, count in sorted(univ_counts.items(), key=lambda x: -x[1])[:5]
            ]
            top_locations = [
                {"name": name, "count": count}
                for name, count in sorted(loc_counts.items(), key=lambda x: -x[1])[:5]
            ]
            work_mode_distribution = [
                {"range": range_name, "count": count}
                for range_name, count in work_mode_counts.items()
            ]
            education_distribution = [
                {"range": range_name, "count": count}
                for range_name, count in edu_tier_counts.items()
            ]
        except Exception as e:
            logger.warning(f"Failed to calculate analytics demographic aggregations: {e}", exc_info=True)

    return AnalyticsResponse(
        candidate_count=candidate_count,
        indexed_candidates=indexed_candidates,
        embedding_dimension=embedding_dimension,
        faiss_loaded=faiss_loaded,
        tfidf_loaded=tfidf_loaded,
        model_loaded=model_loaded,
        latest_retrieval_latency_ms=latest_retrieval_latency_ms,
        latest_pipeline_runtime_ms=latest_pipeline_runtime_ms,
        latest_honeypot_rate=latest_honeypot_rate,
        sqlite_connected=False,
        latest_cohort_size=latest_cohort_size,
        latest_honeypots_count=latest_honeypots_count,
        top_universities=top_universities,
        top_locations=top_locations,
        top_missing_skills=top_missing_skills,
        work_mode_distribution=work_mode_distribution,
        education_distribution=education_distribution
    )
