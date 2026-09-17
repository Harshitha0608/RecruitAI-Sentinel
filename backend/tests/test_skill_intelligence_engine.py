import pytest
from typing import Dict, Any
from pathlib import Path

from backend.app.schemas.candidate import SkillSchema
from backend.app.schemas.candidate_intelligence import CandidateIntelligence
from backend.app.schemas.job_description import JobDescription
from backend.app.services.skill_intelligence_engine import SkillIntelligenceEngine

@pytest.fixture
def temp_synonyms_file(tmp_path) -> Path:
    """Fixture to create a temporary synonyms config file."""
    synonyms_data = {
        "sentence transformers": "sentence-transformers",
        "recommender systems": "recommendation systems",
        "recommendation engine": "recommendation systems",
        "retrieval augmented generation": "RAG"
    }
    file_path = tmp_path / "test_synonyms.json"
    import json
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(synonyms_data, f)
    return file_path

def test_engine_initialization_with_synonyms(temp_synonyms_file):
    """Test that the engine loads synonyms correctly from configuration."""
    engine = SkillIntelligenceEngine(synonyms_path=temp_synonyms_file)
    assert engine.synonym_map["sentence transformers"] == "sentence transformers"
    assert engine.synonym_map["recommender systems"] == "recommendation systems"
    assert engine.synonym_map["recommendation engine"] == "recommendation systems"
    assert engine.synonym_map["retrieval augmented generation"] == "rag" # cleaned to lowercase/stripped

def test_text_cleaning_and_normalization(temp_synonyms_file):
    """Test that skills are cleaned (whitespaces collapsed, lowercase) and normalized."""
    engine = SkillIntelligenceEngine(synonyms_path=temp_synonyms_file)
    
    # Check cleaning
    assert engine.clean_text("  Sentence   Transformers  \n") == "sentence transformers"
    assert engine.clean_text("") == ""
    
    # Check normalization mapping
    assert engine.normalize_skill("Sentence Transformers") == "sentence transformers"
    assert engine.normalize_skill("  recommender    systems ") == "recommendation systems"
    assert engine.normalize_skill("unknown skill") == "unknown skill"

def test_skill_analysis_matching(temp_synonyms_file):
    """Test full SkillAnalysis calculation for exact, synonym, missing, and additional skills."""
    engine = SkillIntelligenceEngine(synonyms_path=temp_synonyms_file)
    
    candidate = CandidateIntelligence.model_construct(
        candidate_id="CAND_1234567",
        skills=[
            SkillSchema.model_construct(name="Python"),
            SkillSchema.model_construct(name="Sentence Transformers"), # Maps to sentence-transformers (Synonym)
            SkillSchema.model_construct(name="Flask"),                 # Additional
            SkillSchema.model_construct(name="FastAPI")                # Exact match (case insensitive)
        ]
    )
    
    jd = JobDescription.model_construct(
        title="Software Engineer",
        requirements=["python", "sentence-transformers", "Kubernetes"],
        preferred_skills=["fastapi", "PyTorch"]
    )
    
    analysis = engine.analyze(candidate, jd)
    
    # Verify normalized skills
    # Expected candidate: flask, fastapi, python, sentence transformers
    assert analysis.normalized_candidate_skills == ["fastapi", "flask", "python", "sentence transformers"]
    # Expected required: kubernetes, python, sentence transformers
    assert analysis.normalized_required_skills == ["kubernetes", "python", "sentence transformers"]
    # Expected preferred: fastapi, pytorch
    assert analysis.normalized_preferred_skills == ["fastapi", "pytorch"]
    
    # Verify exact matches: python, fastapi, sentence transformers
    assert analysis.exact_matches == ["fastapi", "python", "sentence transformers"]
    
    # Verify synonym matches: empty
    assert analysis.synonym_matches == []
    
    # Verify missing required: kubernetes
    assert analysis.missing_required_skills == ["kubernetes"]
    
    # Verify missing preferred: pytorch
    assert analysis.missing_preferred_skills == ["pytorch"]
    
    # Verify additional candidate skills: flask
    assert analysis.additional_candidate_skills == ["flask"]

def test_deterministic_and_deduplicated_outputs(temp_synonyms_file):
    """Test that outputs are sorted alphabetically (deterministic) and deduplicated."""
    engine = SkillIntelligenceEngine(synonyms_path=temp_synonyms_file)
    
    candidate = CandidateIntelligence.model_construct(
        candidate_id="CAND_1234567",
        skills=[
            SkillSchema.model_construct(name="Python"),
            SkillSchema.model_construct(name="python"), # duplicate
            SkillSchema.model_construct(name="Docker"),
            SkillSchema.model_construct(name="docker"), # duplicate
            SkillSchema.model_construct(name="AWS")
        ]
    )
    
    jd = JobDescription.model_construct(
        title="DevOps",
        requirements=["AWS", "aws", "docker", "Jenkins"],
        preferred_skills=[]
    )
    
    analysis = engine.analyze(candidate, jd)
    
    # Deduped and sorted
    assert analysis.normalized_candidate_skills == ["aws", "docker", "python"]
    assert analysis.normalized_required_skills == ["aws", "docker", "jenkins"]
    
    assert analysis.exact_matches == ["aws", "docker"]
    assert analysis.additional_candidate_skills == ["python"]
    assert analysis.missing_required_skills == ["jenkins"]

def test_skill_analysis_sentence_matching(temp_synonyms_file):
    """Test skill matching within descriptive sentences with negative cases (prevent matching 'go' in 'good')."""
    engine = SkillIntelligenceEngine(synonyms_path=temp_synonyms_file)
    
    candidate = CandidateIntelligence.model_construct(
        candidate_id="CAND_9999999",
        skills=[
            SkillSchema.model_construct(name="Python"),
            SkillSchema.model_construct(name="Sentence Transformers"), # synonym sentence-transformers
            SkillSchema.model_construct(name="Go"),                     # negative check (should not match 'good')
            SkillSchema.model_construct(name="FastAPI")                  # match preferred
        ]
    )
    
    jd = JobDescription.model_construct(
        title="AI Architect",
        requirements=[
            "Must have strong python skills.", 
            "We want clean and good code.",              # 'good' contains 'go', but should not match 'Go'
            "Experience with sentence-transformers is a plus."
        ],
        preferred_skills=[
            "Experience building APIs with FastAPI or Flask."
        ]
    )
    
    analysis = engine.analyze(candidate, jd)
    
    # Exact matches: python, fastapi, sentence transformers
    assert "python" in analysis.exact_matches
    assert "fastapi" in analysis.exact_matches
    assert "sentence transformers" in analysis.exact_matches
    
    # Synonym matches: empty
    assert len(analysis.synonym_matches) == 0
    
    # Go should NOT match because of the word boundary check!
    assert "go" not in analysis.exact_matches
    assert "go" not in analysis.synonym_matches
