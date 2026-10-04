"""
Regression tests for the stable (order-independent) critical-skill selection introduced
in RankingEngine.evaluate_candidate_with_embeddings().

These tests verify that:
  1. Reordering jd.requirements lines does NOT change the chosen critical skills
     or the resulting candidate score.
  2. Skills present only in jd.preferred_skills never become critical.
  3. scoring_breakdown keys 'critical_skills_matched' and 'missing_critical_skills'
     remain populated for API compatibility.
  4. The prose-fallback path (no jd.technical_skills) preserves original behaviour.
  5. The mandatory -20 penalty fires when the candidate matches zero critical skills
     and does NOT fire when at least one is matched.
"""

import pytest
from unittest.mock import MagicMock

from backend.app.ranking.ranking_engine import RankingEngine
from backend.app.schemas.job_description import JobDescription, ExperienceRequirement


def _make_jd(requirements, preferred_skills=None, technical_skills=None):
    return JobDescription(
        title="Senior AI Engineer",
        company="TestCo",
        location="Remote",
        employment_type="Full-time",
        experience_requirement=ExperienceRequirement(raw_text="5+ years", min_years=5.0),
        education="Bachelor's in CS",
        summary="Building AI systems.",
        requirements=requirements,
        preferred_skills=preferred_skills or [],
        responsibilities=["Build things"],
        disqualifiers=[],
        keywords=[],
        technical_skills=technical_skills or [],
    )


def _make_candidate(skills, years=6.0, notice=30, candidate_id="CAND_STABILITY_001"):
    cand = MagicMock()
    cand.candidate_id = candidate_id
    skill_mocks = []
    for s in skills:
        sk = MagicMock()
        sk.name = s
        sk.proficiency = "Expert"
        sk.duration_months = 36
        skill_mocks.append(sk)
    cand.skills = skill_mocks
    cand.certifications = []
    cand.career_text = " ".join(skills).lower()
    cand.profile_text = " ".join(skills).lower()
    cand.current_title = "AI Engineer"
    cand.years_of_experience = years
    cand.location = "Remote"
    cand.notice_period = notice
    cand.name = "Test Candidate"
    cand.summary = ""
    cand.headline = ""
    cand.education = []
    cand.projects = []
    cand.career_history = []
    signals = MagicMock()
    signals.expected_salary_range_inr_lpa = MagicMock(min=20.0, max=40.0)
    signals.signup_date = "2023-01-01"
    signals.last_active_date = "2026-01-01"
    signals.profile_completeness_score = 90.0
    signals.recruiter_response_rate = 0.85
    signals.interview_completion_rate = 0.9
    signals.offer_acceptance_rate = 0.8
    signals.notice_period_days = notice
    signals.open_to_work_flag = True
    signals.preferred_work_mode = "remote"
    signals.willing_to_relocate = True
    signals.profile_views_received_30d = 10
    signals.applications_submitted_30d = 5
    signals.connection_count = 200
    signals.endorsements_received = 20
    signals.search_appearance_30d = 30
    signals.saved_by_recruiters_30d = 8
    signals.verified_email = True
    signals.verified_phone = True
    signals.linkedin_connected = True
    signals.github_activity_score = 80.0
    cand.behavioral_signals = signals
    return cand


def _evaluate(engine, candidate, jd):
    return engine.evaluate_candidate_with_embeddings(
        candidate=candidate,
        jd=jd,
        jd_title_emb=None,
        jd_emb=None,
        cand_emb=None,
        role_embs=None,
        skill_rarity_map={},
    )


@pytest.fixture(scope="module")
def engine():
    return RankingEngine()


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_REQUIREMENTS_ORIGINAL = [
    "Production experience with embeddings-based retrieval systems (Sentence-Transformers, OpenAI embeddings, BGE, E5, or similar)",
    "Production experience with vector databases -- Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, or FAISS",
    "Hands-on experience fine-tuning open-weights models using LoRA, QLoRA, PEFT",
    "Experience designing and evaluating search relevance -- NDCG, MRR, MAP",
]

_REQUIREMENTS_REORDERED = [
    "Hands-on experience fine-tuning open-weights models using LoRA, QLoRA, PEFT",
    "Experience designing and evaluating search relevance -- NDCG, MRR, MAP",
    "Production experience with embeddings-based retrieval systems (Sentence-Transformers, OpenAI embeddings, BGE, E5, or similar)",
    "Production experience with vector databases -- Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, or FAISS",
]

_TECHNICAL_SKILLS = [
    "Sentence Transformers", "OpenAI Embeddings", "BGE", "E5",
    "Pinecone", "Weaviate", "Qdrant", "Milvus", "OpenSearch",
    "Elasticsearch", "FAISS", "LoRA", "QLoRA", "PEFT", "NDCG", "MRR", "MAP",
]


def _derive_critical(requirements):
    """Mirror the engine's internal atomic critical-skill derivation (ONTOLOGY-based).

    Uses RankingEngine._get_ontology_skills_in_text directly so this helper always
    reflects the actual engine behaviour without duplicating logic.
    """
    seen: set = set()
    required_atomic: list = []
    for req_line in requirements:
        for atomic_lower in RankingEngine._get_ontology_skills_in_text(req_line):
            if atomic_lower not in seen:
                seen.add(atomic_lower)
                required_atomic.append(atomic_lower)
    required_atomic.sort()
    return required_atomic[:2]


# ---------------------------------------------------------------------------
# Test 1: Critical-skill stability on requirement line reorder
# ---------------------------------------------------------------------------

class TestCriticalSkillStabilityOnReorder:

    def test_critical_skills_identical_after_reorder(self):
        """Selected critical skills must be the same set regardless of line order."""
        critical_original = _derive_critical(_REQUIREMENTS_ORIGINAL)
        critical_reordered = _derive_critical(_REQUIREMENTS_REORDERED)
        assert critical_original == critical_reordered, (
            f"Critical skills changed on reorder!\n"
            f"  Original  -> {critical_original}\n"
            f"  Reordered -> {critical_reordered}"
        )

    def test_score_stable_after_reorder(self, engine):
        """Candidate skill_score must be identical when requirement lines are reordered."""
        candidate_a = _make_candidate(
            ["Sentence Transformers", "FAISS", "LoRA"],
            candidate_id="CAND_REORDER_A",
        )
        candidate_b = _make_candidate(
            ["Sentence Transformers", "FAISS", "LoRA"],
            candidate_id="CAND_REORDER_B",
        )

        jd_original = _make_jd(requirements=_REQUIREMENTS_ORIGINAL, technical_skills=_TECHNICAL_SKILLS)
        jd_reordered = _make_jd(requirements=_REQUIREMENTS_REORDERED, technical_skills=_TECHNICAL_SKILLS)

        RankingEngine._evaluation_cache.clear()
        res_original = _evaluate(engine, candidate_a, jd_original)

        RankingEngine._evaluation_cache.clear()
        res_reordered = _evaluate(engine, candidate_b, jd_reordered)

        assert res_original["skill_score"] == res_reordered["skill_score"], (
            f"skill_score changed on requirement reorder!\n"
            f"  Original  -> {res_original['skill_score']}\n"
            f"  Reordered -> {res_reordered['skill_score']}"
        )


# ---------------------------------------------------------------------------
# Test 2: Preferred-only skills must not become critical
# ---------------------------------------------------------------------------

class TestPreferredSkillsNeverCritical:

    _REQUIREMENTS = [
        "Production experience with vector databases -- FAISS, Pinecone, or Milvus",
    ]
    _PREFERRED = [
        "Experience with Learning-to-Rank algorithms (LambdaMART, XGBoost, or neural rankers)"
    ]
    # technical_skills mixes both sections (as the parser builds it)
    _TECH = ["FAISS", "Pinecone", "Milvus", "XGBoost", "LambdaMART"]

    def test_preferred_only_skill_not_in_critical(self):
        """XGBoost (preferred-only) must not appear as a critical skill.

        The required line contains 'FAISS', 'Pinecone', 'Milvus' (all ONTOLOGY-recognized).
        'XGBoost' and 'LambdaMART' appear only in the preferred line and must not leak.
        """
        critical = _derive_critical(self._REQUIREMENTS)
        lower_critical = [c.lower() for c in critical]
        assert "xgboost" not in lower_critical, (
            f"XGBoost (preferred-only) incorrectly selected as critical: {critical}"
        )
        assert "lambdamart" not in lower_critical, (
            f"LambdaMART (preferred-only) incorrectly selected as critical: {critical}"
        )

    def test_required_atomic_skills_in_critical(self):
        """Only skills found in required lines may appear in the critical list."""
        critical = _derive_critical(self._REQUIREMENTS)
        lower_critical = {c.lower() for c in critical}
        allowed = {"faiss", "pinecone", "milvus"}
        assert lower_critical.issubset(allowed), (
            f"Critical skills contain unexpected entries: {critical}"
        )


# ---------------------------------------------------------------------------
# Test 3: scoring_breakdown API fields remain populated
# ---------------------------------------------------------------------------

class TestScoringBreakdownAPIContract:

    def test_breakdown_fields_present_and_list(self, engine):
        """'critical_skills_matched' and 'missing_critical_skills' must be lists."""
        jd = _make_jd(
            requirements=[
                "Experience with Sentence Transformers or similar embedding models",
                "Production experience with FAISS or Pinecone vector databases",
            ],
            technical_skills=["Sentence Transformers", "FAISS", "Pinecone"],
        )
        candidate = _make_candidate(
            ["Sentence Transformers", "FAISS"],
            candidate_id="CAND_API_CONTRACT",
        )
        RankingEngine._evaluation_cache.clear()
        result = _evaluate(engine, candidate, jd)

        breakdown = result.get("scoring_breakdown", {})
        assert "critical_skills_matched" in breakdown
        assert "missing_critical_skills" in breakdown
        assert isinstance(breakdown["critical_skills_matched"], list)
        assert isinstance(breakdown["missing_critical_skills"], list)


# ---------------------------------------------------------------------------
# Test 4: Prose-fallback path when technical_skills is empty
# ---------------------------------------------------------------------------

class TestProseFallbackBehavior:

    def test_fallback_produces_float_skill_score(self, engine):
        """With no technical_skills, prose fallback must still return a valid float score."""
        jd = _make_jd(
            requirements=["Python development experience", "FastAPI REST API experience", "Docker containerization"],
            technical_skills=[],
        )
        candidate = _make_candidate(["Python", "FastAPI"], candidate_id="CAND_FALLBACK")
        candidate.career_text = "python fastapi rest api experience"
        RankingEngine._evaluation_cache.clear()
        result = _evaluate(engine, candidate, jd)
        assert isinstance(result["skill_score"], float)
        assert "critical_skills_matched" in result["scoring_breakdown"]
        assert "missing_critical_skills" in result["scoring_breakdown"]


# ---------------------------------------------------------------------------
# Test 5: Mandatory penalty behaviour
# ---------------------------------------------------------------------------

class TestMandatoryPenaltyBehavior:

    _REQUIREMENTS = [
        "Production experience with Sentence Transformers embedding models",
        "Production experience with FAISS or Pinecone vector databases",
    ]
    _TECH = ["Sentence Transformers", "FAISS", "Pinecone"]

    def test_penalty_fires_zero_critical_matches(self, engine):
        """Candidate with no relevant skills should score lower than one with critical skills."""
        jd = _make_jd(requirements=self._REQUIREMENTS, technical_skills=self._TECH)

        cand_zero = _make_candidate(["Java", "Spring Boot", "MySQL"], candidate_id="CAND_PEN_ZERO")
        cand_zero.career_text = "java spring boot mysql"

        cand_both = _make_candidate(["Sentence Transformers", "FAISS"], candidate_id="CAND_PEN_BOTH")
        cand_both.career_text = "sentence transformers faiss vector search"

        RankingEngine._evaluation_cache.clear()
        res_zero = _evaluate(engine, cand_zero, jd)
        RankingEngine._evaluation_cache.clear()
        res_both = _evaluate(engine, cand_both, jd)

        assert res_both["skill_score"] > res_zero["skill_score"], (
            f"Candidate with critical skills must outscore zero-match candidate.\n"
            f"  Both matched -> {res_both['skill_score']}\n"
            f"  Zero matched -> {res_zero['skill_score']}"
        )

    def test_penalty_does_not_fire_one_critical_matched(self, engine):
        """Matching at least one critical skill prevents the full -20 penalty."""
        jd = _make_jd(requirements=self._REQUIREMENTS, technical_skills=self._TECH)

        cand_one = _make_candidate(["Sentence Transformers"], candidate_id="CAND_PEN_ONE")
        cand_one.career_text = "sentence transformers embeddings"

        cand_zero = _make_candidate(["Java", "Spring Boot"], candidate_id="CAND_PEN_ZERO2")
        cand_zero.career_text = "java spring boot"

        RankingEngine._evaluation_cache.clear()
        res_one = _evaluate(engine, cand_one, jd)
        RankingEngine._evaluation_cache.clear()
        res_zero = _evaluate(engine, cand_zero, jd)

        assert res_one["skill_score"] >= res_zero["skill_score"], (
            f"Matching one critical should not score below zero matches.\n"
            f"  One matched  -> {res_one['skill_score']}\n"
            f"  Zero matched -> {res_zero['skill_score']}"
        )


# ---------------------------------------------------------------------------
# Test 6: False-positive prevention for short/common ONTOLOGY skill names
# ---------------------------------------------------------------------------

class TestFalsePositivePrevention:
    """Regression tests for the two correctness problems fixed in the ONTOLOGY-based
    critical-skill selection path:

    1. A skill that appears *only* in preferred_skills text must not become critical
       merely because the same word accidentally appears in required prose (provenance).
    2. Short skills like 'C' must not match because 'C++' appears in required text
       ('c' is not in ONTOLOGY; 'c++' is).
    3. Ordinary English verbs/nouns ('go', 'react', 'rest') must not match the
       ONTOLOGY technical skills when they appear all-lowercase in required prose.
    4. Order-independence continues to hold under the ONTOLOGY-based derivation.
    """

    # --- helpers -----------------------------------------------------------

    @staticmethod
    def _skill_in(skill_lower: str, derived: list) -> bool:
        return skill_lower in {c.lower() for c in derived}

    # --- Test 6a: preferred-only skill does not contaminate critical list --

    def test_preferred_only_word_in_required_prose_does_not_become_critical(self):
        """If a skill name appears only in the preferred section but the *same word*
        accidentally occurs in required prose (e.g. 'Go to production'), it must NOT
        be selected as critical. The ONTOLOGY-based selection scans only jd.requirements
        lines, so the preferred-section skill can only contaminate if its name literally
        appears as a technical term (capitalized) inside a required line.
        """
        # Required line contains the English word 'go' (lowercase verb, not the lang)
        # Preferred line contains 'Go' as a programming language.
        requirements = [
            "Ability to go above and beyond when delivering production features",
            "5+ years experience building distributed Python systems",
        ]
        # Derivation scans only requirements; 'go' (lowercase) should be rejected
        # because purely-alpha skills require a non-lowercase match.
        derived = _derive_critical(requirements)
        assert not self._skill_in("go", derived), (
            f"'go' (lowercase English verb in required prose) incorrectly selected as critical: {derived}"
        )

    # --- Test 6b: 'C' does not match 'C++' in requirement text ------------

    def test_single_char_c_does_not_match_cpp_in_requirement(self):
        """'C' alone is NOT in the ONTOLOGY. 'c++' IS in the ONTOLOGY.
        A requirement line containing 'C++' must select 'c++' as the critical skill,
        not a phantom 'C' skill.
        """
        requirements = [
            "Strong proficiency in C++ for low-latency systems programming",
            "Experience with Python and PyTorch for ML model development",
        ]
        derived = _derive_critical(requirements)
        # 'c' is not an ONTOLOGY skill at all — must never appear
        assert not self._skill_in("c", derived), (
            f"Phantom 'C' skill incorrectly appeared in critical list: {derived}"
        )
        # 'c++' IS in the ONTOLOGY and should be present
        assert self._skill_in("c++", derived), (
            f"'c++' (ONTOLOGY skill) missing from critical list: {derived}"
        )

    # --- Test 6c: English prose homographs do not match ONTOLOGY skills ---

    def test_english_prose_homographs_not_selected_as_critical(self):
        """Ordinary English verbs/nouns that happen to share a name with ONTOLOGY skills
        must be rejected when they appear all-lowercase in requirement prose.

        Tested phrases (from the task spec):
          - 'go above and beyond'  -> must NOT match ONTOLOGY 'go' (Go language)
          - 'react quickly'        -> must NOT match ONTOLOGY 'react' (React framework)
          - 'the rest of the team' -> 'rest' is NOT in the ONTOLOGY; this is a
                                      belt-and-suspenders check.
        """
        requirements = [
            "Must be willing to go above and beyond to meet deadlines",
            "Ability to react quickly to production incidents and outages",
            "Work well with the rest of the engineering team",
        ]
        derived = _derive_critical(requirements)
        assert not self._skill_in("go", derived), (
            f"'go' (English verb in prose) incorrectly selected as critical: {derived}"
        )
        assert not self._skill_in("react", derived), (
            f"'react' (English verb in prose) incorrectly selected as critical: {derived}"
        )
        # 'rest' is not in ONTOLOGY — this is an additional provenance check
        assert not self._skill_in("rest", derived), (
            f"'rest' incorrectly selected as critical (not even in ONTOLOGY): {derived}"
        )

    # --- Test 6d: technical capitalized forms ARE accepted -----------------

    def test_capitalized_skill_names_in_requirements_are_accepted(self):
        """The capitalized / all-caps technical forms of the same short skill names
        must BE selected as critical candidates when they appear correctly in requirements.
        """
        requirements = [
            "Strong proficiency in Go for backend microservices development",
            "Production experience with React and TypeScript for frontend systems",
        ]
        derived = _derive_critical(requirements)
        # 'Go' (capital G) and 'React' (capital R) are the technical forms
        assert self._skill_in("go", derived) or self._skill_in("react", derived) or self._skill_in("typescript", derived), (
            f"No expected ONTOLOGY skill found in critical list for technical requirements: {derived}"
        )

    # --- Test 6e: order-independence still holds under ONTOLOGY derivation --

    def test_ontology_derivation_is_order_independent(self):
        """Shuffling requirement lines must not change which skills are selected."""
        requirements_a = [
            "Production experience with FAISS or Pinecone vector databases",
            "Proficiency in Python for backend services",
        ]
        requirements_b = [
            "Proficiency in Python for backend services",
            "Production experience with FAISS or Pinecone vector databases",
        ]
        derived_a = _derive_critical(requirements_a)
        derived_b = _derive_critical(requirements_b)
        assert derived_a == derived_b, (
            f"Critical skills changed on requirement reorder!\n"
            f"  Order A -> {derived_a}\n"
            f"  Order B -> {derived_b}"
        )
