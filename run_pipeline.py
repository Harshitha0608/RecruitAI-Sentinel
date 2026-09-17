import os
# Configure environment variables at the absolute entrypoint
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
import sys
import time
import logging
from pathlib import Path

# Adjust python path to import app modules correctly
sys.path.append(str(Path(__file__).resolve().parent))

from backend.app.config.settings import settings
from backend.app.services.ranking_pipeline import RankingPipeline

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger("run_pipeline")

def get_memory_usage_mb() -> float:
    """Returns the current process memory usage in Megabytes."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0

def main():
    logger.info("Starting AI Ranking Pipeline runner...")
    
    # Verify precomputed index files exist
    faiss_path = Path(settings.VECTOR_INDEX_PATH)
    ids_path = Path(settings.CANDIDATE_IDS_PATH)
    tfidf_path = Path(settings.TFIDF_PATH)
    
    if not faiss_path.exists() or not ids_path.exists() or not tfidf_path.exists():
        logger.error(
            "Precomputed index files not found. Please run the precompute script first.",
            extra={
                "faiss_exists": faiss_path.exists(),
                "ids_exists": ids_path.exists(),
                "tfidf_exists": tfidf_path.exists()
            }
        )
        sys.exit(1)
        
    jd_path = settings.JOB_DESCRIPTION_PATH
    if not jd_path or not Path(jd_path).exists():
        logger.error(f"Job Description file not found at: {jd_path}")
        sys.exit(1)
        
    output_csv = "submission.csv"
    
    start_memory = get_memory_usage_mb()
    start_time = time.time()
    
    # Initialize and execute pipeline
    pipeline = RankingPipeline()
    res = pipeline.run(jd_path, output_csv)
    
    end_time = time.time()
    end_memory = get_memory_usage_mb()
    peak_memory = max(start_memory, end_memory) # basic approximation
    
    elapsed = end_time - start_time
    logger.info(f"Pipeline completed in {elapsed:.2f} seconds.")
    logger.info(f"Memory stats - Start: {start_memory:.2f} MB, End: {end_memory:.2f} MB, Peak approx: {peak_memory:.2f} MB")
    
    print("\n--- Pipeline Execution Summary ---")
    print(f"Status: {'Success' if res['success'] else 'Validation Failed'}")
    print(f"Total Execution Time: {res['total_execution_time_seconds']:.2f} seconds")
    print(f"Memory Usage: {end_memory:.2f} MB (Peak approx: {peak_memory:.2f} MB)")
    print(f"Honeypots Detected and Filtered: {res['honeypots_detected_in_cohort']}")
    print(f"Top 100 average candidate score: {res['top_100_average_score']:.4f}")
    print(f"Submission validation errors: {res['validation_errors']}")
    print(f"Output CSV path: {Path(output_csv).resolve()}")
    print("----------------------------------\n")

if __name__ == "__main__":
    main()
