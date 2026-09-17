import pytest
from pathlib import Path
from backend.app.services.jd_parser import JDParser
from backend.app.ranking.ranking_engine import SkillMatchEvaluator, RankingEngine
from backend.app.retrieval.retrieval_engine import RetrievalEngine
from backend.app.schemas.candidate_intelligence import CandidateIntelligence
from backend.app.schemas.candidate import SkillSchema, CertificationSchema, RedrobSignalsSchema

def get_mock_signals():
    return RedrobSignalsSchema.model_construct(
        profile_completeness_score=100,
        signup_date="2023-01-01",
        last_active_date="2023-01-01",
        open_to_work_flag=True,
        profile_views_received_30d=10,
        applications_submitted_30d=10,
        recruiter_response_rate=1.0,
        avg_response_time_hours=1.0,
        skill_assessment_scores={},
        connection_count=100,
        endorsements_received=10,
        notice_period_days=30,
        expected_salary_range_inr_lpa=[10, 20],
        preferred_work_mode="remote",
        willing_to_relocate=False,
        github_activity_score=1.0,
        search_appearance_30d=10,
        saved_by_recruiters_30d=10,
        interview_completion_rate=1.0,
        offer_acceptance_rate=1.0,
        verified_email=True,
        verified_phone=True,
        linkedin_connected=True
    )

def test_certification_strict_isolation():
    evaluator = SkillMatchEvaluator()

    # Candidate with generic skills but NO certs
    cand_no_cert = CandidateIntelligence.model_construct(
        candidate_id="CAND_0000001",
        name="Test",
        headline="",
        summary="",
        current_title="Salesforce Developer",
        current_company="",
        years_of_experience=5.0,
        skills=[
            SkillSchema.model_construct(name="Salesforce", proficiency="expert", endorsements=10, duration_months=36),
            SkillSchema.model_construct(name="Apex", proficiency="expert", endorsements=10, duration_months=36),
            SkillSchema.model_construct(name="LWC", proficiency="expert", endorsements=10, duration_months=36)
        ],
        education=[],
        certifications=[],
        languages=[],
        career_history=[],
        behavioral_signals=get_mock_signals(),
        notice_period=30,
        location="Remote",
        normalized_skills=["salesforce", "apex", "lwc"],
        normalized_titles=[],
        work_history_text="",
        skills_text="salesforce apex lwc",
        profile_text="",
        career_text="",
        education_text=""
    )

    # 1. Must NOT satisfy PD1 requirement
    cls, msg, obj = evaluator.classify("Salesforce Platform Developer I", cand_no_cert)
    assert cls == "NONE", "Candidate without cert should NOT satisfy certification requirement using generic skills"

    # Candidate WITH cert
    cand_with_cert = CandidateIntelligence.model_construct(
        candidate_id="CAND_0000002",
        name="Test 2",
        headline="",
        summary="",
        current_title="Developer",
        current_company="",
        years_of_experience=5.0,
        skills=[],
        education=[],
        certifications=[
            CertificationSchema.model_construct(name="Salesforce Platform Developer I", issuer="Salesforce", year=2023)
        ],
        languages=[],
        career_history=[],
        behavioral_signals=get_mock_signals(),
        notice_period=30,
        location="Remote",
        normalized_skills=[],
        normalized_titles=[],
        work_history_text="",
        skills_text="",
        profile_text="",
        career_text="",
        education_text=""
    )

    # 2. Must satisfy PD1 requirement
    cls, msg, obj = evaluator.classify("Salesforce Platform Developer I", cand_with_cert)
    assert cls == "DIRECT"
    assert obj.name == "Salesforce Platform Developer I"

    # 3. Must satisfy PD1 requirement alias
    cls, msg, obj = evaluator.classify("PD1", cand_with_cert)
    assert cls == "DIRECT"
    
    # 4. Cert does NOT leak to satisfy generic requirement
    cls, msg, obj = evaluator.classify("Salesforce", cand_with_cert)
    assert cls == "NONE", "Certification evidence must not automatically satisfy generic technical skills"


def test_scenario_a_and_b_dedicated_certification_routing(tmp_path: Path):
    jd_content = """# Salesforce Developer
Certifications:
Salesforce Platform Developer I
"""
    jd_file = tmp_path / "dedicated_cert_jd.txt"
    jd_file.write_text(jd_content, encoding="utf-8")

    parser = JDParser(file_path=str(jd_file))
    jd = parser.parse()

    # Scenario A: jd.certifications contains the certification
    assert any("Salesforce Platform Developer I" in c for c in jd.certifications)

    # Scenario A: jd.requirements contains the certification exactly once
    req_matches = [r for r in jd.requirements if "Salesforce Platform Developer I" in r]
    assert len(req_matches) == 1

    # Scenario B: Dedicated certification is NOT guessed as preferred (routed to requirements)
    pref_matches = [p for p in jd.preferred_skills if "Salesforce Platform Developer I" in p]
    assert len(pref_matches) == 0

    # Scenario A: Retrieval query contains it through the existing requirements/preferred path
    retrieval_engine = RetrievalEngine()
    query_text = retrieval_engine._get_query_text(jd)
    assert "salesforce platform developer i" in query_text.lower()


def test_scenario_c_exact_certification_match():
    evaluator = SkillMatchEvaluator()
    candidate = CandidateIntelligence.model_construct(
        candidate_id="CAND_0000003",
        name="Exact Match Cand",
        headline="",
        summary="",
        current_title="Developer",
        current_company="",
        years_of_experience=3.0,
        skills=[],
        education=[],
        certifications=[
            CertificationSchema.model_construct(name="Salesforce Platform Developer I", issuer="Salesforce", year=2023)
        ],
        languages=[],
        career_history=[],
        behavioral_signals=get_mock_signals(),
        notice_period=30,
        location="Remote",
        normalized_skills=[],
        normalized_titles=[],
        work_history_text="",
        skills_text="",
        profile_text="",
        career_text="",
        education_text=""
    )
    cls, msg, obj = evaluator.classify("Salesforce Platform Developer I", candidate)
    assert cls == "DIRECT"
    assert obj is not None and obj.name == "Salesforce Platform Developer I"


def test_scenario_d_alias_certification_match():
    evaluator = SkillMatchEvaluator()
    # Candidate has alias PD1
    candidate_alias = CandidateIntelligence.model_construct(
        candidate_id="CAND_0000004",
        name="Alias Cand",
        headline="",
        summary="",
        current_title="Developer",
        current_company="",
        years_of_experience=3.0,
        skills=[],
        education=[],
        certifications=[
            CertificationSchema.model_construct(name="PD1", issuer="Salesforce", year=2023)
        ],
        languages=[],
        career_history=[],
        behavioral_signals=get_mock_signals(),
        notice_period=30,
        location="Remote",
        normalized_skills=[],
        normalized_titles=[],
        work_history_text="",
        skills_text="",
        profile_text="",
        career_text="",
        education_text=""
    )

    # JD requirement uses full canonical name
    cls1, msg1, obj1 = evaluator.classify("Salesforce Platform Developer I", candidate_alias)
    assert cls1 == "DIRECT"

    # Candidate has full name, JD requirement uses alias PD1
    candidate_full = CandidateIntelligence.model_construct(
        candidate_id="CAND_0000005",
        name="Full Cand",
        headline="",
        summary="",
        current_title="Developer",
        current_company="",
        years_of_experience=3.0,
        skills=[],
        education=[],
        certifications=[
            CertificationSchema.model_construct(name="Salesforce Platform Developer I", issuer="Salesforce", year=2023)
        ],
        languages=[],
        career_history=[],
        behavioral_signals=get_mock_signals(),
        notice_period=30,
        location="Remote",
        normalized_skills=[],
        normalized_titles=[],
        work_history_text="",
        skills_text="",
        profile_text="",
        career_text="",
        education_text=""
    )
    cls2, msg2, obj2 = evaluator.classify("PD1", candidate_full)
    assert cls2 == "DIRECT"


def test_scenario_e_generic_skill_cannot_satisfy_certification():
    evaluator = SkillMatchEvaluator()
    candidate = CandidateIntelligence.model_construct(
        candidate_id="CAND_0000006",
        name="Skills Only Cand",
        headline="",
        summary="",
        current_title="Salesforce Developer",
        current_company="",
        years_of_experience=5.0,
        skills=[
            SkillSchema.model_construct(name="Salesforce", proficiency="expert", endorsements=10, duration_months=36),
            SkillSchema.model_construct(name="Apex", proficiency="expert", endorsements=10, duration_months=36),
            SkillSchema.model_construct(name="LWC", proficiency="expert", endorsements=10, duration_months=36)
        ],
        education=[],
        certifications=[],
        languages=[],
        career_history=[],
        behavioral_signals=get_mock_signals(),
        notice_period=30,
        location="Remote",
        normalized_skills=["salesforce", "apex", "lwc"],
        normalized_titles=[],
        work_history_text="",
        skills_text="salesforce apex lwc",
        profile_text="",
        career_text="",
        education_text=""
    )
    cls, msg, obj = evaluator.classify("Salesforce Platform Developer I", candidate)
    assert cls == "NONE"


def test_scenario_f_certification_cannot_satisfy_generic_skill():
    evaluator = SkillMatchEvaluator()
    candidate = CandidateIntelligence.model_construct(
        candidate_id="CAND_0000007",
        name="Cert Only Cand",
        headline="",
        summary="",
        current_title="Developer",
        current_company="",
        years_of_experience=5.0,
        skills=[],
        education=[],
        certifications=[
            CertificationSchema.model_construct(name="Salesforce Platform Developer I", issuer="Salesforce", year=2023)
        ],
        languages=[],
        career_history=[],
        behavioral_signals=get_mock_signals(),
        notice_period=30,
        location="Remote",
        normalized_skills=[],
        normalized_titles=[],
        work_history_text="",
        skills_text="",
        profile_text="",
        career_text="",
        education_text=""
    )
    cls, msg, obj = evaluator.classify("Salesforce", candidate)
    assert cls == "NONE"


def test_scenario_g_no_duplicate_scoring_evidence(tmp_path: Path):
    jd_content = """# Senior Salesforce Developer
Requirements: Python

Certifications:
Salesforce Platform Developer I
"""
    jd_file = tmp_path / "dup_cert_jd.txt"
    jd_file.write_text(jd_content, encoding="utf-8")

    parser = JDParser(file_path=str(jd_file))
    jd = parser.parse()

    # Certification is in requirements exactly once
    req_certs = [r for r in jd.requirements if r == "Salesforce Platform Developer I"]
    assert len(req_certs) == 1

    # Certification is not in preferred skills
    pref_certs = [p for p in jd.preferred_skills if p == "Salesforce Platform Developer I"]
    assert len(pref_certs) == 0


def test_scenario_h_mandatory_vs_preferred_routing(tmp_path: Path):
    jd_content = """# Salesforce Lead
Requirements:
Salesforce Platform Developer I

Preferred Qualifications:
Salesforce Platform App Builder

Certifications:
Salesforce Administrator (ADM-201)
"""
    jd_file = tmp_path / "context_routing_jd.txt"
    jd_file.write_text(jd_content, encoding="utf-8")

    parser = JDParser(file_path=str(jd_file))
    jd = parser.parse()

    # Explicit mandatory remains in requirements
    assert "Salesforce Platform Developer I" in jd.requirements
    assert "Salesforce Platform Developer I" not in jd.preferred_skills

    # Explicit preferred remains in preferred_skills
    assert "Salesforce Platform App Builder" in jd.preferred_skills
    assert "Salesforce Platform App Builder" not in jd.requirements

    # Dedicated section with no explicit context routes to requirements deterministically
    assert any("administrator" in r.lower() or "adm-201" in r.lower() for r in jd.requirements)
    assert not any("administrator" in p.lower() or "adm-201" in p.lower() for p in jd.preferred_skills)
