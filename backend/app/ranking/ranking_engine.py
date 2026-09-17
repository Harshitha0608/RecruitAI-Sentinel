import logging
import re
from datetime import datetime
from typing import Dict, Tuple, List, Optional, Any

from backend.app.schemas.candidate_intelligence import CandidateIntelligence
from backend.app.schemas.job_description import JobDescription

logger = logging.getLogger("app.ranking.ranking_engine")

# Configurable relationship table for semantic matching (alphabetically sorted keys)
SEMANTIC_SIMILARITY_MAP: Dict[Tuple[str, str], float] = {
    ("chromadb", "faiss"): 0.75,
    ("chromadb", "milvus"): 0.75,
    ("chromadb", "pinecone"): 0.75,
    ("chromadb", "qdrant"): 0.75,
    ("chromadb", "vector database"): 0.60,
    ("chromadb", "vector databases"): 0.60,
    ("faiss", "milvus"): 0.75,
    ("faiss", "pinecone"): 0.75,
    ("faiss", "qdrant"): 0.75,
    ("faiss", "vector database"): 0.60,
    ("faiss", "vector databases"): 0.60,
    ("milvus", "pinecone"): 0.75,
    ("milvus", "qdrant"): 0.75,
    ("milvus", "vector database"): 0.60,
    ("milvus", "vector databases"): 0.60,
    ("pinecone", "qdrant"): 0.75,
    ("pinecone", "vector database"): 0.60,
    ("pinecone", "vector databases"): 0.60,
    ("qdrant", "vector database"): 0.60,
    ("qdrant", "vector databases"): 0.60,
    ("bert", "sentence transformers"): 0.70,
    ("bert", "sentence-transformers"): 0.70,
    ("bge", "sentence transformers"): 0.75,
    ("bge", "sentence-transformers"): 0.75,
    ("minilm", "sentence transformers"): 0.75,
    ("minilm", "sentence-transformers"): 0.75,
    ("mpnet", "sentence transformers"): 0.75,
    ("mpnet", "sentence-transformers"): 0.75,
    ("lora", "peft"): 0.80,
    ("lora", "qlora"): 0.80,
    ("peft", "qlora"): 0.80,
    ("bm25", "elasticsearch"): 0.75,
    ("bm25", "solr"): 0.75,
    ("bm25", "opensearch"): 0.75,
    ("elasticsearch", "solr"): 0.75,
    ("elasticsearch", "opensearch"): 0.75,
    ("dense retrieval", "semantic search"): 0.75,
    ("dense retrieval", "vector search"): 0.75,
    ("dense retrieval", "neural search"): 0.75,
    ("semantic search", "vector search"): 0.75,
    ("neural search", "semantic search"): 0.75,
    ("neural search", "vector search"): 0.75,
    ("python", "pytorch"): 0.20
}

class SkillMatchEvaluator:
    """Requirement-aware Skill Match Evaluator enforcing multi-tier classification."""

    ALIAS_MAP = {
        "ai": ["artificial intelligence"],
        "ml": ["machine learning"],
        "llm": ["large language models", "large language model"],
        "faiss": ["facebook ai similarity search"],
        "sentence transformers": ["sentence-transformers", "sentence transformer"],
        "python": ["python 3.x", "python3", "python 3"],
    }

    CERTIFICATION_ALIAS_MAP = {
        "salesforce platform developer i": ["pd1", "platform developer i", "platform developer 1", "salesforce platform developer 1"],
        "salesforce platform developer ii": ["pd2", "platform developer ii", "platform developer 2", "salesforce platform developer 2"],
        "salesforce administrator": ["adm-201", "adm201", "salesforce admin"],
        "salesforce platform app builder": ["platform app builder"]
    }

    CERT_SIGNAL_RE = re.compile(
        r'\b(?:certifications?|certified|cert|certs|adm-\d+|pd1|pd2|platform developer\s*(?:i/ii|i|ii|1/2|1|2)?|platform app builder)\b',
        re.IGNORECASE
    )

    VERSION_FAMILY_PATTERNS = {
        "bge": [r"\bbge\b", r"\bbge-[a-z0-9\-]+\b"],
        "python": [r"\bpython\b", r"\bpython\s*\d+(\.\d+)?\b", r"\bpython3\b"],
        "faiss": [r"\bfaiss\b", r"\bfacebook\s+ai\s+similarity\s+search\b"],
        "sentence transformers": [r"\bsentence[\s\-_]*transformers?\b"],
        "lora": [r"\blora\b", r"\bqlora\b"],
    }

    EQUIVALENT_DOMAINS = {
        "ai": ["ml", "machine learning", "deep learning"],
        "artificial intelligence": ["ml", "machine learning", "deep learning"],
        "machine learning": ["deep learning"],
        "ml": ["deep learning"]
    }

    SUPPORTED_DOMAINS = {
        "ai": ["nlp", "llm", "large language models", "natural language processing", "computer vision", "rag", "mlops", "cnn"],
        "machine learning": ["reinforcement learning", "feature engineering", "mlops", "cnn"],
        "ml": ["reinforcement learning", "feature engineering", "mlops", "cnn"],
        "postgresql": ["sql"],
        "sentence transformers": ["bert", "roberta", "spacy"]
    }

    BROAD_EXCLUDED_TERMS = {
        "data science", "python", "programming", "software engineering", "analytics", "coding", "computer science"
    }

    COMPETITOR_GROUPS = [
        {"aws", "azure", "gcp", "google cloud platform"},
        {"react", "angular", "vue", "svelte"},
        {"postgresql", "mysql", "oracle", "sql server", "sqlite", "mongodb"},
        {"faiss", "pinecone", "milvus", "qdrant", "chromadb", "weaviate"},
        {"sentence transformers", "bert", "roberta", "spacy"}
    ]

    def __init__(self, ranking_engine: Optional[Any] = None) -> None:
        self.ranking_engine = ranking_engine
        self._reverse_alias = {}
        for canonical, aliases in self.ALIAS_MAP.items():
            for alias in aliases:
                self._reverse_alias[alias] = canonical
                
        self._reverse_cert_alias = {}
        for canonical, aliases in self.CERTIFICATION_ALIAS_MAP.items():
            for alias in aliases:
                self._reverse_cert_alias[alias] = canonical

    def classify(self, jd_req: str, candidate: CandidateIntelligence) -> Tuple[str, str, Optional[Any]]:
        req_norm = jd_req.lower().strip()
        
        # 1. Isolation: Check if JD requirement is a certification
        is_cert_req = (
            bool(self.CERT_SIGNAL_RE.search(req_norm)) or
            req_norm in self.CERTIFICATION_ALIAS_MAP or
            req_norm in self._reverse_cert_alias
        )
        
        if is_cert_req:
            req_canonical = self._reverse_cert_alias.get(req_norm, req_norm)
            cand_certs_norm = [c.name.lower().strip() for c in (candidate.certifications or [])]
            cand_certs_canonical = [self._reverse_cert_alias.get(c, c) for c in cand_certs_norm]
            
            for idx, (orig_c, can_c) in enumerate(zip(cand_certs_norm, cand_certs_canonical)):
                if req_canonical == can_c or req_norm == orig_c:
                    return "DIRECT", f"Direct certification match '{orig_c}'", candidate.certifications[idx]
                    
            # Strict boundary: DO NOT fall back to generic technical skills, titles, or domains!
            return "NONE", "Missing required certification", None
            
        # 2. Generic technical skill evaluation (certs do not leak here)
        req_canonical = self._reverse_alias.get(req_norm, req_norm)

        cand_skills_norm = [s.name.lower().strip() for s in candidate.skills]
        cand_skills_canonical = [self._reverse_alias.get(s, s) for s in cand_skills_norm]
        cand_titles_norm = [candidate.current_title.lower().strip()] + [job.title.lower().strip() for job in candidate.career_history if job.title]
        career_text_norm = candidate.career_text.lower()

        # A. DIRECT MATCH 1: Exact or Alias Match in Skill Tags
        for idx, (orig_s, can_s) in enumerate(zip(cand_skills_norm, cand_skills_canonical)):
            if req_canonical == can_s or req_norm == orig_s:
                return "DIRECT", f"Direct skill tag match '{orig_s}'", candidate.skills[idx]

        # B. DIRECT MATCH 2: Model-Family / Version Match in Skill Tags
        for pattern in self.VERSION_FAMILY_PATTERNS.get(req_canonical, []):
            for idx, orig_s in enumerate(cand_skills_norm):
                if re.search(pattern, orig_s):
                    return "DIRECT", f"Model-family/version match '{orig_s}' for '{jd_req}'", candidate.skills[idx]

        # C. TITLE EQUIVALENCE (With Safeguard Rule: Must have supporting skill tag OR career text evidence!)
        has_title_claim = any(req_canonical in title or req_norm in title for title in cand_titles_norm)
        if has_title_claim:
            has_corroboration = (
                any(s in self.EQUIVALENT_DOMAINS.get(req_canonical, []) for s in cand_skills_canonical) or
                any(s in self.SUPPORTED_DOMAINS.get(req_canonical, []) for s in cand_skills_canonical) or
                any(s in career_text_norm for s in self.EQUIVALENT_DOMAINS.get(req_canonical, []))
            )
            if has_corroboration:
                return "EQUIVALENT", "Title claim corroborated by skills/career text evidence", None
            else:
                return "SUPPORTED", "Title claim present but lacks corroborating skill evidence", None

        # D. DOMAIN ONTOLOGY CHECK
        if req_canonical in self.EQUIVALENT_DOMAINS:
            for idx, s_can in enumerate(cand_skills_canonical):
                if s_can in self.EQUIVALENT_DOMAINS[req_canonical]:
                    return "EQUIVALENT", f"Skill '{s_can}' is a core equivalent domain substitute", candidate.skills[idx]

        if req_canonical in self.SUPPORTED_DOMAINS:
            for idx, s_can in enumerate(cand_skills_canonical):
                if s_can in self.SUPPORTED_DOMAINS[req_canonical]:
                    return "SUPPORTED", f"Skill '{s_can}' is a supporting domain subfield", candidate.skills[idx]

        # E. VERSION / MODEL FAMILY MENTION IN TEXT (e.g. bge-large in career text)
        for pattern in self.VERSION_FAMILY_PATTERNS.get(req_canonical, []):
            if re.search(pattern, career_text_norm):
                return "SUPPORTED", f"Version/model-family term mentioned in career text for '{jd_req}'", None

        # F. COMPETITOR CHECK
        for group in self.COMPETITOR_GROUPS:
            if req_canonical in group or req_norm in group:
                for idx, s_can in enumerate(cand_skills_canonical):
                    s_orig = cand_skills_norm[idx]
                    if (s_can in group or s_orig in group) and s_can != req_canonical and s_orig != req_norm:
                        if req_norm in career_text_norm or req_canonical in career_text_norm:
                            return "SUPPORTED", f"Competitor technology '{s_orig}' present but '{jd_req}' verified in text", candidate.skills[idx]
                        else:
                            return "RELATED", f"Competitor technology '{s_orig}' present but '{jd_req}' absent in text", None

        # G. COMPOSITE REQUIREMENT COVERAGE MATCH
        # If the requirement contains multiple words, it might be a composite string from the parser.
        # We calculate the token coverage using the candidate's skills that exactly substring-match.
        # This prevents generic single tokens from artificially satisfying large, specific composite strings.
        COMPOSITE_STOPWORDS = {
            "and", "or", "with", "experience", "in", "knowledge", "of", "understanding", "api", "apis", 
            "integration", "record", "types", "modules", "patterns", "best", "practices", "fields", 
            "page", "layouts", "custom", "settings", "dashboards", "reports", "the", "to", "for", "a", "an"
        }
        
        req_words = set(re.findall(r'[a-z0-9]+', req_norm))
        meaningful_req_tokens = {w for w in req_words if len(w) >= 3 and w not in COMPOSITE_STOPWORDS and w not in self.BROAD_EXCLUDED_TERMS}
        
        if len(meaningful_req_tokens) >= 3:
            matched_cand_skills = []
            matched_tokens = set()
            
            for idx, orig_s in enumerate(cand_skills_norm):
                can_s = cand_skills_canonical[idx]
                # If candidate skill is a substring of the requirement (with word boundaries)
                is_match = False
                if len(orig_s) >= 3 and re.search(r'\b' + re.escape(orig_s) + r'\b', req_norm):
                    is_match = True
                elif len(can_s) >= 3 and re.search(r'\b' + re.escape(can_s) + r'\b', req_norm):
                    is_match = True
                    
                if is_match:
                    matched_cand_skills.append(candidate.skills[idx])
                    matched_tokens.update(re.findall(r'[a-z0-9]+', orig_s))
                    matched_tokens.update(re.findall(r'[a-z0-9]+', can_s))
                    
            meaningful_matched = {w for w in matched_tokens if len(w) >= 3 and w not in COMPOSITE_STOPWORDS and w not in self.BROAD_EXCLUDED_TERMS}
            
            coverage = len(meaningful_matched) / len(meaningful_req_tokens)
            if coverage >= 0.60:
                best_skill = matched_cand_skills[0] if matched_cand_skills else None
                return "EQUIVALENT", f"Candidate possesses substantial constituent skills ({coverage*100:.0f}% coverage) for composite requirement", best_skill

        # H. SEMANTIC SIMILARITY & EXCLUSION VERIFICATION
        best_sim = 0.0
        best_cand_skill = None
        best_skill_name = None

        if self.ranking_engine:
            for idx, c_skill in enumerate(candidate.skills):
                sim = self.ranking_engine.get_semantic_similarity(c_skill.name, jd_req)
                if sim > best_sim:
                    best_sim = sim
                    best_cand_skill = c_skill
                    best_skill_name = c_skill.name.lower().strip()

        if best_skill_name:
            if best_skill_name in self.BROAD_EXCLUDED_TERMS:
                return "RELATED", f"Broad generic term '{best_skill_name}' cannot trigger SUPPORTED for '{jd_req}'", None

            if best_sim >= 0.70:
                if req_norm in career_text_norm or req_canonical in career_text_norm:
                    return "SUPPORTED", f"High semantic similarity with '{best_skill_name}' ({best_sim:.2f}), verified in text", best_cand_skill
                else:
                    return "RELATED", f"High semantic similarity with '{best_skill_name}' ({best_sim:.2f}), but unverified in text", None

        # I. CAREER TEXT MENTION
        if req_norm in career_text_norm or req_canonical in career_text_norm:
            return "SUPPORTED", f"Requirement '{jd_req}' mentioned in career text", None

        return "NONE", "No evidence found", None


class RankingEngine:
    """Core ranking engine which evaluates sub-scores, filters honeypots, and sorts candidates."""

    _evaluation_cache = {}
    _cached_jd_title = None
    _cached_jd_title_emb = None
    _cached_jd_text = None
    _cached_jd_emb = None

    def __init__(self, skill_engine: Optional[Any] = None) -> None:
        if skill_engine is None:
            from backend.app.services.skill_intelligence_engine import SkillIntelligenceEngine
            skill_engine = SkillIntelligenceEngine()
        self.skill_engine = skill_engine
        self.skill_evaluator = SkillMatchEvaluator(self)
        self._model = None

    _shared_model = None

    GENERIC_SKILL_WORDS = {
        "production", "experience", "systems", "users", "development",
        "application", "applications", "software", "knowledge", "design",
        "testing", "management", "tools", "data", "work", "team",
        "understanding", "infrastructure", "similar", "real", "domain",
        "specific", "hands-on", "hands on", "years", "deployment",
        "deployed", "models", "open-weights", "open weights", "technologies",
        "technology", "skills", "solutions", "practices", "stack"
    }

    def _get_constituent_technical_skills(self, req_text: str, technical_skills: List[str]) -> List[str]:
        """Finds concise atomic technical skills explicitly mentioned within a composite/prose requirement."""
        if not req_text or not technical_skills:
            return []
        
        req_norm = re.sub(r'[\-_/]', ' ', req_text.lower())
        constituents = []
        
        for skill in technical_skills:
            s_clean = skill.strip()
            s_lower = s_clean.lower()
            if len(s_lower) < 2 or s_lower in self.GENERIC_SKILL_WORDS:
                continue
            
            # Check whole-word boundary in original text
            pattern_orig = r'(?<![a-zA-Z0-9])' + re.escape(s_lower) + r'(?![a-zA-Z0-9])'
            if re.search(pattern_orig, req_text.lower()):
                constituents.append(s_clean)
                continue
            
            # Check normalized punctuation (e.g. Sentence-Transformers -> Sentence Transformers)
            s_norm = re.sub(r'[\-_/]', ' ', s_lower)
            pattern_norm = r'(?<![a-zA-Z0-9])' + re.escape(s_norm) + r'(?![a-zA-Z0-9])'
            if re.search(pattern_norm, req_norm):
                constituents.append(s_clean)
                
        return constituents

    def load_model(self) -> None:
        """Lazily loads SentenceTransformer embedding model."""
        if RankingEngine._shared_model is None:
            from backend.app.retrieval.retrieval_engine import RetrievalEngine
            retrieval = RetrievalEngine()
            if retrieval._model is not None:
                RankingEngine._shared_model = retrieval._model
            else:
                from sentence_transformers import SentenceTransformer
                RankingEngine._shared_model = SentenceTransformer("all-MiniLM-L6-v2")
        self._model = RankingEngine._shared_model

    def is_honeypot(self, candidate: CandidateIntelligence) -> bool:
        """Determines if a candidate profile is a strict chronological honeypot."""
        # 1. Salary Inconsistency: min salary > max salary
        expected_salary = candidate.behavioral_signals.expected_salary_range_inr_lpa
        if expected_salary.min > expected_salary.max:
            logger.debug(
                "Candidate identified as honeypot: expected min salary > max salary",
                extra={"candidate_id": candidate.candidate_id, "min": expected_salary.min, "max": expected_salary.max}
            )
            return True
            
        # 2. Date Inconsistency: last active date is before signup date
        try:
            signup_dt = datetime.strptime(candidate.behavioral_signals.signup_date, "%Y-%m-%d")
            active_dt = datetime.strptime(candidate.behavioral_signals.last_active_date, "%Y-%m-%d")
            if active_dt < signup_dt:
                logger.debug(
                    "Candidate identified as honeypot: last active date before signup date",
                    extra={"candidate_id": candidate.candidate_id, "signup": candidate.behavioral_signals.signup_date, "active": candidate.behavioral_signals.last_active_date}
                )
                return True
        except ValueError:
            pass

        # 3. Job Inconsistency: job start date > job end date in career history
        for job in candidate.career_history:
            if job.start_date and job.end_date:
                try:
                    s_dt = datetime.strptime(job.start_date, "%Y-%m-%d")
                    e_dt = datetime.strptime(job.end_date, "%Y-%m-%d")
                    if e_dt < s_dt:
                        logger.debug(
                            "Candidate identified as honeypot: career end date before start date",
                            extra={"candidate_id": candidate.candidate_id, "job": job.company, "start": job.start_date, "end": job.end_date}
                        )
                        return True
                except ValueError:
                    pass
            
            # Future job start
            if job.start_date:
                try:
                    s_dt = datetime.strptime(job.start_date, "%Y-%m-%d")
                    if s_dt.year > 2026:
                        logger.debug(
                            "Candidate identified as honeypot: career start date in the future",
                            extra={"candidate_id": candidate.candidate_id, "job": job.company, "start": job.start_date}
                        )
                        return True
                except ValueError:
                    pass
                    
            # 4. Job duration exceeds total years of experience
            job_years = job.duration_months / 12.0
            if job_years > candidate.years_of_experience + 0.5:
                logger.debug(
                    "Candidate identified as honeypot: job duration exceeds total experience",
                    extra={"candidate_id": candidate.candidate_id, "job": job.company, "duration_years": job_years, "total_experience": candidate.years_of_experience}
                )
                return True
                
        return False

    def get_semantic_similarity(self, cand_skill: str, req_skill: str) -> float:
        """Determines similarity based on configurable lookup map and boundary regex."""
        a_norm = cand_skill.lower().strip()
        b_norm = req_skill.lower().strip()
        if a_norm == b_norm:
            return 1.0
            
        synonyms = {
            "sentence transformers": "sentence-transformers",
            "sentence-transformers": "sentence-transformers",
            "nextjs": "next.js",
            "next.js": "next.js",
            "golang": "go",
            "k8s": "kubernetes",
            "vector database": "vector databases",
            "recommender systems": "recommendation systems",
            "recommendation engine": "recommendation systems"
        }
        a_norm = synonyms.get(a_norm, a_norm)
        b_norm = synonyms.get(b_norm, b_norm)
        if a_norm == b_norm:
            return 1.0
            
        # Word boundary match check
        if re.search(r"\b" + re.escape(a_norm) + r"\b", b_norm) or re.search(r"\b" + re.escape(b_norm) + r"\b", a_norm):
            return 1.0
            
        key = tuple(sorted([a_norm, b_norm]))
        return SEMANTIC_SIMILARITY_MAP.get(key, 0.0) # type: ignore

    def score_evidence_density(self, candidate: CandidateIntelligence, jd: JobDescription) -> Tuple[float, List[Dict[str, Any]]]:
        """Scans candidate profile text and summary for Verb + Tech + Impact patterns."""
        text = " ".join([
            candidate.summary,
            candidate.headline,
            " ".join([job.description for job in candidate.career_history]),
            " ".join([job.title for job in candidate.career_history])
        ])
        
        sentences = [s.strip() for s in re.split(r'[\.\n\r;]+', text) if len(s.strip()) > 10]
        
        verbs = {
            "built", "build", "developed", "develop", "implemented", "implement", "designed", "design",
            "serving", "served", "serve", "reduced", "reduce", "optimized", "optimize", "optimising", "optimizing",
            "deployed", "deploy", "owned", "own", "spearheaded", "spearhead", "mentored", "mentor",
            "architected", "architect", "scaled", "scale", "increased", "increase", "decreased", "decrease",
            "improved", "improve", "created", "create", "migrated", "migrate", "integrated", "integrate",
            "achieved", "achieve", "led", "lead"
        }
        
        tech_keywords = set()
        for req in jd.requirements:
            tech_keywords.add(req.lower().strip())
        for pref in jd.preferred_skills:
            tech_keywords.add(pref.lower().strip())
            
        tech_list = {
            "python", "faiss", "milvus", "pinecone", "qdrant", "chromadb", "vector", "embeddings",
            "sentence-transformers", "transformers", "bge", "minilm", "mpnet", "bert", "lora", "peft",
            "qlora", "bm25", "elasticsearch", "solr", "opensearch", "kubernetes", "k8s", "docker",
            "fastapi", "django", "flask", "pytorch", "tensorflow", "aws", "azure", "gcp", "sql", "nosql",
            "rag", "llm", "search", "retrieval", "pipeline", "bentoml", "distributed", "ab test", "a/b test"
        }
        tech_keywords.update(tech_list)
        
        evidence_score = 0.0
        snippets = []
        seen_sentences = set()
        
        for s in sentences:
            s_lower = s.lower()
            if s_lower in seen_sentences:
                continue
                
            words = re.findall(r"\b\w+\b", s_lower)
            matched_verbs = [w for w in words if w in verbs]
            
            matched_techs = []
            for tech in sorted(tech_keywords):
                if " " in tech:
                    if tech in s_lower:
                        matched_techs.append(tech)
                else:
                    if re.search(r"\b" + re.escape(tech) + r"\b", s_lower):
                        matched_techs.append(tech)
                        
            has_number = bool(re.search(r"\b\d+", s_lower))
            has_percentage = "%" in s_lower
            has_metric = bool(re.search(r"\b(million|million\+|billion|users|qps|ms|latency|accuracy|throughput|cost|reduction|improvement|scale)\b", s_lower))
            
            if matched_verbs and matched_techs:
                seen_sentences.add(s_lower)
                if has_number or has_percentage or has_metric:
                    evidence_score += 5.0
                    snippets.append({
                        "sentence": s,
                        "quality": "strong",
                        "verb": matched_verbs[0],
                        "tech": matched_techs[0],
                        "impact": "numerical/metric"
                    })
                else:
                    evidence_score += 2.0
                    snippets.append({
                        "sentence": s,
                        "quality": "medium",
                        "verb": matched_verbs[0],
                        "tech": matched_techs[0],
                        "impact": "none"
                    })
                    
        evidence_score = min(25.0, evidence_score)
        return evidence_score, snippets

    def calculate_confidence_score(self, candidate: CandidateIntelligence) -> Tuple[float, List[str]]:
        """Computes a Recruiter Confidence Score based on soft chronological and data anomalies."""
        confidence_score = 100.0
        confidence_penalties = []
        
        # Chronological Overlaps
        jobs_sorted = []
        for job in candidate.career_history:
            if job.start_date:
                try:
                    s_dt = datetime.strptime(job.start_date, "%Y-%m-%d")
                    e_dt = datetime.strptime(job.end_date, "%Y-%m-%d") if job.end_date else datetime(2026, 7, 2)
                    jobs_sorted.append((s_dt, e_dt, job.company))
                except ValueError:
                    pass
        jobs_sorted.sort(key=lambda x: x[0])
        has_overlap = False
        for i in range(len(jobs_sorted) - 1):
            s1, e1, c1 = jobs_sorted[i]
            s2, e2, c2 = jobs_sorted[i+1]
            if c1 != c2 and s2 < e1:
                overlap_days = (e1 - s2).days
                if overlap_days > 90:
                    has_overlap = True
                    break
        if has_overlap:
            confidence_score -= 15.0
            confidence_penalties.append("Chronological Overlaps: concurrent full-time jobs overlapping by > 3 months")
            
        # Promotions Anomaly
        if candidate.years_of_experience < 1.5:
            anomalous_roles = []
            for job in candidate.career_history:
                title_l = job.title.lower()
                if any(r in title_l for r in ["principal", "architect", "lead", "director", "chief", "cto", "vp"]):
                    anomalous_roles.append(job.title)
            if anomalous_roles:
                confidence_score -= 20.0
                confidence_penalties.append(f"Promotion Anomaly: role '{anomalous_roles[0]}' with < 1.5 years of total experience")

        # Job duration exceeds total experience
        total_job_years = sum(job.duration_months for job in candidate.career_history) / 12.0
        if total_job_years > candidate.years_of_experience + 5.0:
            confidence_score -= 20.0
            confidence_penalties.append(f"Job duration sum ({total_job_years:.1f} years) significantly exceeds total experience ({candidate.years_of_experience} years)")

        # Education timeline inconsistency
        edu_anomaly = False
        edu_sorted = []
        for edu in candidate.education:
            if edu.start_year and edu.end_year:
                if edu.end_year < edu.start_year:
                    edu_anomaly = True
                edu_sorted.append((edu.start_year, edu.end_year, edu.degree.lower()))
                
        edu_sorted.sort(key=lambda x: x[0])
        college_grad = None
        hs_grad = None
        for start, end, deg in edu_sorted:
            if "high school" in deg or "hsc" in deg or "matric" in deg:
                hs_grad = end
            elif "bachelor" in deg or "b.s" in deg or "b.e" in deg or "b.tech" in deg or "college" in deg:
                college_grad = end
        if hs_grad and college_grad and hs_grad > college_grad:
            edu_anomaly = True
        if edu_anomaly:
            confidence_score -= 20.0
            confidence_penalties.append("Education Timeline Anomaly: inconsistent high school / college graduation dates")

        # Unrealistic expert claim
        expert_count = 0
        for s in candidate.skills:
            if s.proficiency.lower() in ["expert", "advanced", "lead"]:
                expert_count += 1
        if expert_count > 15:
            confidence_score -= 15.0
            confidence_penalties.append(f"Unrealistic Skill Claims: expert/advanced proficiency in {expert_count} distinct technologies")

        # Suspicious endorsement inflation
        total_endorsements = candidate.behavioral_signals.endorsements_received
        if total_endorsements > 300 and (candidate.years_of_experience < 1.5 or candidate.behavioral_signals.connection_count < 15):
            confidence_score -= 15.0
            confidence_penalties.append(f"Suspicious Endorsement Inflation: {total_endorsements} endorsements with low experience/connections")

        # Technology Release Anomaly
        TECH_RELEASE_YEARS = {
            "fastapi": 2018,
            "pytorch": 2016,
            "langchain": 2022,
            "gpt-4": 2023,
            "gpt4": 2023,
            "llama": 2023,
            "transformers": 2017,
            "bert": 2018,
            "kubernetes": 2014,
            "faiss": 2017,
            "milvus": 2019,
            "pinecone": 2021,
            "qdrant": 2020,
            "copilot": 2021,
            "next.js": 2016,
            "nextjs": 2016
        }
        released_tech_anomaly = False
        for s in candidate.skills:
            s_clean = s.name.lower().strip()
            for tech, rel_year in TECH_RELEASE_YEARS.items():
                if re.search(r"\b" + re.escape(tech) + r"\b", s_clean):
                    claimed_years = (s.duration_months or 0) / 12.0
                    max_allowed = 2026 - rel_year + 0.5
                    if claimed_years > max_allowed:
                        released_tech_anomaly = True
                        break
        if released_tech_anomaly:
            confidence_score -= 30.0
            confidence_penalties.append("Technology Release Anomaly: technology usage duration exceeds release history")

        # Contradictory Ph.D. info
        headline_summary_phd = "phd" in candidate.headline.lower() or "ph.d" in candidate.headline.lower() or "phd" in candidate.summary.lower() or "ph.d" in candidate.summary.lower()
        has_phd_degree = False
        for edu in candidate.education:
            deg = edu.degree.lower()
            if "phd" in deg or "ph.d" in deg or "doctor" in deg:
                has_phd_degree = True
                break
        if headline_summary_phd and not has_phd_degree:
            confidence_score -= 15.0
            confidence_penalties.append("Contradictory Profile Information: PhD claimed in summary/headline but not listed in education")

        confidence_score = max(0.0, confidence_score)
        return confidence_score, confidence_penalties

    def evaluate_candidate(self, candidate: CandidateIntelligence, jd: JobDescription) -> Dict[str, Any]:
        """Evaluates sub-scores and aggregates them into a final score.

        If the candidate is flagged as a honeypot, returns final score = 0.0.
        """
        # Honeypot check
        if self.is_honeypot(candidate):
            return {
                "candidate_id": candidate.candidate_id,
                "name": candidate.name,
                "years_of_experience": candidate.years_of_experience,
                "location": candidate.location,
                "open_to_work": candidate.behavioral_signals.open_to_work_flag if candidate.behavioral_signals else False,
                "notice_period_days": candidate.notice_period,
                "skills": [s.name for s in candidate.skills] if candidate.skills else [],
                "current_title": candidate.current_title,
                "current_company": candidate.current_company,
                "is_honeypot": True,
                "skill_score": 0.0,
                "experience_score": 0.0,
                "behavior_score": 0.0,
                "final_score": 0.0,
                "skill_analysis": None,
                "scoring_breakdown": {
                    "final_score": 0.0,
                    "is_honeypot": True
                }
            }

        # Check evaluation cache
        cache_key = (jd.title, candidate.candidate_id)
        if cache_key in RankingEngine._evaluation_cache:
            return RankingEngine._evaluation_cache[cache_key]

        # Load embedding model lazily
        self.load_model()
        import numpy as np

        # Check cache for JD Title embedding
        if (RankingEngine._cached_jd_title == jd.title and 
            RankingEngine._cached_jd_title_emb is not None):
            jd_title_emb = RankingEngine._cached_jd_title_emb
        else:
            jd_title_emb = self._model.encode(jd.title, convert_to_numpy=True)
            jd_title_emb = jd_title_emb / np.linalg.norm(jd_title_emb)
            RankingEngine._cached_jd_title = jd.title
            RankingEngine._cached_jd_title_emb = jd_title_emb

        jd_text = " ".join([jd.title, jd.summary, " ".join(jd.requirements), " ".join(jd.preferred_skills)]).strip().lower()
        # Check cache for JD Text embedding
        if (RankingEngine._cached_jd_text == jd_text and 
            RankingEngine._cached_jd_emb is not None):
            jd_emb = RankingEngine._cached_jd_emb
        else:
            jd_emb = self._model.encode(jd_text, convert_to_numpy=True)
            jd_emb = jd_emb / np.linalg.norm(jd_emb)
            RankingEngine._cached_jd_text = jd_text
            RankingEngine._cached_jd_emb = jd_emb

        cand_emb = self._model.encode(candidate.profile_text, convert_to_numpy=True)
        cand_emb = cand_emb / np.linalg.norm(cand_emb)

        recent_roles = [candidate.current_title] + [job.title for job in candidate.career_history[:2] if job.title]
        role_embs = []
        for role in recent_roles:
            emb = self._model.encode(role, convert_to_numpy=True)
            role_embs.append(emb / np.linalg.norm(emb))

        res = self.evaluate_candidate_with_embeddings(candidate, jd, jd_title_emb, jd_emb, cand_emb, role_embs)
        RankingEngine._evaluation_cache[cache_key] = res
        return res

    def evaluate_candidate_with_embeddings(
        self,
        candidate: CandidateIntelligence,
        jd: JobDescription,
        jd_title_emb,
        jd_emb,
        cand_emb,
        role_embs,
        skill_rarity_map: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Evaluates sub-scores using precomputed embeddings."""
        cache_key = (jd.title, candidate.candidate_id)
        if cache_key in RankingEngine._evaluation_cache:
            return RankingEngine._evaluation_cache[cache_key]

        # Honeypot check
        if self.is_honeypot(candidate):
            res = {
                "candidate_id": candidate.candidate_id,
                "is_honeypot": True,
                "skill_score": 0.0,
                "experience_score": 0.0,
                "education_score": 0.0,
                "project_score": 0.0,
                "behavior_score": 0.0,
                "availability_score": 0.0,
                "final_score": 0.0,
                "skill_analysis": None,
                "scoring_breakdown": {
                    "final_score": 0.0,
                    "is_honeypot": True,
                    "skill_score": 0.0,
                    "experience_score": 0.0,
                    "education_score": 0.0,
                    "project_score": 0.0,
                    "behavior_score": 0.0,
                    "availability_score": 0.0,
                    "engagement_bonus": 0.0
                }
            }
            RankingEngine._evaluation_cache[cache_key] = res
            return res

        # Calculate Recruiter Confidence Score (Minor anomalies only penalize confidence)
        confidence_score, confidence_penalties = self.calculate_confidence_score(candidate)
        if confidence_score < 40.0:
            res = {
                "candidate_id": candidate.candidate_id,
                "is_honeypot": True,
                "skill_score": 0.0,
                "experience_score": 0.0,
                "education_score": 0.0,
                "project_score": 0.0,
                "behavior_score": 0.0,
                "availability_score": 0.0,
                "final_score": 0.0,
                "skill_analysis": None,
                "scoring_breakdown": {
                    "final_score": 0.0,
                    "is_honeypot": True,
                    "skill_score": 0.0,
                    "experience_score": 0.0,
                    "education_score": 0.0,
                    "project_score": 0.0,
                    "behavior_score": 0.0,
                    "availability_score": 0.0,
                    "engagement_bonus": 0.0
                }
            }
            RankingEngine._evaluation_cache[cache_key] = res
            return res

        # 1. Skill Match (40 pts)
        analysis = self.skill_engine.analyze(candidate, jd)
        skill_rarity_map = skill_rarity_map or {}

        # Core required skills (first 2 requirements)
        critical_reqs = jd.requirements[:2]
        has_critical_1 = False
        has_critical_2 = False

        raw_skill_score = 0.0
        max_possible_raw_skill = 0.0

        # Build list of skills with importance weights (FIX 5)
        skills_to_eval = []
        for idx, r in enumerate(jd.requirements):
            is_crit = (idx < 2)
            w = 1.0 if is_crit else 0.8
            skills_to_eval.append((r, w, is_crit))
        for p in jd.preferred_skills:
            if p.lower() != "none specified":
                skills_to_eval.append((p, 0.4, False))

        critical_matched = []
        important_matched = []
        matched_pref = []
        missing_critical = []

        for req, weight, is_crit in skills_to_eval:
            cls, reason, best_cand_skill = self.skill_evaluator.classify(req, candidate)

            # If conversational/prose requirement failed direct coverage, evaluate constituent atomic skills
            if cls in ("NONE", "RELATED") and getattr(jd, "technical_skills", None):
                constituents = self._get_constituent_technical_skills(req, jd.technical_skills)
                matched_constituents = []
                for t_skill in constituents:
                    t_cls, t_reason, t_cand_skill = self.skill_evaluator.classify(t_skill, candidate)
                    if t_cls in ("DIRECT", "EQUIVALENT"):
                        matched_constituents.append((t_skill, t_cls, t_reason, t_cand_skill))
                
                if matched_constituents:
                    best_match = max(
                        matched_constituents,
                        key=lambda item: (
                            1.2 if item[3] and "expert" in getattr(item[3], "proficiency", "").lower() else (
                                1.1 if item[3] and ("advanced" in getattr(item[3], "proficiency", "").lower() or "lead" in getattr(item[3], "proficiency", "").lower()) else 1.0
                            ),
                            getattr(item[3], "duration_months", 0) or 0
                        )
                    )
                    t_skill, cls, t_reason, best_cand_skill = best_match
                    reason = f"Matched via constituent skill '{t_skill}': {t_reason}"
                elif cls == "NONE":
                    for t_skill in constituents:
                        t_cls, t_reason, t_cand_skill = self.skill_evaluator.classify(t_skill, candidate)
                        if t_cls == "SUPPORTED":
                            cls = "SUPPORTED"
                            reason = f"Supported via constituent skill '{t_skill}': {t_reason}"
                            best_cand_skill = t_cand_skill
                            break

            max_possible_raw_skill += 10.0 * weight

            if cls in ("DIRECT", "EQUIVALENT"):
                if is_crit:
                    if len(critical_reqs) > 0 and req == critical_reqs[0]:
                        has_critical_1 = True
                    elif len(critical_reqs) > 1 and req == critical_reqs[1]:
                        has_critical_2 = True
                    critical_matched.append(req)
                elif weight >= 0.8:
                    important_matched.append(req)
                else:
                    matched_pref.append(req)

                prof_val = (best_cand_skill.proficiency.lower() if best_cand_skill and hasattr(best_cand_skill, 'proficiency') else "intermediate")
                prof_mult = 1.2 if "expert" in prof_val else (1.1 if "advanced" in prof_val or "lead" in prof_val else (1.0 if "intermediate" in prof_val else 0.7))
                dur_y = ((best_cand_skill.duration_months or 0) / 12.0 if best_cand_skill and hasattr(best_cand_skill, 'duration_months') else 3.0)
                dur_mult = 1.0 if dur_y >= 3.0 else (0.9 if dur_y >= 1.0 else (0.8 if dur_y > 0.0 else 0.7))

                recent_use = False
                if candidate.career_history:
                    recent_job = candidate.career_history[0]
                    skill_name_check = getattr(best_cand_skill, 'name', '').lower() if best_cand_skill else ''
                    if (req.lower() in recent_job.description.lower() or req.lower() in recent_job.title.lower() or
                        (skill_name_check and (skill_name_check in recent_job.description.lower() or skill_name_check in recent_job.title.lower()))):
                        recent_use = True
                recency_mult = 1.2 if recent_use else 1.0
                rarity = skill_rarity_map.get(req.lower().strip(), 1.0)

                contrib = (1.0 * prof_mult * dur_mult * recency_mult * 10.0 * weight * rarity)
                raw_skill_score += contrib

            elif cls == "SUPPORTED":
                rarity = skill_rarity_map.get(req.lower().strip(), 1.0)
                contrib = (0.50 * 10.0 * weight * rarity)
                raw_skill_score += contrib
                if is_crit:
                    missing_critical.append(req)
                elif weight >= 0.8:
                    important_matched.append(req)
                else:
                    matched_pref.append(req)
            else: # RELATED or NONE
                if is_crit:
                    missing_critical.append(req)
                    raw_skill_score -= 3.0 * skill_rarity_map.get(req.lower().strip(), 1.0)

        # JD Mandatory filter: Lacks BOTH of the top 2 critical skills
        mandatory_penalty = 0.0
        if len(critical_reqs) >= 2 and (not has_critical_1 and not has_critical_2):
            mandatory_penalty = 20.0

        if max_possible_raw_skill > 0:
            skill_score = 40.0 * (raw_skill_score / max_possible_raw_skill)
        else:
            skill_score = 0.0
        skill_score = max(0.0, min(40.0, skill_score - mandatory_penalty))

        # 2. Experience Match (25 pts)
        exp_req = jd.experience_requirement
        total_exp = candidate.years_of_experience
        exp_pts = 8.0
        if exp_req.min_years is not None and total_exp < exp_req.min_years:
            exp_pts = max(0.0, 8.0 * (total_exp / exp_req.min_years))

        # Semantic title & description similarity
        import numpy as np
        cand_jd_sim = float(np.dot(jd_emb, cand_emb)) if cand_emb is not None else 0.5
        title_resp_score = max(0.0, min(7.0, 7.0 * (cand_jd_sim - 0.2) / 0.7))

        # Optional Company Quality bonus (+0.75 pts max)
        company_bonus = 0.0
        hq_companies = ["google", "openai", "microsoft", "nvidia", "scale ai"]
        for job in candidate.career_history:
            if any(hq in job.company.lower() for hq in hq_companies):
                company_bonus = 0.75
                break

        # Leadership & Scale
        leadership_score = 0.0
        lead_keywords = ["senior", "lead", "principal", "staff", "cto", "vp", "director", "manager", "architect"]
        if any(any(k in job.title.lower() for k in lead_keywords) for job in candidate.career_history):
            leadership_score += 2.0

        scale_keywords = ["scale", "production", "latency", "deploy", "served", "optimize", "ab test", "a/b test"]
        scale_found = 0
        desc_text = " ".join([job.description for job in candidate.career_history]).lower()
        for k in scale_keywords:
            if k in desc_text:
                scale_found += 1
        leadership_score += min(5.0, scale_found * 1.0)

        # Role similarity (max 3 pts)
        role_sims = []
        if role_embs is not None:
            for role_emb in role_embs:
                role_sims.append(float(np.dot(jd_title_emb, role_emb)))
        max_role_sim = max(role_sims) if role_sims else 0.0
        industry_score = max(0.0, min(3.0, 3.0 * max_role_sim))

        experience_score = exp_pts + title_resp_score + company_bonus + leadership_score + industry_score
        experience_score = max(0.0, min(25.0, experience_score))

        # 3. Education Score (10 pts)
        edu_relevance = 4.0
        for edu in candidate.education:
            field = edu.field_of_study.lower()
            if any(k in field for k in ["computer science", "artificial intelligence", "ai", "data science", "mathematics", "statistics", "electronics", "machine learning"]):
                edu_relevance = 8.0
                break
            elif any(k in field for k in ["engineering", "information technology", "information systems", "software engineering"]):
                edu_relevance = 6.0

        deg_bonus = 0.0
        for edu in candidate.education:
            deg = edu.degree.lower()
            if any(k in deg for k in ["phd", "ph.d", "doctor"]):
                deg_bonus = max(deg_bonus, 2.0)
            elif any(k in deg for k in ["master", "m.s", "m.tech", "mba", "m.e"]):
                deg_bonus = max(deg_bonus, 1.0)

        education_score = min(10.0, edu_relevance + deg_bonus)

        # 4. Projects & Responsibilities Score (10 pts)
        evidence_density_score, snippets = self.score_evidence_density(candidate, jd)
        project_score = min(10.0, evidence_density_score)

        # 5. Behaviour Signals Score (10 pts)
        signals = candidate.behavioral_signals
        profile_completeness = 2.0 * (signals.profile_completeness_score / 100.0)
        response_rate = 2.0 * signals.recruiter_response_rate
        interview_rate = 2.0 * signals.interview_completion_rate
        connections_endorsements = min(2.0, (signals.connection_count / 1000.0) + (signals.endorsements_received / 100.0))
        
        verified_flags = 0
        if signals.verified_email:
            verified_flags += 1
        if signals.verified_phone:
            verified_flags += 1
        if signals.linkedin_connected:
            verified_flags += 1
        verified_score = 2.0 * (verified_flags / 3.0)

        behavior_score = max(0.0, min(10.0, profile_completeness + response_rate + interview_rate + connections_endorsements + verified_score))

        # 6. Availability Score (5 pts)
        notice_days = signals.notice_period_days
        if notice_days == 0 or signals.open_to_work_flag:
            avail_pts = 4.0
        elif notice_days <= 15:
            avail_pts = 3.5
        elif notice_days <= 30:
            avail_pts = 3.0
        elif notice_days <= 60:
            avail_pts = 2.0
        elif notice_days <= 90:
            avail_pts = 1.0
        else:
            avail_pts = 0.5
            
        open_bonus = 1.0 if signals.open_to_work_flag else 0.0
        availability_score = min(5.0, avail_pts + open_bonus)

        # Base Sum
        overall_score = skill_score + experience_score + education_score + project_score + behavior_score + availability_score

        # Capped Modifiers (adjust score without rescuing weak profiles)
        modifier = 0.0
        if signals.profile_completeness_score > 85 and signals.recruiter_response_rate > 0.8:
            modifier += 0.03
        elif signals.profile_completeness_score < 50 or signals.recruiter_response_rate < 0.4:
            modifier -= 0.05
            
        try:
            active_dt = datetime.strptime(signals.last_active_date, "%Y-%m-%d")
            if active_dt.year < 2026:
                modifier -= 0.03
        except ValueError:
            pass
            
        if signals.open_to_work_flag:
            modifier += 0.02
        if signals.notice_period_days >= 90:
            modifier -= 0.01

        # Restore original global modifier application
        final_score = overall_score * (1.0 + modifier)
        final_score = round(max(0.0, min(100.0, final_score)), 4)
        engagement_bonus = round(final_score - overall_score, 4)

        scoring_breakdown = {
            "critical_skills_matched": critical_matched,
            "important_skills_matched": important_matched,
            "nice_to_have_skills_matched": matched_pref,
            "missing_critical_skills": missing_critical,
            "skill_score": round(skill_score, 4),
            "experience_score": round(experience_score, 4),
            "education_score": round(education_score, 4),
            "project_score": round(project_score, 4),
            "behavior_score": round(behavior_score, 4),
            "availability_score": round(availability_score, 4),
            "engagement_bonus": engagement_bonus,
            "final_score": final_score,
            "evidence_snippets": snippets,
            "confidence_score": round(confidence_score, 4),
            "confidence_penalties": confidence_penalties,
            "is_honeypot": False
        }

        res = {
            "candidate_id": candidate.candidate_id,
            "name": candidate.name,
            "years_of_experience": candidate.years_of_experience,
            "location": candidate.location,
            "open_to_work": candidate.behavioral_signals.open_to_work_flag if candidate.behavioral_signals else False,
            "notice_period_days": candidate.notice_period,
            "skills": [s.name for s in candidate.skills] if candidate.skills else [],
            "current_title": candidate.current_title,
            "current_company": candidate.current_company,
            "is_honeypot": False,
            "skill_score": round(skill_score, 4),
            "experience_score": round(experience_score, 4),
            "education_score": round(education_score, 4),
            "project_score": round(project_score, 4),
            "behavior_score": round(behavior_score, 4),
            "availability_score": round(availability_score, 4),
            "engagement_bonus": engagement_bonus,
            "final_score": round(final_score, 4),
            "skill_analysis": analysis,
            "scoring_breakdown": scoring_breakdown
        }
        RankingEngine._evaluation_cache[cache_key] = res
        return res

    def rank_cohort(self, candidates: List[CandidateIntelligence], jd: JobDescription) -> List[Dict[str, Any]]:
        """Evaluates and ranks a cohort of candidate profiles.

        Returns ranked records sorted by final score descending (with tie-break on behavior_score descending and candidate_id ascending).
        """
        self.load_model()
        import numpy as np

        # 1. Compute dynamic skill rarity map over the cohort
        skill_rarity_map = {}
        total_cand = len(candidates)
        if total_cand > 0:
            cohort_skill_counts = {}
            for c in candidates:
                for skill in c.skills:
                    s_name = skill.name.lower().strip()
                    cohort_skill_counts[s_name] = cohort_skill_counts.get(s_name, 0) + 1
            for s_name, count in cohort_skill_counts.items():
                rarity_val = 1.0 + (1.0 - (count / total_cand))
                skill_rarity_map[s_name] = max(1.0, min(2.0, rarity_val))

        # 2. Pre-encode JD title and JD text
        jd_title_emb = self._model.encode(jd.title, convert_to_numpy=True)
        jd_title_emb = jd_title_emb / np.linalg.norm(jd_title_emb)
        
        jd_text = " ".join([jd.title, jd.summary, " ".join(jd.requirements), " ".join(jd.preferred_skills)]).strip().lower()
        jd_emb = self._model.encode(jd_text, convert_to_numpy=True)
        jd_emb = jd_emb / np.linalg.norm(jd_emb)

        # 3. Collect texts to encode
        profile_texts = [c.profile_text for c in candidates]
        
        candidate_roles_indices = []
        all_roles = []
        for c in candidates:
            roles = [c.current_title] + [job.title for job in c.career_history[:2] if job.title]
            start_idx = len(all_roles)
            all_roles.extend(roles)
            end_idx = len(all_roles)
            candidate_roles_indices.append((start_idx, end_idx))

        # 4. Batch encode
        profile_embs = []
        if profile_texts:
            raw_embs = self._model.encode(profile_texts, batch_size=64, show_progress_bar=False, convert_to_numpy=True)
            for emb in raw_embs:
                norm = np.linalg.norm(emb)
                profile_embs.append(emb / norm if norm > 0 else emb)
                
        role_embs = []
        if all_roles:
            raw_embs = self._model.encode(all_roles, batch_size=64, show_progress_bar=False, convert_to_numpy=True)
            for emb in raw_embs:
                norm = np.linalg.norm(emb)
                role_embs.append(emb / norm if norm > 0 else emb)

        # 5. Map back and evaluate candidates
        evaluated = []
        for idx, c in enumerate(candidates):
            c_profile_emb = profile_embs[idx] if idx < len(profile_embs) else None
            role_range = candidate_roles_indices[idx]
            c_role_embs = role_embs[role_range[0]:role_range[1]] if role_range[0] < len(role_embs) else []
            
            evaluated.append(
                self.evaluate_candidate_with_embeddings(
                    c, jd, jd_title_emb, jd_emb, c_profile_emb, c_role_embs, skill_rarity_map
                )
            )
        
        # Sort key: final_score descending, behavior_score descending, candidate_id ascending (FIX 15)
        sorted_cohort = sorted(
            evaluated,
            key=lambda x: (-x["final_score"], -x["scoring_breakdown"]["behavior_score"], x["candidate_id"])
        )

        # 6. Apply Recruiter deduplication Sanity Post-Pass (FIX 16)
        top_100 = sorted_cohort[:100]
        rest = sorted_cohort[100:]
        seen_resumes = set()
        cleaned_top_100 = []
        for record in top_100:
            candidate = next((c for c in candidates if c.candidate_id == record["candidate_id"]), None)
            if not candidate:
                cleaned_top_100.append(record)
                continue
            sig = (candidate.name.lower().strip(), candidate.years_of_experience, candidate.current_title.lower().strip())
            if sig in seen_resumes:
                logger.warning(f"Sanity pass: Duplicate profile detected and penalized: {record['candidate_id']}")
                record["final_score"] = round(record["final_score"] * 0.1, 4)
                record["scoring_breakdown"]["final_score"] = record["final_score"]
                record["scoring_breakdown"]["duplicate_anomaly"] = True
                rest.append(record)
            else:
                seen_resumes.add(sig)
                cleaned_top_100.append(record)
                
        all_records = cleaned_top_100 + rest
        sorted_cohort = sorted(
            all_records,
            key=lambda x: (-x["final_score"], -x["scoring_breakdown"]["behavior_score"], x["candidate_id"])
        )
        
        return sorted_cohort
