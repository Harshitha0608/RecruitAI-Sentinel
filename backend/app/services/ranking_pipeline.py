import logging
import time
import json
import re
import math
from pathlib import Path
from collections import Counter
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

from backend.app.config.settings import settings
from backend.app.services.jd_parser import JDParser
from backend.app.services.dataset_loader import DatasetLoader
from backend.app.services.candidate_intelligence_builder import CandidateIntelligenceBuilder
from backend.app.retrieval.retrieval_engine import RetrievalEngine
from backend.app.ranking.ranking_engine import RankingEngine
from backend.app.explainability.explainability_engine import ExplainabilityEngine
from backend.app.services.submission_engine import SubmissionEngine
from backend.app.schemas.candidate_intelligence import CandidateIntelligence
from backend.app.schemas.job_description import JobDescription

logger = logging.getLogger("app.services.ranking_pipeline")

def report_progress(stage: str, percentage: int, status_message: str) -> None:
    """Writes the current progress state to a JSON file for frontend polling (FIX 9)."""
    progress_path = Path(settings.CANDIDATE_IDS_PATH).parent / "screening_progress.json"
    try:
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump({
                "stage": stage,
                "percentage": percentage,
                "status_message": status_message,
                "completed": percentage >= 100 or stage.lower() == "complete"
            }, f)
    except Exception as e:
        logger.warning(f"Failed to write screening progress: {e}")

class BM25Scorer:
    """Fast in-memory BM25Okapi implementation (FIX 10)."""
    def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.avg_doc_len = sum(len(doc) for doc in corpus) / self.corpus_size if self.corpus_size > 0 else 1.0
        
        self.doc_freqs = {}
        for doc in corpus:
            for term in set(doc):
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1
        
        self.idf = {}
        for term, freq in self.doc_freqs.items():
            self.idf[term] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)

    def score(self, doc: List[str], query: List[str]) -> float:
        score = 0.0
        doc_len = len(doc)
        term_counts = Counter(doc)
        for term in query:
            if term in self.idf:
                tf = term_counts[term]
                num = tf * (self.k1 + 1)
                den = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += self.idf[term] * (num / den)
        return score

def get_candidate_words(intel: CandidateIntelligence) -> List[str]:
    """Combines candidate title, headline, summary, and skills for tokenization."""
    text = " ".join([
        intel.current_title,
        intel.headline,
        intel.summary,
        " ".join([s.name for s in intel.skills])
    ]).lower()
    return re.findall(r"\b[a-z0-9\.\-/]+\b", text)

class RankingPipeline:
    """The complete integrated AI Ranking Pipeline coordinating candidate ranking and submission."""

    def __init__(
        self,
        jd_parser: Optional[JDParser] = None,
        dataset_loader: Optional[DatasetLoader] = None,
        intelligence_builder: Optional[CandidateIntelligenceBuilder] = None,
        retrieval_engine: Optional[RetrievalEngine] = None,
        ranking_engine: Optional[RankingEngine] = None,
        explainability_engine: Optional[ExplainabilityEngine] = None,
        submission_engine: Optional[SubmissionEngine] = None
    ) -> None:
        self.jd_parser = jd_parser or JDParser()
        self.dataset_loader = dataset_loader or DatasetLoader()
        self.intelligence_builder = intelligence_builder or CandidateIntelligenceBuilder()
        self.retrieval_engine = retrieval_engine or RetrievalEngine()
        self.ranking_engine = ranking_engine or RankingEngine()
        self.explainability_engine = explainability_engine or ExplainabilityEngine()
        self.submission_engine = submission_engine or SubmissionEngine()

    def run(self, jd_path: str, output_csv_path: str) -> Dict[str, Any]:
        """Runs the entire multi-stage pipeline end-to-end and writes the submission CSV."""
        logger.info("Starting complete AI Ranking Pipeline run...")
        start_time = time.time()

        # Limit CPU threads to keep health check responsive (FIX 12)
        try:
            import torch
            import faiss
            torch.set_num_threads(2)
            faiss.omp_set_num_threads(2)
        except Exception as e:
            logger.warning(f"Could not limit CPU threads: {e}")

        # 1. Preparing Job (0%)
        report_progress("Preparing Job", 0, "Initializing workspace and loaders...")
        
        # 2. Parse Job Description (20%)
        report_progress("Understanding Requirements", 20, "Parsing requirements from uploaded Job Description...")
        jd = self.jd_parser.parse_jd(jd_path)
        logger.info(f"Job Description parsed: {jd.title} ({jd.company})")

        # 3. Stage 1 (100k -> 8000) using fast sparse TF-IDF keyword query matching (40%)
        report_progress("Searching Candidate Pool", 40, "Filtering candidate database via hybrid search...")
        retrieval_start = time.time()
        top_8000_ids = self.retrieval_engine.retrieve_top_8000_tfidf(jd)
        retrieval_time = time.time() - retrieval_start
        logger.info(f"Retrieved top {len(top_8000_ids)} candidates via TF-IDF in {retrieval_time:.2f}s")
        
        # 4. Stage 2 (8000 -> 1000) using custom BM25 Scorer (45%)
        report_progress("Searching Candidate Pool", 45, "Ranking candidates via keyword density...")
        bm25_start = time.time()
        
        # Load profile data via seek offsets for the 8000 candidates
        cohort_8000 = []
        total_top = len(top_8000_ids)
        for idx, cid in enumerate(top_8000_ids, start=1):
            raw_cand = self.dataset_loader.load_candidate_by_id(cid)
            if raw_cand:
                intel = self.intelligence_builder.build_intelligence(raw_cand)
                cohort_8000.append(intel)
            
            if idx % 1000 == 0 or idx == total_top:
                pct = 40 + int((idx / max(1, total_top)) * 10)
                report_progress("Searching Candidate Pool", pct, f"Screened {idx:,} / {total_top:,} candidate profiles...")
                
        # Scrypt tokenized query keywords
        query_words = [k.lower() for k in jd.keywords]
        corpus_words = [get_candidate_words(intel) for intel in cohort_8000]
        
        bm25 = BM25Scorer(corpus_words)
        scored_candidates = []
        for idx, intel in enumerate(cohort_8000):
            score = bm25.score(corpus_words[idx], query_words)
            scored_candidates.append((score, intel))
            
        # Stable sort tie-breaker (FIX 15)
        scored_candidates.sort(key=lambda x: (-x[0], x[1].candidate_id))
        cohort_1000 = [intel for _, intel in scored_candidates[:1000]]
        bm25_time = time.time() - bm25_start
        logger.info(f"BM25 filtered down to {len(cohort_1000)} candidates in {bm25_time:.2f}s")
        
        # 5. Stage 3 (1000 -> 300) using batch-encoded Dense Embedding Similarity (55%)
        report_progress("Matching Skills", 55, "Calculating semantic alignment using neural embeddings...")
        semantic_start = time.time()
        self.ranking_engine.load_model()
        model = self.ranking_engine._model
        
        jd_text = " ".join([jd.title, jd.summary, " ".join(jd.requirements), " ".join(jd.preferred_skills)]).strip().lower()
        jd_emb = model.encode(jd_text, convert_to_numpy=True)
        jd_emb = jd_emb / np.linalg.norm(jd_emb)
        
        profile_texts = [intel.profile_text for intel in cohort_1000]
        raw_embs = model.encode(profile_texts, batch_size=128, show_progress_bar=False, convert_to_numpy=True)
        
        candidates_with_sim = []
        for idx, intel in enumerate(cohort_1000):
            emb = raw_embs[idx]
            norm = np.linalg.norm(emb)
            emb_norm = emb / norm if norm > 0 else emb
            sim = float(np.dot(jd_emb, emb_norm))
            candidates_with_sim.append((sim, intel, emb_norm))
            
        candidates_with_sim.sort(key=lambda x: (-x[0], x[1].candidate_id))
        cohort_300 = [item[1] for item in candidates_with_sim[:300]]
        cohort_embs_300 = [item[2] for item in candidates_with_sim[:300]]
        semantic_time = time.time() - semantic_start
        logger.info(f"Dense semantic match filtered down to {len(cohort_300)} candidates in {semantic_time:.2f}s")
        
        # 6. Stage 4 (300 -> 100) using scoring engine adjustments (70%)
        report_progress("Behaviour Analysis", 70, "Applying behavioral and availability filters...")
        scoring_start = time.time()
        
        jd_title_emb = model.encode(jd.title, convert_to_numpy=True)
        jd_title_emb = jd_title_emb / np.linalg.norm(jd_title_emb)
        
        all_roles = []
        candidate_roles_indices = []
        for intel in cohort_300:
            roles = [intel.current_title] + [job.title for job in intel.career_history[:2] if job.title]
            start_idx = len(all_roles)
            all_roles.extend(roles)
            end_idx = len(all_roles)
            candidate_roles_indices.append((start_idx, end_idx))
            
        role_embs = []
        if all_roles:
            raw_role_embs = model.encode(all_roles, batch_size=128, show_progress_bar=False, convert_to_numpy=True)
            for emb in raw_role_embs:
                norm = np.linalg.norm(emb)
                role_embs.append(emb / norm if norm > 0 else emb)
                
        # Calculate skill rarity over the cohort
        skill_rarity_map = {}
        total_cand = len(cohort_300)
        if total_cand > 0:
            cohort_skill_counts = {}
            for intel in cohort_300:
                for skill in intel.skills:
                    s_name = skill.name.lower().strip()
                    cohort_skill_counts[s_name] = cohort_skill_counts.get(s_name, 0) + 1
            for s_name, count in cohort_skill_counts.items():
                rarity_val = 1.0 + (1.0 - (count / total_cand))
                skill_rarity_map[s_name] = max(1.0, min(2.0, rarity_val))
                
        evaluated = []
        for idx, intel in enumerate(cohort_300):
            c_profile_emb = cohort_embs_300[idx]
            role_range = candidate_roles_indices[idx]
            c_role_embs = role_embs[role_range[0]:role_range[1]] if role_range[0] < len(role_embs) else []
            
            evaluation = self.ranking_engine.evaluate_candidate_with_embeddings(
                intel, jd, jd_title_emb, jd_emb, c_profile_emb, c_role_embs, skill_rarity_map
            )
            evaluated.append(evaluation)
            
        # Initial tie-break sort
        sorted_cohort = sorted(
            evaluated,
            key=lambda x: (-x["final_score"], -x["scoring_breakdown"]["behavior_score"], x["candidate_id"])
        )

        # Apply Recruiter deduplication Sanity Post-Pass
        top_100 = sorted_cohort[:100]
        rest = sorted_cohort[100:]
        seen_resumes = set()
        cleaned_top_100 = []
        for record in top_100:
            candidate = next((c for c in cohort_300 if c.candidate_id == record["candidate_id"]), None)
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
        ranked_cohort = sorted(
            all_records,
            key=lambda x: (-x["final_score"], -x["scoring_breakdown"]["behavior_score"], x["candidate_id"])
        )
        
        non_honeypots = [c for c in ranked_cohort if not c["is_honeypot"]]
        honeypot_count = len(ranked_cohort) - len(non_honeypots)
        scoring_time = time.time() - scoring_start
        logger.info(f"Cohort scoring completed in {scoring_time:.2f}s. Honeypots excluded: {honeypot_count}")
 
        # 7. Generate Factual Explanations for Top 100 (85% and 95%)
        report_progress("Final Ranking", 85, "Sorting and selecting top ranked candidates...")
        report_progress("Preparing Results", 95, "Generating candidate recommendation reports...")
        
        top_100_records = ranked_cohort[:100]
        top_100_ids = [r["candidate_id"] for r in top_100_records]
        top_100_set = set(top_100_ids)
        
        top_100_profiles = [p for p in cohort_300 if p.candidate_id in top_100_set]
        explanations = self.explainability_engine.explain_cohort(top_100_profiles, top_100_records, jd)
 
        # 8. Generate Submission CSV (100%)
        report_progress("Completed", 100, "Vetting process completed successfully.")
        self.submission_engine.generate_submission(ranked_cohort, explanations, output_csv_path)

        # Validate
        challenge_root = settings.CHALLENGE_ROOT
        validation_script = str(Path(challenge_root) / "validate_submission.py") if challenge_root else ""
        valid, validation_errors = self.submission_engine.validate_submission_file(validation_script, output_csv_path)
        
        total_time = time.time() - start_time
        logger.info(f"Ranking Pipeline execution completed in {total_time:.2f} seconds.")
        
        run_data = {
            "success": valid,
            "validation_errors": validation_errors,
            "total_execution_time_seconds": round(total_time, 2),
            "retrieval_time_seconds": round(retrieval_time, 2),
            "streaming_time_seconds": round(bm25_time, 2),
            "ranking_time_seconds": round(scoring_time, 2),
            "explain_time_seconds": 0.0,
            "honeypots_detected_in_cohort": honeypot_count,
            "cohort_size": len(ranked_cohort),
            "top_100_average_score": round(sum(r["final_score"] for r in top_100_records) / 100.0, 4) if top_100_records else 0.0
        }
        
        try:
            metrics_path = Path(settings.CANDIDATE_IDS_PATH).parent / "run_metrics.json"
            with open(metrics_path, "w", encoding="utf-8") as f:
                json.dump(run_data, f)
        except Exception as e:
            logger.warning(f"Failed to write run metrics to file: {e}")
            
        return run_data
