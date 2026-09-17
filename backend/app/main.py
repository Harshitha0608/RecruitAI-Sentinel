import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from pydantic import ValidationError

from backend.app.config.settings import settings
from backend.app.config.logging import setup_logging
from backend.app.config.middleware import setup_middleware
from backend.app.api.endpoints.health import router as health_router
from backend.app.api.endpoints.precompute import router as precompute_router
from backend.app.api.endpoints.ranking import router as ranking_router
from backend.app.api.endpoints.candidate import router as candidate_router
from backend.app.api.endpoints.analytics import router as analytics_router

from backend.app.core.exceptions import (
    validation_exception_handler,
    value_error_handler,
    runtime_error_handler,
    file_not_found_error_handler,
    generic_exception_handler
)

# Setup system logging config
setup_logging()
logger = logging.getLogger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Initializing RecruitAI Sentinel backend services...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Configure CPU thread limits for backend stability (FIX 12)
    try:
        import torch
        import faiss
        torch.set_num_threads(2)
        faiss.omp_set_num_threads(2)
        logger.info("Successfully configured PyTorch & FAISS to run with 2 CPU threads max.")
    except Exception as e:
        logger.warning(f"Could not configure startup CPU thread limits: {e}")
    
    # Verify and print configured paths
    if settings.CHALLENGE_ROOT:
        logger.info(f"Challenge Root Path: {settings.CHALLENGE_ROOT}")
    else:
        logger.warning("Configuration Warning: CHALLENGE_ROOT is missing or None")
        
    if settings.CANDIDATE_DATASET_PATH:
        logger.info(f"Candidates Dataset Path: {settings.CANDIDATE_DATASET_PATH}")
    else:
        logger.warning("Configuration Warning: CANDIDATE_DATASET_PATH is missing or None")
        
    if settings.JOB_DESCRIPTION_PATH:
        logger.info(f"Job Description Path: {settings.JOB_DESCRIPTION_PATH}")
    else:
        logger.warning("Configuration Warning: JOB_DESCRIPTION_PATH is missing or None")
        
    yield
    # Shutdown actions
    logger.info("Shutting down RecruitAI Sentinel backend services...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

# Setup standard middlewares
setup_middleware(app)

# Register central exception handlers
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(RuntimeError, runtime_error_handler)
app.add_exception_handler(FileNotFoundError, file_not_found_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API routes
app.include_router(health_router)
app.include_router(precompute_router, prefix="/api", tags=["precompute"])
app.include_router(ranking_router, prefix="/api", tags=["ranking"])
app.include_router(candidate_router, prefix="/api", tags=["candidate"])
app.include_router(analytics_router, prefix="/api", tags=["analytics"])

