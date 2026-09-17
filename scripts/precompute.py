import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
import sys
import json
import time
import pickle
import re
import logging
from pathlib import Path
import numpy as np

# Adjust python path to import app modules correctly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.app.config.settings import settings
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer
import faiss

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger("precompute")

def write_status(status_str: str, progress: int, message: str) -> None:
    status_path = Path(settings.CANDIDATE_IDS_PATH).parent / "precompute_status.json"
    try:
        status_path.parent.mkdir(parents=True, exist_ok=True)
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": status_str, "progress": progress, "message": message}, f)
    except Exception as e:
        logger.warning(f"Failed to write precompute status: {e}")

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()

def get_candidate_sparse_text(cand: dict) -> str:
    """Full representation for TF-IDF containing complete work history and education details."""
    parts = []
    profile = cand.get("profile", {})
    parts.append(profile.get("headline", ""))
    parts.append(profile.get("summary", ""))
    parts.append(profile.get("current_title", ""))
    parts.append(profile.get("current_company", ""))
    
    for s in cand.get("skills", []):
        parts.append(s.get("name", ""))
        
    for job in cand.get("career_history", []):
        parts.append(job.get("title", ""))
        parts.append(job.get("company", ""))
        parts.append(job.get("description", ""))
        
    for edu in cand.get("education", []):
        parts.append(edu.get("degree", ""))
        parts.append(edu.get("field_of_study", ""))
        parts.append(edu.get("institution", ""))
        
    return clean_text(" ".join([p for p in parts if p]))

def get_candidate_dense_text(cand: dict) -> str:
    """Short, semantic representation for dense embeddings, focusing on key identity elements."""
    parts = []
    profile = cand.get("profile", {})
    parts.append(profile.get("headline", ""))
    parts.append(profile.get("current_title", ""))
    parts.append(profile.get("current_company", ""))
    
    # Include up to top 25 skill names
    for s in cand.get("skills", [])[:25]:
        parts.append(s.get("name", ""))
        
    return clean_text(" ".join([p for p in parts if p]))

def main():
    write_status("processing", 5, "Initializing optimized precomputation...")
    try:
        logger.info("Initializing optimized precomputation...")
        
        # 1. Check dataset path
        dataset_path = settings.CANDIDATE_DATASET_PATH
        if not dataset_path or not Path(dataset_path).exists():
            logger.error(f"Candidate dataset path not configured or file not found: {dataset_path}")
            write_status("failed", 0, f"Candidate dataset path not found: {dataset_path}")
            sys.exit(1)
            
        logger.info(f"Reading candidates from: {dataset_path}")
        write_status("processing", 10, "Streaming candidate dataset and building direct offsets map...")
        
        # Configure PyTorch CPU threads
        num_threads = os.cpu_count() or 4
        torch.set_num_threads(num_threads)
        logger.info(f"Configured PyTorch to use {num_threads} CPU threads")
        
        candidate_ids = []
        sparse_texts = []
        dense_texts = []
        
        start_time = time.time()
        
        # Stream JSONL and track line offsets
        offsets = {}
        with open(dataset_path, "rb") as f:
            while True:
                offset = f.tell()
                line = f.readline()
                if not line:
                    break
                line_str = line.strip()
                if not line_str:
                    continue
                cand = json.loads(line_str.decode("utf-8"))
                cid = cand["candidate_id"]
                offsets[cid] = offset
                candidate_ids.append(cid)
                sparse_texts.append(get_candidate_sparse_text(cand))
                dense_texts.append(get_candidate_dense_text(cand))
                
                idx = len(candidate_ids)
                if idx % 20000 == 0:
                    logger.info(f"Streamed and parsed {idx} candidates...")
                    pct = 10 + int(idx / 100000.0 * 30.0)
                    write_status("processing", min(pct, 40), f"Streamed and parsed {idx} candidate profiles...")
                    
        logger.info(f"Loaded {len(candidate_ids)} candidates in {time.time() - start_time:.2f}s")
        write_status("processing", 45, "Building TF-IDF Index...")
        
        # 2. Build and save TF-IDF Vectorizer & Matrix
        logger.info("Building TF-IDF Index...")
        tfidf_start = time.time()
        vectorizer = TfidfVectorizer(max_features=10000, stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(sparse_texts)
        logger.info(f"TF-IDF Index created in {time.time() - tfidf_start:.2f}s. Shape: {tfidf_matrix.shape}")
        
        write_status("processing", 50, "Saving TF-IDF Index and candidate mappings...")
        
        tfidf_out = Path(settings.TFIDF_PATH)
        tfidf_out.parent.mkdir(parents=True, exist_ok=True)
        with open(tfidf_out, "wb") as f:
            pickle.dump({"vectorizer": vectorizer, "matrix": tfidf_matrix}, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info(f"Saved TF-IDF index to {tfidf_out}")
        
        # Save candidate IDs
        ids_out = Path(settings.CANDIDATE_IDS_PATH)
        with open(ids_out, "w", encoding="utf-8") as f:
            json.dump(candidate_ids, f)
        logger.info(f"Saved candidate IDs mapping to {ids_out}")
        
        # Save candidate offsets
        offsets_out = ids_out.parent / "candidate_offsets.json"
        with open(offsets_out, "w", encoding="utf-8") as f:
            json.dump(offsets, f)
        logger.info(f"Saved candidate offsets mapping to {offsets_out}")
        
        # Clear sparse texts from RAM to save memory
        del sparse_texts
        
        write_status("processing", 55, "Loading SentenceTransformer model (all-MiniLM-L6-v2)...")
        
        # 3. Generate Embeddings & Build FAISS Index in chunks
        logger.info("Loading SentenceTransformer model (all-MiniLM-L6-v2)...")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        
        logger.info("Encoding candidate profile texts in chunks to optimize memory...")
        emb_start = time.time()
        
        dimension = 384
        index = faiss.IndexFlatIP(dimension)
        
        chunk_size = 10000
        num_chunks = len(dense_texts) // chunk_size + (1 if len(dense_texts) % chunk_size else 0)
        
        for i in range(0, len(dense_texts), chunk_size):
            chunk_texts = dense_texts[i:i+chunk_size]
            chunk_idx = i // chunk_size + 1
            
            write_status("processing", 60 + int(chunk_idx / num_chunks * 35), f"Encoding embeddings chunk {chunk_idx}/{num_chunks}...")
            
            chunk_embs = model.encode(
                chunk_texts,
                batch_size=128,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            faiss.normalize_L2(chunk_embs)
            index.add(chunk_embs)  # type: ignore
            
            logger.info(f"Encoded chunk {chunk_idx}/{num_chunks}...")
            
            import gc
            del chunk_embs
            gc.collect()
            
        logger.info(f"Generated embeddings for {len(dense_texts)} candidates in {time.time() - emb_start:.2f}s")
        write_status("processing", 98, "Saving FAISS Index to disk...")
        
        faiss_out = Path(settings.VECTOR_INDEX_PATH)
        faiss.write_index(index, str(faiss_out))
        logger.info(f"FAISS index built and saved to {faiss_out}")
        
        logger.info(f"Precomputation completed successfully in {(time.time() - start_time) / 60:.2f} minutes.")
        write_status("success", 100, f"Precomputation completed successfully in {int(time.time() - start_time)} seconds.")
    except Exception as e:
        logger.error(f"Precomputation run failed: {e}", exc_info=True)
        write_status("failed", 0, f"Failed: {str(e)[:150]}")
        sys.exit(1)

if __name__ == "__main__":
    main()
