# Project Guide: RecruitAI Sentinel

This guide serves as the permanent reference for the architecture, engineering standards, folder structure, and build order of **RecruitAI Sentinel**. Future implementations must adhere strictly to the guidelines and specifications detailed in this document.

---

## 1. Project Goal & Constraints

### 1.1 Project Goal
Build a production-quality, high-precision Candidate Ranking System that takes a Job Description (JD) and a pool of 100,000 candidate profiles, filters and ranks them, and outputs a valid `submission.csv` containing the top 100 candidates.

This system is a **real-world backend ranking and retrieval engine** with a supporting web interface—not a chatbot, demo, or ATS clone.

### 1.2 Official Constraints & Source of Truth
All requirements are derived from the official challenge files in:
`C:\Users\BADRINATH\Downloads\[PUB] India_runs_data_and_ai_challenge\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge`

* **Target Python**: Python 3.11
* **Execution Environment**: Runs locally in VS Code and inside the Antigravity IDE sandbox (Windows compatible).
* **Compute Restrictions**:
  * Total runtime: $\le 5$ minutes wall-clock for the ranking step.
  * Memory: $\le 16$ GB RAM peak usage.
  * Compute: CPU only (no GPU execution allowed during ranking).
  * Network: Completely disabled during ranking (no external API calls to OpenAI, Anthropic, Gemini, etc.).
  * Intermediate State Disk Footprint: $\le 5$ GB.
* **Submission Format**: A CSV file named `<participant_id>.csv` containing exactly 100 data rows (plus 1 header row) with columns: `candidate_id,rank,score,reasoning`.
  * `candidate_id`: String matching pattern `^CAND_[0-9]{7}$`.
  * `rank`: Integers 1 to 100 appearing exactly once.
  * `score`: Floating point values, strictly non-increasing by rank.
  * `reasoning`: 1-2 sentence factual, non-hallucinated justification.
  * **Tie-break Rule**: If scores are identical, candidates must be sorted by `candidate_id` ascending.
* **Honeypot Filter**: The dataset contains subtly impossible candidate profiles (honeypots). A honeypot rate $> 10\%$ in the top 100 results in immediate disqualification.

---

## 2. Rules

1. **Never Duplicate Code**: Implement common utility functions (e.g., date parsing, text normalization) in a shared helper module.
2. **Never Duplicate Modules**: Do not create overlapping files or modules. Follow the defined 10-module architecture.
3. **Never Hardcode Paths**: All directory structures, input file paths, and output targets must be read from environment variables or command-line arguments.
4. **Never Modify Challenge Files**: Keep the downloads directory completely read-only.
5. **Keep Interfaces Stable**: Do not change function signatures or API contracts once defined, ensuring backward compatibility.
6. **Correctness First**: Ensure algorithms pass rigorous validation checks before optimizing for execution speed. Only optimize performance after confirming correctness.
7. **No Overfitting**: Design features and matching algorithms to generalize across the entire 100,000 candidate dataset, avoiding hardcoded rules specific to individual sample records.

---

## 3. Modular Architecture

The project consists of exactly these 10 modules:

```
┌────────────────────────────────────────────────────────┐
│                   1. Dataset Loader                    │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌───────────────────────────┐      ┌─────────────────────┐
│       2. JD Parser        │      │ 3. Candidate Parser │
└─────────────┬─────────────┘      └──────────┬──────────┘
              ▼                               ▼
┌────────────────────────────────────────────────────────┐
│                 4. Feature Engineering                 │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│                  5. Retrieval Engine                   │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│                   6. Ranking Engine                    │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│                7. Explainability Engine                │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│                  8. Submission Engine                  │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌───────────────────────────┴────────────────────────────┐
│                  9. FastAPI Backend                    │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│                 10. Next.js Frontend                   │
└────────────────────────────────────────────────────────┘
```

### 3.1 Dataset Loader
* **Purpose**: Read the candidate pool (`candidates.jsonl` or `candidates.jsonl.gz`) in a memory-efficient manner.
* **Inputs**: File path to candidates dataset.
* **Outputs**: Generator yielding raw candidate dictionary records one line at a time.
* **Responsibilities**: Handle decompression of `.gz` files transparently, read data stream line-by-line to avoid loading the entire 480+ MB dataset into memory, and validate stream availability.

### 3.2 JD Parser
* **Purpose**: Parse raw job description files and extract target criteria.
* **Inputs**: Path to `.docx` or `.txt` JD files, or raw query text.
* **Outputs**: Structured dictionary containing job metadata (e.g., target title, experience bounds, required skills, preferred locations, and disqualifiers).
* **Responsibilities**: Extract text from `.docx` files using zip/xml reading, execute rule-based extraction to identify numeric boundaries (years of experience) and matching keywords (skills).

### 3.3 Candidate Parser
* **Purpose**: Normalize and parse candidate raw JSON objects into structured Pydantic models.
* **Inputs**: Raw dictionary representing a single candidate record.
* **Outputs**: Typed `CandidateProfile` schema instance.
* **Responsibilities**: Clean unstructured string inputs, handle missing/null attributes gracefully, convert date strings to date objects, and parse structured sub-elements (`career_history`, `education`, `skills`, `redrob_signals`).

### 3.4 Feature Engineering
* **Purpose**: Calculate numeric and categorical features from candidate profiles to feed retrieval and ranking modules.
* **Inputs**: `CandidateProfile` schema.
* **Outputs**: Structured feature dictionary.
* **Responsibilities**: Compute total months of professional experience, extract current company type (IT services vs. product), determine average tenure duration, match listed skills against a canonical skill synonym graph, and flag structural profile anomalies (such as overlapping employment dates).

### 3.5 Retrieval Engine
* **Purpose**: Perform fast initial candidate screening to reduce the 100,000 pool to a manageable subset (e.g., top 1,000) for heavy ranking calculations.
* **Inputs**: Target JD criteria, candidate feature registry, and candidate limit ($K$, defaults to 1,000).
* **Outputs**: List of $K$ candidate IDs.
* **Responsibilities**: Implement a pluggable retrieval design interface. Provide BM25 keyword matching over candidate profiles and cosine similarity matching over pre-computed low-dimensional vector embeddings, combining scores using Reciprocal Rank Fusion (RRF).

### 3.6 Ranking Engine
* **Purpose**: Perform multi-criteria evaluation on the screened cohort and output a sorted ranking.
* **Inputs**: Cohort of candidate profiles, JD criteria, and scoring configuration weights.
* **Outputs**: List of candidate IDs sorted by final aggregated scores.
* **Responsibilities**:
  * Execute scoring sub-routines: Skill Relevance, Production Experience Alignment, Tenure Stability, Behavioral Availability, and Logistics match.
  * **Honeypot Filter**: Check candidate profile consistency (e.g., checking if candidate's years of experience at a company exceed the company's lifespan, or if listed experience overlaps impossible timeline boundaries). Candidates flagged as honeypots are assigned a final score of $0.0$ and excluded from the top 100.
  * Aggregate sub-scores using a configurable aggregator (e.g., weighted sum or rule ensemble).

### 3.7 Explainability Engine
* **Purpose**: Generate factual, non-hallucinated explanations for the ranked candidate cohort.
* **Inputs**: Top 100 candidate profiles, scoring logs, and JD requirements.
* **Outputs**: Dictionary mapping candidate IDs to a 1-2 sentence explanation string.
* **Responsibilities**: Ensure all reasoning claims are derived strictly from facts present in the candidate profile (referencing exact years of experience, specific skills, titles, or locations) and match the candidate's rank position.

### 3.8 Submission Engine
* **Purpose**: Format, sort, and write final ranking outputs to a CSV file.
* **Inputs**: Ranked candidate details, scores, and reasonings.
* **Outputs**: Formatted, validated CSV file (`team_xxx.csv`).
* **Responsibilities**: Order records by score descending (resolving score ties by sorting `candidate_id` ascending), format output columns precisely, and run the official `validate_submission.py` script.

### 3.9 FastAPI Backend
* **Purpose**: Expose HTTP endpoints to orchestrate the parsing, ranking, and export tasks.
* **Endpoints**:
  * `POST /api/v1/jd/upload`: Parse and register an uploaded Job Description.
  * `POST /api/v1/rank/run`: Trigger the ranking pipeline for the active JD against the candidate dataset.
  * `GET /api/v1/rank/results`: Return the top 100 ranked candidates with sub-scores, confidence levels, and reasonings.
  * `POST /api/v1/submission/export`: Write and validate the output submission CSV file.

### 3.10 Next.js Frontend
* **Purpose**: Provide a web-based user interface to interact with the ranking engine.
* **Components**:
  * **Dashboard Layout**: Side panel navigation and connection status monitor.
  * **JD Upload Card**: UI controls to select a Job Description file, view parsed details, and configure weights.
  * **Rankings Table**: Grid display of the top 100 candidates highlighting scores, inline reasonings, and risk warning indicators.
  * **Candidate Deep-dive Modal**: Explanatory radar charts of engine sub-scores and interactive candidate career timelines.

---

## 4. Folder Structure

```
RecruitAI-Sentinel/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py              # Environment & Config settings
│   │   │   └── database.py            # SQLite connection setup
│   │   ├── models/
│   │   │   └── candidate.py           # Database relational schemas
│   │   ├── schemas/
│   │   │   ├── candidate.py           # Pydantic profile validation models
│   │   │   └── pipeline.py            # Pipeline run schemas
│   │   ├── modules/
│   │   │   ├── dataset_loader.py      # Memory-efficient JSONL reader
│   │   │   ├── jd_parser.py           # Word parser & criteria extractor
│   │   │   ├── candidate_parser.py    # Raw dictionary normalizer
│   │   │   ├── feature_engineering.py  # Metrics & Synonym calculations
│   │   │   ├── retrieval_engine.py    # Pluggable candidate screening
│   │   │   ├── ranking_engine.py      # Core scorer & honeypot filter
│   │   │   ├── explainability_engine.py# Factual reasoning generator
│   │   │   └── submission_engine.py   # Tie-breaking CSV generator
│   │   ├── api/
│   │   │   ├── endpoints/
│   │   │   │   ├── health.py          # API status endpoint
│   │   │   │   ├── jd.py              # JD upload routing
│   │   │   │   └── rank.py            # Ranking execution routing
│   │   │   └── router.py              # Central routing registry
│   │   └── main.py                    # FastAPI entrypoint
│   ├── tests/
│   │   ├── test_modules.py            # Isolated checks for modules 1-8
│   │   └── test_pipeline.py           # End-to-end correctness tests
│   ├── requirements.txt               # Backend dependencies
│   └── Dockerfile                     # API containerization spec
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx             # Root frame structure
│   │   │   └── page.tsx               # Main Dashboard page
│   │   ├── components/
│   │   │   ├── JDUploadCard.tsx       # File upload controller
│   │   │   ├── RankingsTable.tsx      # Results rendering grid
│   │   │   └── CandidateModal.tsx     # Visual profile deep-dive
│   │   └── lib/
│   │       └── api.ts                 # Fetch clients for backend routes
│   ├── package.json                   # Frontend node dependencies
│   ├── tailwind.config.js             # Styling tokens
│   └── tsconfig.json                  # TypeScript compiler settings
├── scripts/
│   ├── precompute.py                  # Embedding & SQLite indexing script
│   └── setup_env.ps1                  # Development environment bootstrap
├── docker-compose.yml                 # Service orchestrator
├── .env.example                       # Reference environment variables
├── .gitignore                         # Version control exclusions
└── PROJECT_GUIDE.md                   # This guide
```

---

## 5. Storage Architecture

We utilize a **Hybrid Storage Architecture** tailored for fast, local sandboxed execution:
1. **SQLite Database (`sentinel.db`)**: Holds structural profile metadata, parsed Job Descriptions, historical runs, and active system settings. SQLite is zero-configuration, single-file, fast, and integrates seamlessly into sandboxed environments without requiring background database services.
2. **Flat Binary Vector Indexes / Arrays (`vectors.faiss` or NumPy matrices)**: Holds pre-computed candidate embeddings. Offloading high-dimensional vector search to flat binary indexes keeps the SQL database small, efficient, and responsive.

---

## 6. Project Build Roadmap

This section outlines the chronological implementation roadmap. Each step must be fully verified before proceeding to the next.

```
┌────────────────────────────────────────────────────────┐
│             PHASE 1: Project Setup & Init             │
│                    (Steps 1 - 2)                       │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│             PHASE 2: Parsers & Data Pipeline           │
│                    (Steps 3 - 5)                       │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│             PHASE 3: Retrieval & Engines               │
│                    (Steps 6 - 8)                       │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│             PHASE 4: API & Integration                 │
│                    (Steps 9 - 10)                      │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│            PHASE 5: Next.js Frontend Dashboard         │
│                    (Steps 11 - 12)                     │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│           PHASE 6: Optimization & Validation           │
│                    (Steps 13 - 14)                     │
└────────────────────────────────────────────────────────┘
```

### Step 1: Environment & Directory Skeleton Setup
* **Objective**: Initialize virtual environment, requirements, and empty directory structures.
* **Files to create**:
  * `backend/requirements.txt`
  * `scripts/setup_env.ps1`
  * `.gitignore`
  * `.env.example`
* **Dependencies**: None.
* **Verification**: Running `setup_env.ps1` creates the virtual environment, installs basic packages, and confirms directories exist.

### Step 2: Database Initialization & Relational Schemas
* **Objective**: Create the SQLite database file and initialize tables for candidates, JDs, and active pipelines.
* **Files to create**:
  * `backend/app/core/config.py`
  * `backend/app/core/database.py`
  * `backend/app/models/candidate.py`
* **Dependencies**: Step 1.
* **Verification**: Run database check script to confirm creation of `sentinel.db` containing correct tables.

### Step 3: Dataset Loader & Candidate Parser Development
* **Objective**: Implement memory-efficient candidate streaming and parse profiles into Pydantic models.
* **Files to create**:
  * `backend/app/modules/dataset_loader.py`
  * `backend/app/modules/candidate_parser.py`
  * `backend/app/schemas/candidate.py`
* **Dependencies**: Step 2.
* **Verification**: Parse a sample of candidate dictionary records. Confirm correct validation of nested attributes with zero memory leaks.

### Step 4: JD Parser Implementation
* **Objective**: Extract title, experience ranges, and key terms from Job Description `.docx` files.
* **Files to create**:
  * `backend/app/modules/jd_parser.py`
* **Dependencies**: Step 3.
* **Verification**: Parse the official challenge `job_description.docx`. Verify outputs contain correct experience bounds and target keyword terms.

### Step 5: Feature Engineering & Pre-computation
* **Objective**: Build candidate numeric features, handle synonyms mapping, and pre-compute similarity indexes.
* **Files to create**:
  * `backend/app/modules/feature_engineering.py`
  * `scripts/precompute.py`
* **Dependencies**: Step 4.
* **Verification**: Run `precompute.py` on `sample_candidates.json`. Confirm output generates correct SQL profiles and flat-file vector matrices.

### Step 6: Pluggable Retrieval Engine
* **Objective**: Build candidate filter engine yielding top $K$ candidates using BM25 and vector embeddings.
* **Files to create**:
  * `backend/app/modules/retrieval_engine.py`
* **Dependencies**: Step 5.
* **Verification**: Execute query search against sample dataset. Confirm retrieval of top 1,000 matches completes within 5 seconds on CPU.

### Step 7: Core Ranking Engine & Honeypot Detector
* **Objective**: Build scoring sub-routines (skills, experience, behavioral) and absolute filters to identify and remove honeypot candidates.
* **Files to create**:
  * `backend/app/modules/ranking_engine.py`
* **Dependencies**: Step 6.
* **Verification**: Run candidate validation tests. Verify honeypots are assigned a score of $0.0$ and excluded from calculations.

### Step 8: Explainability & Submission Engines
* **Objective**: Generate factual candidate justifications and construct valid final CSV files.
* **Files to create**:
  * `backend/app/modules/explainability_engine.py`
  * `backend/app/modules/submission_engine.py`
* **Dependencies**: Step 7.
* **Verification**: Generate ranked CSV file. Run `validate_submission.py` to confirm zero formatting errors.

### Step 9: FastAPI Backend Endpoints
* **Objective**: Expose API routers to orchestrate the pipeline from file upload to rankings display.
* **Files to create**:
  * `backend/app/api/endpoints/health.py`
  * `backend/app/api/endpoints/jd.py`
  * `backend/app/api/endpoints/rank.py`
  * `backend/app/api/router.py`
  * `backend/app/main.py`
* **Dependencies**: Step 8.
  * **Verification**: Query endpoint APIs using local client. Check JSON responses match schema properties.

### Step 10: Backend Containerization
* **Objective**: Setup Docker environment for isolated, reproducible backend execution.
* **Files to create**:
  * `backend/Dockerfile`
  * `docker-compose.yml`
* **Dependencies**: Step 9.
* **Verification**: Build and launch using command `docker compose up`. Verify health endpoint returns success.

### Step 11: Next.js Boilerplate & Core Layouts
* **Objective**: Create frontend boilerplate and basic interface structure.
* **Files to create**:
  * `frontend/package.json`
  * `frontend/tsconfig.json`
  * `frontend/src/app/layout.tsx`
  * `frontend/src/app/page.tsx`
* **Dependencies**: Step 10.
* **Verification**: Start frontend development server. Confirm home page renders without console warnings.

### Step 12: Frontend Components & Interactive Dashboards
* **Objective**: Build file upload cards, interactive candidate tables, and radar analysis dashboards.
* **Files to create**:
  * `frontend/src/components/JDUploadCard.tsx`
  * `frontend/src/components/RankingsTable.tsx`
  * `frontend/src/components/CandidateModal.tsx`
  * `frontend/src/lib/api.ts`
* **Dependencies**: Step 11.
* **Verification**: Upload test JD file. Verify candidates render correctly in rankings view, and modal timeline displays correct candidate details.

### Step 13: Pipeline Constraints Verification
* **Objective**: Run performance profiling to verify execution boundaries are satisfied on full pool.
* **Files to create**: None.
* **Dependencies**: Step 12.
* **Verification**: Trigger ranking run on complete `candidates.jsonl` file. Ensure process completes in under 5 minutes on CPU and stays within 16 GB RAM limits.

### Step 14: Final Submission Verification
* **Objective**: Run official format check on the exported ranking CSV file.
* **Files to create**: None.
* **Dependencies**: Step 13.
* **Verification**: Run `python validate_submission.py submission.csv` on backend. Confirm output displays "Submission is valid".
