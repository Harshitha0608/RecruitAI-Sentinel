import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Define base paths relative to this file
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "RecruitAI Sentinel"
    ENVIRONMENT: str = "local"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Dataset and storage paths (defaulting relative to project root)
    CHALLENGE_ROOT: str | None = None
    CANDIDATE_DATASET_PATH: str | None = None
    JOB_DESCRIPTION_PATH: str | None = None
    
    SQLITE_DB_PATH: str = Field(
        default=str(BASE_DIR / "backend" / "app" / "sentinel.db"),
        validation_alias="SQLITE_DB_PATH"
    )
    VECTOR_INDEX_PATH: str = Field(
        default=str(BASE_DIR / "backend" / "app" / "vectors.faiss"),
        validation_alias="VECTOR_INDEX_PATH"
    )
    SKILL_SYNONYMS_PATH: str = Field(
        default=str(BASE_DIR / "backend" / "app" / "config" / "skill_synonyms.json"),
        validation_alias="SKILL_SYNONYMS_PATH"
    )
    CANDIDATE_IDS_PATH: str = Field(
        default=str(BASE_DIR / "backend" / "app" / "candidate_ids.json"),
        validation_alias="CANDIDATE_IDS_PATH"
    )
    TFIDF_PATH: str = Field(
        default=str(BASE_DIR / "backend" / "app" / "tfidf.pkl"),
        validation_alias="TFIDF_PATH"
    )
    CANDIDATE_OFFSETS_PATH: str = Field(
        default=str(BASE_DIR / "backend" / "app" / "candidate_offsets.json"),
        validation_alias="CANDIDATE_OFFSETS_PATH"
    )

    
    # Core system defaults
    DEFAULT_COHORT_LIMIT: int = 1000
    PIPELINE_VERSION: str = "1.0.0"

    # Pydantic settings config to load variables from project root .env
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Check for dynamically saved active job description on startup
for ext in [".docx", ".txt", ".md"]:
    active_path = BASE_DIR / "backend" / "app" / f"active_job_description{ext}"
    if active_path.exists():
        settings.JOB_DESCRIPTION_PATH = str(active_path)
        break

