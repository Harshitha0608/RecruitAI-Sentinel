import pytest
from unittest.mock import MagicMock
from backend.app.ranking.ranking_engine import RankingEngine, SkillMatchEvaluator

@pytest.fixture
def evaluator():
    # Use real production RankingEngine so semantic-similarity behavior is fully exercised
    return SkillMatchEvaluator(ranking_engine=RankingEngine())

def build_cand(skills, career_text="", certs=None):
    cand = MagicMock()
    cand.candidate_id = "CAND_0000000"
    
    cand_skills = []
    for s in skills:
        sk = MagicMock()
        sk.name = s
        sk.proficiency = "Expert"
        sk.duration_months = 24
        cand_skills.append(sk)
    cand.skills = cand_skills
    
    cand.career_text = career_text
    cand.profile_text = ""
    cand.work_history_text = ""
    cand.education_text = ""
    cand.skills_text = ""
    cand.summary = ""
    cand.headline = ""
    cand.name = "Test Candidate"
    cand.education = []
    cand.projects = []
    cand.career_history = []
    cand.certifications = []
    cand.current_title = ""
    return cand

def test_a_salesforce_crm_routing_production(evaluator):
    """A. 'Salesforce CRM/PRM Modules' + candidate 'Salesforce CRM' reaches composite coverage and receives EQUIVALENT at 66.7%."""
    cand = build_cand(["Salesforce CRM"])
    req = "Salesforce CRM/PRM Modules"
    cls, reason, _ = evaluator.classify(req, cand)
    assert cls == "EQUIVALENT"
    assert "constituent skills" in reason
    assert "67%" in reason

def test_b_salesforce_crm_prm_single_token_fails(evaluator):
    """B. 'Salesforce CRM/PRM Modules' + candidate 'Salesforce' does NOT receive EQUIVALENT."""
    cand = build_cand(["Salesforce"])
    req = "Salesforce CRM/PRM Modules"
    cls, _, _ = evaluator.classify(req, cand)
    assert cls != "EQUIVALENT"
    assert cls in ("NONE", "RELATED")

def test_c_service_cloud_single_token_fails(evaluator):
    """C. 'Salesforce Service Cloud Sales Cloud' + candidate 'Salesforce' does NOT receive EQUIVALENT."""
    cand = build_cand(["Salesforce"])
    req = "Salesforce Service Cloud Sales Cloud"
    cls, _, _ = evaluator.classify(req, cand)
    assert cls != "EQUIVALENT"
    assert cls in ("NONE", "RELATED")

def test_d_service_cloud_constituent_evidence(evaluator):
    """D. 'Salesforce Service Cloud Sales Cloud' + candidate 'Salesforce + Service Cloud' can receive EQUIVALENT at 75%."""
    cand = build_cand(["Salesforce", "Service Cloud"])
    req = "Salesforce Service Cloud Sales Cloud"
    cls, reason, _ = evaluator.classify(req, cand)
    assert cls == "EQUIVALENT"
    assert "constituent skills" in reason
    assert "75%" in reason

def test_d2_all_constituent_evidence(evaluator):
    cand = build_cand(["Salesforce", "Service Cloud", "Sales Cloud"])
    req = "Salesforce Service Cloud Sales Cloud"
    cls, reason, _ = evaluator.classify(req, cand)
    assert cls == "EQUIVALENT"
    assert "constituent skills" in reason

def test_e_competitor_protection(evaluator):
    """E. 'Salesforce Service Cloud Sales Cloud' + Oracle CRM remains protected as RELATED/NONE and does not receive composite credit."""
    cand = build_cand(["Oracle CRM", "React"])
    req = "Salesforce Service Cloud Sales Cloud"
    cls, _, _ = evaluator.classify(req, cand)
    assert cls != "EQUIVALENT"
    assert cls in ("NONE", "RELATED")
    
    req2 = "Lightning Aura, LWC, HTML, CSS, JavaScript"
    cls2, _, _ = evaluator.classify(req2, cand)
    assert cls2 not in ("DIRECT", "EQUIVALENT")

def test_f_certification_isolation(evaluator):
    """F. Certification requirements never enter composite matching."""
    cand = build_cand(["Salesforce", "Apex"])
    req = "Salesforce Platform Developer I"
    cls, reason, _ = evaluator.classify(req, cand)
    assert cls == "NONE"
    assert "Missing required certification" in reason

def test_g_atomic_requirement_semantic_similarity(evaluator):
    """G. At least one atomic requirement still exercises the normal semantic-similarity path."""
    # Test unverified in text -> RELATED
    cand_unverified = build_cand(["bm25"], career_text="working on search engines")
    req = "elasticsearch"
    cls_u, reason_u, _ = evaluator.classify(req, cand_unverified)
    assert cls_u == "RELATED"
    assert "High semantic similarity with 'bm25'" in reason_u
    assert "unverified in text" in reason_u

    # Test verified in text -> SUPPORTED
    cand_verified = build_cand(["bm25"], career_text="maintained elasticsearch clusters for search")
    cls_v, reason_v, _ = evaluator.classify(req, cand_verified)
    assert cls_v == "SUPPORTED"
    assert "High semantic similarity with 'bm25'" in reason_v
    assert "verified in text" in reason_v

def test_generic_web_skill_fails_critical(evaluator):
    cand = build_cand(["JavaScript", "HTML", "CSS"])
    req = "Lightning Aura, LWC, HTML, CSS, JavaScript"
    cls, _, _ = evaluator.classify(req, cand)
    assert cls in ("NONE", "RELATED", "SUPPORTED")
    assert cls not in ("DIRECT", "EQUIVALENT")


def test_redrob_prose_requirement_constituent_matching():
    """Verifies constituent atomic skill matching for conversational/prose requirements."""
    from backend.app.schemas.job_description import JobDescription, ExperienceRequirement
    
    engine = RankingEngine()
    
    # Mock Redrob-style JD with prose requirements and atomic technical skills
    jd = JobDescription(
        title="Senior AI Engineer",
        company="Redrob",
        location="Remote",
        employment_type="Full-time",
        experience_requirement=ExperienceRequirement(raw_text="5+ years", min_years=5.0),
        education="Bachelor's in Computer Science",
        summary="Building AI retrieval systems",
        requirements=[
            "Production experience with embeddings-based retrieval systems (Sentence-Transformers, OpenAI embeddings, BGE, E5, or similar) deployed to real users",
            "Production experience with vector databases or hybrid search infrastructure — Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, or FAISS",
            "Hands-on experience fine-tuning open-weights models (LLaMA, Mistral, Qwen) using LoRA, QLoRA, PEFT, or full fine-tuning on domain-specific datasets",
            "Experience designing and evaluating search relevance — NDCG, MRR, MAP, or custom ranking metrics"
        ],
        preferred_skills=[
            "Experience with Learning-to-Rank algorithms (LambdaMART, XGBoost, or neural rankers)"
        ],
        responsibilities=["Build search systems"],
        disqualifiers=["Lack of production experience"],
        keywords=["ai", "embeddings", "vector", "search"],
        technical_skills=[
            "Sentence Transformers", "OpenAI Embeddings", "BGE", "E5",
            "Pinecone", "Weaviate", "Qdrant", "Milvus", "OpenSearch",
            "Elasticsearch", "FAISS", "LoRA", "QLoRA", "PEFT", "NDCG",
            "MRR", "MAP", "Learning-to-Rank", "XGBoost"
        ]
    )

    def _setup_signals(c):
        c.behavioral_signals = MagicMock()
        c.behavioral_signals.open_to_work_flag = True
        c.behavioral_signals.expected_salary_range_inr_lpa = MagicMock(min=25.0, max=35.0)
        c.behavioral_signals.signup_date = "2024-01-01"
        c.behavioral_signals.last_active_date = "2024-06-01"
        c.behavioral_signals.recruiter_response_rate = 0.85
        c.behavioral_signals.profile_completeness_score = 90.0
        c.behavioral_signals.github_activity_score = 80.0
        c.behavioral_signals.interview_completion_rate = 0.9
        c.behavioral_signals.offer_acceptance_rate = 0.8
        c.behavioral_signals.notice_period_days = 30
        c.behavioral_signals.preferred_work_mode = "remote"
        c.behavioral_signals.willing_to_relocate = True
        c.behavioral_signals.profile_views_received_30d = 10
        c.behavioral_signals.applications_submitted_30d = 5
        c.behavioral_signals.connection_count = 100
        c.behavioral_signals.endorsements_received = 10
        c.behavioral_signals.search_appearance_30d = 20
        c.behavioral_signals.saved_by_recruiters_30d = 5

    # 1. Candidate with genuine atomic technologies receives skill credit
    cand_matching = build_cand(["Pinecone", "Sentence Transformers", "LoRA"])
    cand_matching.candidate_id = "CAND_0000001"
    cand_matching.years_of_experience = 6.0
    cand_matching.location = "Remote"
    cand_matching.notice_period = 30
    _setup_signals(cand_matching)
    eval_res = engine.evaluate_candidate(cand_matching, jd)
    assert eval_res["skill_score"] > 20.0, f"Expected substantial skill credit, got {eval_res['skill_score']}"
    assert "critical_skills_matched" in eval_res["scoring_breakdown"]
    assert len(eval_res["scoring_breakdown"]["critical_skills_matched"]) == 2
    assert len(eval_res["scoring_breakdown"]["missing_critical_skills"]) == 0

    # 2. Candidate without relevant technologies receives no credit
    cand_unrelated = build_cand(["Java", "Spring Boot", "MySQL"])
    cand_unrelated.candidate_id = "CAND_0000002"
    cand_unrelated.years_of_experience = 6.0
    cand_unrelated.location = "Remote"
    cand_unrelated.notice_period = 30
    _setup_signals(cand_unrelated)
    eval_unrelated = engine.evaluate_candidate(cand_unrelated, jd)
    assert eval_unrelated["skill_score"] == 0.0
    assert len(eval_unrelated["scoring_breakdown"]["missing_critical_skills"]) == 2

    # 3. Generic words such as "production", "experience", "systems", "users" do NOT create skill matches
    cand_generic = build_cand(["production", "experience", "systems", "users", "development"])
    cand_generic.candidate_id = "CAND_0000003"
    cand_generic.years_of_experience = 6.0
    cand_generic.location = "Remote"
    cand_generic.notice_period = 30
    _setup_signals(cand_generic)
    eval_generic = engine.evaluate_candidate(cand_generic, jd)
    assert eval_generic["skill_score"] == 0.0
    assert len(eval_generic["scoring_breakdown"]["missing_critical_skills"]) == 2

