import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
import logging
import json
import pickle
import threading
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import csr_matrix
from sentence_transformers import SentenceTransformer
import faiss

import numpy as np

from backend.app.config.settings import settings
from backend.app.schemas.job_description import JobDescription

logger = logging.getLogger("app.retrieval.retrieval_engine")

class RetrievalEngine:
    """Retrieval Engine performing hybrid search combining TF-IDF and FAISS vector similarity."""
    
    _instance = None
    _singleton_lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(RetrievalEngine, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self.model_name = "all-MiniLM-L6-v2"
        self._model: Optional[SentenceTransformer] = None
        self._faiss_index: Optional[faiss.IndexFlatIP] = None
        self._candidate_ids: Optional[List[str]] = None
        self._tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self._tfidf_matrix: Optional[csr_matrix] = None
        
        self._lock = threading.Lock()
        self.loaded = False
        self._initialized = True

    def load_indexes(self) -> None:
        """Loads indexes and models into memory if not already loaded."""
        if (
            self.loaded
            and self._tfidf_vectorizer is not None
            and self._faiss_index is not None
            and self._candidate_ids is not None
            and self._model is not None
        ):
            return
            
        with self._lock:
            if (
                self.loaded
                and self._tfidf_vectorizer is not None
                and self._faiss_index is not None
                and self._candidate_ids is not None
                and self._model is not None
            ):
                return
                
            logger.info("Loading retrieval engine models and indexes...")
        
            # Load candidate IDs mapping
            ids_path = Path(settings.CANDIDATE_IDS_PATH)
            if not ids_path.exists():
                raise FileNotFoundError(f"Candidate IDs file not found at {ids_path}. Run precompute.py first.")
            with open(ids_path, "r", encoding="utf-8") as f:
                self._candidate_ids = json.load(f)
                
            # Load FAISS index
            faiss_path = Path(settings.VECTOR_INDEX_PATH)
            if not faiss_path.exists():
                raise FileNotFoundError(f"FAISS index file not found at {faiss_path}. Run precompute.py first.")
            self._faiss_index = faiss.read_index(str(faiss_path))
            
            # Load TF-IDF index
            tfidf_path = Path(settings.TFIDF_PATH)
            if not tfidf_path.exists():
                raise FileNotFoundError(f"TF-IDF index file not found at {tfidf_path}. Run precompute.py first.")
            with open(tfidf_path, "rb") as f:
                data = pickle.load(f)
                if not isinstance(data, dict) or "vectorizer" not in data or "matrix" not in data:
                    raise ValueError(
                        f"TF-IDF pickle at {tfidf_path} is invalid or has wrong format. "
                        "Please run precompute.py to re-generate."
                    )
                self._tfidf_vectorizer = data["vectorizer"]
                self._tfidf_matrix = data["matrix"]
                
            if self._tfidf_vectorizer is None or self._tfidf_matrix is None:
                raise ValueError(
                    f"TF-IDF index file at {tfidf_path} has missing vectorizer or matrix. "
                    "Please run precompute.py to re-generate."
                )
                
            # Load SentenceTransformer model
            logger.info("Loading SentenceTransformer model...")
            self._model = SentenceTransformer(self.model_name)
            
            # Post-load validation checks
            if self._candidate_ids is None:
                raise ValueError(
                    f"Candidate IDs file at {ids_path} did not load properly (returned None). "
                    "Please ensure the file is valid or run precompute.py to re-generate."
                )
            if self._faiss_index is None:
                raise ValueError(
                    f"FAISS index at {faiss_path} did not load properly (returned None). "
                    "Please ensure the file is valid or run precompute.py to re-generate."
                )
            if self._model is None:
                raise ValueError(
                    "SentenceTransformer model could not be initialized."
                )
            
            self.loaded = True
            logger.info(
                "Retrieval engine models and indexes loaded successfully",
                extra={
                    "candidate_count": len(self._candidate_ids),
                    "faiss_dimension": self._faiss_index.d
                }
            )

    def _get_query_text(self, jd: JobDescription) -> str:
        """Combines job description fields into a unified query string."""
        parts = [
            jd.title,
            jd.summary,
            " ".join(jd.requirements),
            " ".join(jd.preferred_skills)
        ]
        return " ".join([p for p in parts if p]).strip().lower()

    def retrieve(self, jd: JobDescription, limit: int = 1000) -> List[str]:
        """Performs hybrid retrieval using TF-IDF and FAISS with RRF to select the top candidate IDs.

        Args:
            jd: JobDescription model.
            limit: Maximum candidate IDs to return.

        Returns:
            Sorted list of Top candidate IDs.
        """
        self.load_indexes()
        
        # Validation checks to narrow types for Pyrefly and guarantee runtime loaded state
        if self._tfidf_vectorizer is None:
            raise RuntimeError("TF-IDF vectorizer failed to load.")
        if self._tfidf_matrix is None:
            raise RuntimeError("TF-IDF matrix failed to load.")
        if self._faiss_index is None:
            raise RuntimeError("FAISS index failed to load.")
        if self._candidate_ids is None:
            raise RuntimeError("Candidate IDs failed to load.")
        if self._model is None:
            raise RuntimeError("SentenceTransformer model failed to load.")
        
        query_text = self._get_query_text(jd)
        logger.info("Searching query text", extra={"query_text": query_text})
        
        # 1. TF-IDF Search
        tfidf_vector = self._tfidf_vectorizer.transform([query_text])
        if not isinstance(tfidf_vector, csr_matrix):
            raise RuntimeError("Expected csr_matrix from TfidfVectorizer")
        # Compute cosine similarity
        tfidf_scores = (self._tfidf_matrix * tfidf_vector.transpose()).toarray().flatten()
        # Stable sort: tie-break by index ascending, primary sort by score descending
        tfidf_rank_indices = np.lexsort((np.arange(len(tfidf_scores)), -tfidf_scores))
        
        # Build TF-IDF rank lookup
        tfidf_ranks: Dict[str, int] = {}
        for rank_idx, idx in enumerate(tfidf_rank_indices[:limit * 2], 1):
            cid = self._candidate_ids[idx]
            tfidf_ranks[cid] = rank_idx
            
        # 2. FAISS Search
        query_emb = self._model.encode([query_text], convert_to_numpy=True)
        faiss.normalize_L2(query_emb)
        
        distances, indices = getattr(self._faiss_index, "search")(query_emb, limit * 2)
        
        # Build FAISS rank lookup
        faiss_ranks: Dict[str, int] = {}
        for rank_idx, idx in enumerate(indices[0], 1):
            if idx < 0 or idx >= len(self._candidate_ids):
                continue
            cid = self._candidate_ids[idx]
            faiss_ranks[cid] = rank_idx
            
        # 3. Reciprocal Rank Fusion (RRF)
        # RRF Score = 1 / (60 + rank_tfidf) + 1 / (60 + rank_faiss)
        rrf_scores: Dict[str, float] = {}
        all_candidates = set(tfidf_ranks.keys()).union(set(faiss_ranks.keys()))
        
        for cid in all_candidates:
            rank_t = tfidf_ranks.get(cid, 100000) # large number if not in top list
            rank_f = faiss_ranks.get(cid, 100000)
            
            score = (1.0 / (60.0 + rank_t)) + (1.0 / (60.0 + rank_f))
            rrf_scores[cid] = score
            
        # Sort candidates by RRF score descending, tie-breaking alphabetically on candidate ID
        sorted_candidates = sorted(rrf_scores.keys(), key=lambda c: (-rrf_scores[c], c))
        top_cohort = sorted_candidates[:limit]
        
        logger.info(
            "Hybrid retrieval completed",
            extra={
                "retrieved_count": len(top_cohort),
                "top_1_rrf_score": rrf_scores[top_cohort[0]] if top_cohort else 0.0
            }
        )
        return top_cohort

    def retrieve_top_8000_tfidf(self, jd: JobDescription) -> List[str]:
        """Performs fast keyword filtering from 100k down to 8000 candidates using TF-IDF."""
        self.load_indexes()
        if self._tfidf_vectorizer is None or self._tfidf_matrix is None or self._candidate_ids is None:
            raise RuntimeError("TF-IDF indexes failed to load.")
            
        query_text = self._get_query_text(jd)
        tfidf_vector = self._tfidf_vectorizer.transform([query_text])
        if not isinstance(tfidf_vector, csr_matrix):
            raise RuntimeError("Expected csr_matrix from TfidfVectorizer")
        tfidf_scores = (self._tfidf_matrix * tfidf_vector.transpose()).toarray().flatten()
        
        # Stable sort: tie-break by index ascending, primary sort by score descending
        top_indices = np.lexsort((np.arange(len(tfidf_scores)), -tfidf_scores))[:8000]
        return [self._candidate_ids[idx] for idx in top_indices]
