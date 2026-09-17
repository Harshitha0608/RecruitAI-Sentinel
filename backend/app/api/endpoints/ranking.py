import asyncio
import shutil
import tempfile
import csv
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
import threading

_screening_in_progress = False
_screening_in_progress_lock = threading.Lock()

from backend.app.config.settings import settings, BASE_DIR
from backend.app.services.ranking_pipeline import RankingPipeline
from backend.app.schemas.api_responses import RankResponse, RankResponseItem

logger = logging.getLogger("app.api.endpoints.ranking")
router = APIRouter()

from backend.app.services.dataset_loader import DatasetLoader
from backend.app.services.candidate_intelligence_builder import CandidateIntelligenceBuilder

from backend.app.ranking.ranking_engine import RankingEngine

def populate_candidate_analytics(items: List[RankResponseItem]) -> List[RankResponseItem]:
    loader = DatasetLoader()
    builder = CandidateIntelligenceBuilder()
    ranker = RankingEngine()
    
    # Load active JD for score evaluation
    jd_path = settings.JOB_DESCRIPTION_PATH
    jd = None
    if jd_path and Path(jd_path).exists():
        try:
            from backend.app.services.jd_parser import JDParser
            parser = JDParser(str(jd_path))
            jd = parser.parse()
        except Exception as e:
            logger.warning(f"Could not load active JD in populate_candidate_analytics: {e}")

    # Load persistent ranking_results.json artifact if present
    results_file = Path(settings.CANDIDATE_IDS_PATH).parent / "ranking_results.json"
    ranking_data = {}
    if results_file.exists():
        try:
            import json
            with open(results_file, "r", encoding="utf-8") as rf:
                ranking_data = json.load(rf)
        except Exception:
            pass

    logger.info("Starting populate_candidate_analytics...")
    for idx, item in enumerate(items):
        try:
            saved = ranking_data.get(item.candidate_id)
            
            # Fast-path check: if ranking_results.json contains display metadata, populate directly
            if saved and "name" in saved and "years_of_experience" in saved and "score_breakdown" in saved:
                item.name = saved.get("name")
                item.years_of_experience = saved.get("years_of_experience", 0.0)
                item.location = saved.get("location", "")
                item.is_honeypot = saved.get("is_honeypot", False)
                item.open_to_work = saved.get("open_to_work", False)
                item.notice_period_days = saved.get("notice_period_days", 0)
                item.skills = saved.get("skills", [])
                item.current_title = saved.get("current_title", "")
                item.current_company = saved.get("current_company", "")
                item.critical_skills_matched = saved.get("critical_skills_matched", [])
                item.important_skills_matched = saved.get("important_skills_matched", [])
                item.nice_to_have_skills_matched = saved.get("nice_to_have_skills_matched", [])
                item.missing_critical_skills = saved.get("missing_critical_skills", [])
                
                item.matched_skills = saved.get("matched_skills", [])
                item.missing_skills = saved.get("missing_skills", [])

                if "score_breakdown" in saved:
                    from backend.app.schemas.api_responses import ScoreBreakdown
                    sb = saved["score_breakdown"]
                    item.score_breakdown = ScoreBreakdown(
                        skill_score=sb.get("skill_score", 0.0),
                        experience_score=sb.get("experience_score", 0.0),
                        education_score=sb.get("education_score", 0.0),
                        project_score=sb.get("project_score", 0.0),
                        behavior_score=sb.get("behavior_score", 0.0),
                        availability_score=sb.get("availability_score", 0.0),
                        engagement_bonus=sb.get("engagement_bonus", 0.0),
                        final_score=saved.get("final_score", sb.get("final_score", 0.0))
                    )
                if idx < 2:
                    logger.info(f"Fast-path populated {item.candidate_id}: name={item.name}, exp={item.years_of_experience}, loc={item.location}")
                continue  # Fast path complete! Skip disk seeks, build_intelligence, and evaluation.

            if saved:
                item.critical_skills_matched = saved.get("critical_skills_matched", [])
                item.important_skills_matched = saved.get("important_skills_matched", [])
                item.nice_to_have_skills_matched = saved.get("nice_to_have_skills_matched", [])
                item.missing_critical_skills = saved.get("missing_critical_skills", [])
                
                item.matched_skills = saved.get("matched_skills", [])
                item.missing_skills = saved.get("missing_skills", [])

            raw = loader.load_candidate_by_id(item.candidate_id)
            if raw:
                intel = builder.build_intelligence(raw)
                item.name = intel.name
                item.years_of_experience = intel.years_of_experience
                item.location = intel.location
                item.is_honeypot = ranker.is_honeypot(intel)
                item.open_to_work = intel.behavioral_signals.open_to_work_flag if intel.behavioral_signals else False
                item.notice_period_days = intel.notice_period
                item.skills = [s.name for s in intel.skills] if intel.skills else []
                item.current_title = intel.current_title
                item.current_company = intel.current_company
                
                if saved and "score_breakdown" in saved:
                    from backend.app.schemas.api_responses import ScoreBreakdown
                    sb = saved["score_breakdown"]
                    item.score_breakdown = ScoreBreakdown(
                        skill_score=sb.get("skill_score", 0.0),
                        experience_score=sb.get("experience_score", 0.0),
                        education_score=sb.get("education_score", 0.0),
                        project_score=sb.get("project_score", 0.0),
                        behavior_score=sb.get("behavior_score", 0.0),
                        availability_score=sb.get("availability_score", 0.0),
                        engagement_bonus=sb.get("engagement_bonus", 0.0),
                        final_score=saved.get("final_score", sb.get("final_score", 0.0))
                    )
                elif jd:
                    evaluation = ranker.evaluate_candidate(intel, jd)
                    from backend.app.schemas.api_responses import ScoreBreakdown
                    item.score_breakdown = ScoreBreakdown(
                        skill_score=evaluation["skill_score"],
                        experience_score=evaluation["experience_score"],
                        education_score=evaluation["education_score"],
                        project_score=evaluation["project_score"],
                        behavior_score=evaluation["behavior_score"],
                        availability_score=evaluation["availability_score"],
                        engagement_bonus=evaluation.get("engagement_bonus", 0.0),
                        final_score=evaluation["final_score"]
                    )
                
                if idx < 2:
                    logger.info(f"Fallback populated {item.candidate_id}: name={item.name}, exp={item.years_of_experience}, loc={item.location}")
            else:
                logger.warning(f"Could not find raw candidate {item.candidate_id} in loader")
        except Exception as e:
            logger.warning(f"Failed to populate analytics for candidate {item.candidate_id}: {e}", exc_info=True)
    return items

import hashlib
import json

def get_jd_and_dataset_meta(jd_path: Path) -> dict:
    jd_hash = ""
    if jd_path.exists():
        try:
            with open(jd_path, "rb") as f:
                jd_hash = hashlib.md5(f.read()).hexdigest()
        except Exception:
            pass
            
    dataset_path = Path(settings.CANDIDATE_DATASET_PATH)
    dataset_mtime = 0.0
    dataset_size = 0
    if dataset_path.exists():
        dataset_mtime = dataset_path.stat().st_mtime
        dataset_size = dataset_path.stat().st_size
        
    return {
        "jd_hash": jd_hash,
        "dataset_mtime": dataset_mtime,
        "dataset_size": dataset_size,
        "pipeline_version": getattr(settings, "PIPELINE_VERSION", "1.0.0")
    }

@router.post("/rank", response_model=RankResponse)
async def run_rank(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
) -> RankResponse:
    global _screening_in_progress
    with _screening_in_progress_lock:
        if _screening_in_progress:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Candidate screening is already in progress. Please wait for the current run to complete."
            )
        _screening_in_progress = True

    try:
        # Reset progress lifecycle (Fix 5)
        try:
            import json
            progress_path = Path(settings.CANDIDATE_IDS_PATH).parent / "screening_progress.json"
            with open(progress_path, "w", encoding="utf-8") as f:
                json.dump({
                    "stage": "Preparing Job",
                    "percentage": 0,
                    "status_message": "Initializing screening process...",
                    "completed": False
                }, f)
        except Exception as e:
            logger.warning(f"Failed to reset screening progress: {e}")

        logger.info("REQUEST RECEIVED")
        logger.info(f"run_rank endpoint called. text length: {len(text) if text else 0}")
        if text:
            logger.info(f"First 100 chars of text: {text[:100]}")
        persistent_dir = BASE_DIR / "backend" / "app"
        persistent_dir.mkdir(parents=True, exist_ok=True)
        
        if not file and not text:
            active_path = None
            for ext in [".docx", ".txt", ".md"]:
                p = persistent_dir / f"active_job_description{ext}"
                if p.exists():
                    active_path = p
                    break
            if not active_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Either a job description file (.docx, .txt, .md) or raw text must be provided."
                )
            persistent_path = active_path
        else:
            suffix = ".txt"
            if file and file.filename:
                suffix = Path(file.filename).suffix
                if suffix.lower() not in [".docx", ".txt", ".md"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Unsupported file format. Please upload a .docx, .txt, or .md file."
                    )
            
            for ext in [".docx", ".txt", ".md"]:
                old_path = persistent_dir / f"active_job_description{ext}"
                if old_path.exists():
                    try:
                        old_path.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to remove old active JD file {old_path}: {e}")
                        
            persistent_path = persistent_dir / f"active_job_description{suffix}"
            
            try:
                if file:
                    with open(persistent_path, "wb") as f:
                        shutil.copyfileobj(file.file, f)
                    try:
                        file.file.close()
                    except Exception:
                        pass
                elif text:
                    with open(persistent_path, "wb") as f:
                        f.write(text.encode("utf-8"))
            except Exception as e:
                logger.error(f"Failed to save active job description to disk: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to save job description on server: {str(e)}"
                )
            
        settings.JOB_DESCRIPTION_PATH = str(persistent_path)
        
        out_csv = Path("submission.csv")
        current_meta = get_jd_and_dataset_meta(persistent_path)
        cache_meta_path = Path(settings.CANDIDATE_IDS_PATH).parent / "ranking_cache_meta.json"
        
        # Cache check (FIX 11)
        use_cache = False
        results_file = Path(settings.CANDIDATE_IDS_PATH).parent / "ranking_results.json"
        if out_csv.exists() and cache_meta_path.exists() and results_file.exists():
            try:
                with open(cache_meta_path, "r", encoding="utf-8") as f:
                    cached_meta = json.load(f)
                    if (cached_meta.get("jd_hash") == current_meta["jd_hash"] and
                        cached_meta.get("dataset_mtime") == current_meta["dataset_mtime"] and
                        cached_meta.get("dataset_size") == current_meta["dataset_size"] and
                        cached_meta.get("pipeline_version") == current_meta["pipeline_version"]):
                        with open(results_file, "r", encoding="utf-8") as rf:
                            rf_data = json.load(rf)
                            if len(rf_data) >= 100:
                                use_cache = True
            except Exception:
                pass
                
        if use_cache:
            logger.info("Serving identical active JD ranking run from cache.")
            try:
                candidates = []
                with open(out_csv, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    next(reader)
                    for row in reader:
                        if len(row) >= 4:
                            item = RankResponseItem(
                                candidate_id=row[0],
                                rank=int(row[1]),
                                score=float(row[2]),
                                reasoning=row[3]
                            )
                            candidates.append(item)
                candidates_populated = populate_candidate_analytics(candidates)
                # Write progress complete for cache hit
                try:
                    progress_path = Path(settings.CANDIDATE_IDS_PATH).parent / "screening_progress.json"
                    with open(progress_path, "w", encoding="utf-8") as f:
                        json.dump({"stage": "Completed", "percentage": 100, "status_message": "Screening complete (loaded from cache).", "completed": True}, f)
                except Exception:
                    pass
                return RankResponse(success=True, candidates=candidates_populated)
            except Exception as ce:
                logger.warning(f"Failed to read cached submission.csv, running pipeline: {ce}")
                
        try:
            # Initial status
            try:
                progress_path = Path(settings.CANDIDATE_IDS_PATH).parent / "screening_progress.json"
                with open(progress_path, "w", encoding="utf-8") as f:
                    json.dump({"stage": "Uploading JD", "percentage": 10, "status_message": "Job description uploaded successfully."}, f)
            except Exception:
                pass

            pipeline = RankingPipeline()
            res = await asyncio.to_thread(pipeline.run, str(persistent_path), str(out_csv))
            
            if not res["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Ranking pipeline execution failed. Errors: {res['validation_errors']}"
                )
                
            candidates = []
            with open(out_csv, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)
                for row in reader:
                    if len(row) >= 4:
                        candidates.append(
                            RankResponseItem(
                                candidate_id=row[0],
                                rank=int(row[1]),
                                score=float(row[2]),
                                reasoning=row[3]
                            )
                        )
                        
            # Cache metadata on success (FIX 11)
            try:
                with open(cache_meta_path, "w", encoding="utf-8") as f:
                    json.dump(current_meta, f)
            except Exception as ce:
                logger.warning(f"Failed to save ranking cache metadata: {ce}")
                
            candidates_populated = populate_candidate_analytics(candidates)
            logger.info("RESPONSE SENT")
            return RankResponse(success=True, candidates=candidates_populated)
        except Exception as e:
            logger.error(f"Error during ranking pipeline execution: {e}")
            try:
                import json
                progress_path = Path(settings.CANDIDATE_IDS_PATH).parent / "screening_progress.json"
                with open(progress_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "stage": "error",
                        "percentage": 100,
                        "status_message": f"Screening run failed: {str(e)}",
                        "completed": True
                    }, f)
            except Exception:
                pass
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error executing ranking pipeline: {str(e)}"
            )
    finally:
        with _screening_in_progress_lock:
            _screening_in_progress = False


@router.get("/top100", response_model=RankResponse)
def get_top100() -> RankResponse:
    out_csv = Path("submission.csv")
    if not out_csv.exists():
        return RankResponse(success=False, candidates=[])
    try:
        candidates = []
        with open(out_csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) >= 4:
                    candidates.append(
                        RankResponseItem(
                            candidate_id=row[0],
                            rank=int(row[1]),
                            score=float(row[2]),
                            reasoning=row[3]
                        )
                    )
        candidates_populated = populate_candidate_analytics(candidates)
        return RankResponse(success=True, candidates=candidates_populated)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load latest top 100 ranking results: {str(e)}"
        )

@router.get("/screening-progress")
async def get_screening_progress() -> dict:
    """Returns the current screening execution progress (FIX 9)."""
    progress_path = Path(settings.CANDIDATE_IDS_PATH).parent / "screening_progress.json"
    if not progress_path.exists():
        return {
            "stage": "idle",
            "percentage": 0,
            "status_message": "No active candidate screening is running."
        }
    try:
        with open(progress_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read screening_progress.json: {e}")
        return {
            "stage": "error",
            "percentage": 0,
            "status_message": f"Failed to read progress: {str(e)}"
        }



from backend.app.schemas.job_description import JobDescription
from backend.app.services.jd_parser import JDParser

@router.get("/active-jd", response_model=Optional[JobDescription])
def get_active_jd() -> Optional[JobDescription]:
    """Returns the parsed active job description detail parsed from the server."""
    persistent_dir = BASE_DIR / "backend" / "app"
    active_file = None
    for ext in [".docx", ".txt", ".md"]:
        p = persistent_dir / f"active_job_description{ext}"
        if p.exists():
            active_file = p
            break
            
    if not active_file:
        # Fallback to check setting path
        if settings.JOB_DESCRIPTION_PATH and Path(settings.JOB_DESCRIPTION_PATH).exists():
            active_file = Path(settings.JOB_DESCRIPTION_PATH)
            
    if not active_file:
        return None
        
    try:
        parser = JDParser(str(active_file))
        return parser.parse()
    except Exception as e:
        logger.error(f"Failed to parse active Job Description: {e}")
        return None


@router.post("/parse-jd", response_model=JobDescription)
def parse_job_description(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
) -> JobDescription:
    if not file and not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a job description file (.docx, .txt, .md) or raw text must be provided."
        )
        
    suffix = ".txt"
    if file and file.filename:
        suffix = Path(file.filename).suffix
        if suffix.lower() not in [".docx", ".txt", ".md"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format. Please upload a .docx, .txt, or .md file."
            )
            
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_path = Path(temp_file.name)
    try:
        temp_file.close()
    except Exception:
        pass

    try:
        if file:
            with open(temp_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            try:
                file.file.close()
            except Exception:
                pass
        elif text:
            with open(temp_path, "wb") as f:
                f.write(text.encode("utf-8"))
                
        parser = JDParser(str(temp_path))
        return parser.parse()
    except Exception as e:
        logger.error(f"Failed to parse Job Description: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse job description: {str(e)}"
        )
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to clean up temp JD file {temp_path}: {e}")


@router.post("/upload-dataset")
def upload_dataset(file: UploadFile = File(...)) -> dict:
    """Saves uploaded candidates.jsonl dataset file to server after validation."""
    import json
    from datetime import datetime
    
    try:
        suffix = Path(file.filename or "").suffix
        if suffix.lower() not in [".jsonl", ".json"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported dataset format. Please upload a .jsonl or .json file."
            )

        target_str = settings.CANDIDATE_DATASET_PATH
        if not target_str:
            target_str = str(BASE_DIR / "backend" / "app" / "candidates.jsonl")
            
        target_path = Path(target_str)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to temporary path for validation first
        temp_path = target_path.with_suffix(".tmp")
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        # Count rows and validate the first 5 records
        count = 0
        validated = 0
        try:
            with open(temp_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    count += 1
                    if count <= 5:
                        try:
                            item = json.loads(line_str)
                            if "candidate_id" in item and "profile" in item:
                                validated += 1
                        except Exception:
                            pass
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read file lines: {str(e)}"
            )
            
        # If no rows or first rows are completely invalid
        if count == 0 or (count > 0 and validated == 0):
            if temp_path.exists():
                temp_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid candidate schema. The file must contain valid JSONL candidate rows with 'candidate_id' and 'profile'."
            )
            
        # Move temporary file to final path
        if target_path.exists():
            target_path.unlink()
        shutil.move(str(temp_path), str(target_path))
        
        # Dynamically update settings
        settings.CANDIDATE_DATASET_PATH = str(target_path)
        
        # Write metadata status file
        status_path = Path(settings.CANDIDATE_IDS_PATH).parent / "dataset_status.json"
        status_data = {
            "status": "loaded",
            "candidate_count": count,
            "last_updated": datetime.now().isoformat(),
            "filename": file.filename or "candidates.jsonl"
        }
        with open(status_path, "w", encoding="utf-8") as sf:
            json.dump(status_data, sf, indent=2)
            
        return status_data
        
    except Exception as e:
        logger.error(f"Failed to upload candidate dataset: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload dataset: {str(e)}"
        )

@router.get("/dataset-status")
async def get_dataset_status() -> dict:
    """Returns the current loaded dataset metadata status."""
    import json
    status_path = Path(settings.CANDIDATE_IDS_PATH).parent / "dataset_status.json"
    if not status_path.exists():
        # Fallback to check default candidate count if dataset exists
        dataset_path = settings.CANDIDATE_DATASET_PATH
        if dataset_path and Path(dataset_path).exists():
            try:
                # Count lines without reloading
                count = 0
                with open(dataset_path, "rb") as f:
                    for _ in f:
                        count += 1
                return {
                    "status": "loaded",
                    "candidate_count": count,
                    "last_updated": "System Default",
                    "filename": Path(dataset_path).name
                }
            except Exception:
                pass
        return {
            "status": "idle",
            "candidate_count": 0,
            "last_updated": None,
            "filename": None
        }
        
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read dataset_status.json: {e}")
        return {
            "status": "error",
            "candidate_count": 0,
            "last_updated": None,
            "filename": None
        }

