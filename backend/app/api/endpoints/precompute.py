import sys
import subprocess
import logging
import json
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, status
from backend.app.schemas.api_responses import PrecomputeResponse, PrecomputeStatusResponse
from backend.app.config.settings import settings

logger = logging.getLogger("app.api.endpoints.precompute")
router = APIRouter()

def write_status(status_str: str, progress: int, message: str) -> None:
    status_path = Path(settings.CANDIDATE_IDS_PATH).parent / "precompute_status.json"
    try:
        status_path.parent.mkdir(parents=True, exist_ok=True)
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": status_str, "progress": progress, "message": message}, f)
    except Exception as e:
        logger.warning(f"Failed to write precompute status: {e}")

def run_precompute_script() -> None:
    try:
        script_path = Path(__file__).resolve().parents[4] / "scripts" / "precompute.py"
        logger.info(f"Starting precomputation subprocess for: {script_path}")
        write_status("processing", 5, "Starting precomputation script...")
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Precomputation subprocess completed. Output: {result.stdout.strip()}")
        write_status("success", 100, "Precomputation completed successfully.")
    except subprocess.CalledProcessError as cpe:
        logger.error(f"Precomputation subprocess failed with code {cpe.returncode}. Error: {cpe.stderr.strip()}", exc_info=True)
        write_status("failed", 0, f"Failed with code {cpe.returncode}: {cpe.stderr.strip()[:150]}")
    except Exception as e:
        logger.error(f"Failed to run precomputation subprocess: {e}", exc_info=True)
        write_status("failed", 0, f"Failed to launch script: {str(e)[:150]}")

@router.post("/precompute", response_model=PrecomputeResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_precompute(background_tasks: BackgroundTasks) -> PrecomputeResponse:
    write_status("processing", 0, "Triggered background precomputation task...")
    background_tasks.add_task(run_precompute_script)
    return PrecomputeResponse(
        status="processing",
        message="Precomputation task has been successfully triggered in the background."
    )

@router.get("/precompute/status", response_model=PrecomputeStatusResponse)
async def get_precompute_status() -> PrecomputeStatusResponse:
    status_path = Path(settings.CANDIDATE_IDS_PATH).parent / "precompute_status.json"
    if not status_path.exists():
        return PrecomputeStatusResponse(
            status="idle",
            progress=0,
            message="System indices are idle. No indexing runs have been executed."
        )
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return PrecomputeStatusResponse(
                status=data.get("status", "unknown"),
                progress=data.get("progress", 0),
                message=data.get("message", "")
            )
    except Exception as e:
        logger.error(f"Failed to read precompute status file: {e}")
        return PrecomputeStatusResponse(
            status="error",
            progress=0,
            message=f"Failed to parse status: {str(e)}"
        )
