# RecruitAI-Sentinel

An intelligent candidate discovery, screening, ranking, and explainability platform built for recruiter workflows.

---

## 1. Problem Statement

Recruiters evaluating large applicant pools (e.g. 100,000 candidates) face a challenge balancing technical requirements, experience tenure, education relevance, project evidence, behavioral signals, availability, and resume anomalies.

Applying full neural semantic evaluation to every candidate across a 100,000-person dataset is computationally expensive. RecruitAI-Sentinel solves this by implementing a **staged retrieval and ranking funnel**. Cheaper keyword filters prune the initial candidate pool down before deep semantic embedding matching and multi-factor candidate scoring are applied.

---

## 2. Key Features

- **Job Description Parsing**: Automatically extracts job titles, core mandatory requirements, preferred skills, and minimum experience requirements (`JDParser`).
- **4-Stage Funnel Search**: Progressively filters candidate pools from 100,000 down to the Top 100 best-fit candidates using TF-IDF, BM25, and SentenceTransformers.
- **Sentinel Fit Score**: A 100-point composite score evaluating candidate suitability across six weighted dimensions.
- **Dynamic Cohort Skill Rarity**: Dynamically calculates skill scarcity across candidate pools, giving higher weight to hard-to-find specialized skills.
- **Honeypot & Anomaly Detection**: Automatically flags impossible timeline dates, inverted salary expectations, speed title inflation, and technology release-year contradictions (e.g. claiming 7 years of ChatGPT experience).
- **Duplicate-Profile Sanity Handling**: Detects duplicate profile submissions and applies a score demotion pass ($\times 0.1$) so non-duplicate candidates enter the top ranking slice.
- **Factual Candidate Explanations**: Generates transparent recommendation reports based on matched skills, missing skills, and empirical signals (`ExplainabilityEngine`).
- **Recruiter Dashboard**: Interactive Next.js web application with candidate rankings, candidate detail views, and server-side demographic analytics.
- **Submission Output**: Generates benchmark-compliant `submission.csv` and `ranking_results.json` persistence files.

---

## 3. Architecture

RecruitAI-Sentinel processes large candidate datasets using a multi-stage funnel:

```
                  Uploaded Job Description
                             │
                             ▼
                        [JD Parser]
                             │
                             ▼
              [Stage 1: TF-IDF Retrieval]
            (100,000 ──► 8,000 Candidate IDs)
                             │
                             ▼
               [Stage 2: BM25 Filtering]
            (8,000 ──► 1,000 Candidates)
                             │
                             ▼
      [Stage 3: SentenceTransformer Semantic Search]
            (1,000 ──► 300 Candidates)
                             │
                             ▼
         [Stage 4: Multi-Factor Ranking Engine]
           (Skill, Exp, Edu, Proj, Beh, Avail)
                             │
                             ▼
                  [Explainability Engine]
                             │
                             ▼
                   Top 100 Candidates
             (submission.csv & ranking_results.json)
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
         FastAPI Backend          Next.js Web UI
      (http://127.0.0.1:8000)  (http://localhost:3000)
```

---

## 4. Sentinel Fit Score

Candidate evaluation produces a **Sentinel Fit Score** out of 100 points, calculated across six canonical dimensions:

| Dimension | Maximum Points | Description |
| :--- | :---: | :--- |
| **Skills Match** | **40.0** | Core requirements ($1.0\times$), preferred skills ($0.4\times$), recency, duration, proficiency, and dynamic cohort rarity. |
| **Experience Match** | **25.0** | Tenure alignment, semantic title/description similarity, leadership indicators, and scale metrics. |
| **Education Match** | **10.0** | Degree level (Ph.D $+2.0$, Master's $+1.0$) and field relevance (CS/STEM $8.0$ vs IT $6.0$ vs Other $4.0$). |
| **Project Evidence** | **10.0** | Verb + Tech + Metric pattern density extracted from summary and project descriptions. |
| **Behaviour Signals** | **10.0** | Profile completeness, recruiter response rate, interview completion, social proof, and verification flags. |
| **Availability** | **5.0** | Notice period scoring ($0$ days/immediate $= 4.0$ pts vs $90+$ days $= 0.5$ pts) plus open-to-work bonus ($+1.0$ pt). |
| **Total** | **100.0** | **Composite Sentinel Fit Score** |

*Note: The Sentinel Fit Score is a cohort-relative ranking index out of 100, not a literal percentage of job requirements met.*

---

## 5. Technology Stack

### Backend
- **Language**: Python 3.11
- **API Framework**: FastAPI 0.111, Uvicorn 0.30
- **Validation & Settings**: Pydantic 2.7, Pydantic-Settings 2.3
- **Vector Search & ML**: SentenceTransformers 3.0 (`all-MiniLM-L6-v2`), FAISS-cpu 1.8, scikit-learn 1.5, rank-bm25 0.2
- **Data Processing**: NumPy 1.26, Pandas 2.2, python-docx 1.1, ujson 5.10
- **Testing**: Pytest 8.2, Pytest-Asyncio 0.23

### Frontend
- **Framework**: Next.js 15.1 (App Router), React 19
- **Language**: TypeScript 5.7
- **Styling**: Tailwind CSS 3.4
- **UI & Animations**: Lucide React, Framer Motion 11.15, Recharts 2.15

---

## 6. Repository Structure

```
RecruitAI-Sentinel/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── endpoints/         # FastAPI router endpoints (ranking, candidate, analytics, health)
│   │   ├── config/                # Environment settings & middleware
│   │   ├── core/                  # Exception handlers
│   │   ├── explainability/        # Factual reasoning generation engine
│   │   ├── ranking/               # Multi-factor candidate scoring engine
│   │   ├── retrieval/             # Hybrid search engine (TF-IDF + FAISS + RRF)
│   │   ├── schemas/               # Pydantic data schemas
│   │   └── services/              # Pipeline runner, dataset loader, JD parser, intelligence builder
│   └── tests/                     # Backend automated test suite
├── frontend/
│   ├── app/                       # Next.js pages (/, /rankings, /candidate/[id], /analytics)
│   ├── components/                # Reusable UI components & navigation
│   ├── services/                  # Frontend API integration service
│   └── types/                     # TypeScript interface definitions
├── docs/                          # Architectural specifications & documentation
├── scripts/                       # Environment setup & precompute indexing scripts
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git exclusion rules
├── package.json                   # Frontend dependencies
├── pytest.ini                     # Pytest configuration
├── README.md                      # Project documentation
├── requirements.txt               # Backend Python dependencies
├── run_pipeline.py                # Command-line entrypoint for ranking pipeline
├── sample_jd.docx                 # Sample Job Description (.docx format)
└── sample_jd.txt                  # Sample Job Description (.txt format)
```

---

## 7. Prerequisites

- **Python**: Python 3.11
- **Node.js & npm**: Node.js v18+ and `npm` v9+

---

## 8. Installation

### PowerShell (Windows) Setup Instructions:

1. **Clone or navigate into the repository**:
   ```powershell
   cd RecruitAI-Sentinel
   ```

2. **Create and activate Python virtual environment**:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install backend dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Install frontend dependencies**:
   ```powershell
   cd frontend
   npm install
   cd ..
   ```

---

## 9. Environment Configuration

Copy `.env.example` to `.env` in the root directory:

```powershell
Copy-Item .env.example .env
```

Configure data paths inside `.env` to point to your candidate dataset:

```env
CHALLENGE_ROOT=./data
CANDIDATE_DATASET_PATH=./data/candidates.jsonl
JOB_DESCRIPTION_PATH=./data/job_description.docx
SQLITE_DB_PATH=backend/app/sentinel.db
VECTOR_INDEX_PATH=backend/app/vectors.faiss
```

---

## 10. Dataset Setup

The 100,000 candidate dataset (`candidates.jsonl`) is externally supplied as part of the challenge data package.

If using the default/example configuration:
1. Create the `data/` directory in the project root if it does not exist:
   ```powershell
   New-Item -ItemType Directory -Path "data" -Force
   ```
2. Place the organizer-provided `candidates.jsonl` inside the `data/` directory.
3. Ensure `CANDIDATE_DATASET_PATH=./data/candidates.jsonl` is set in your `.env` file.

This path is used by the backend `DatasetLoader` when retrieving full profile details during candidate inspection and when running the ranking pipeline.

---

## 11. Precomputation & Index Setup (Optional for Included Demo)

> [!NOTE]
> **Precomputation is OPTIONAL for the included demo and evaluation.**
> The package already contains the precomputed retrieval assets corresponding to the benchmark dataset:
> - `backend/app/vectors.faiss` (FAISS vector index for profile embeddings)
> - `backend/app/tfidf.pkl` (TF-IDF vectorizer and sparse matrix)
> - `backend/app/candidate_ids.json` (Ordered candidate ID mapping)
> - `backend/app/candidate_offsets.json` (Fast file byte offsets for single-candidate retrieval)
>
> Therefore, a fresh evaluator does **NOT** need to run `scripts/precompute.py` merely to launch the application, inspect candidates, or evaluate the canonical results.

`scripts/precompute.py` is only required when building or rebuilding indexes for a new or different candidate dataset:

```powershell
python scripts/precompute.py
```
*(Note: If executing a full pipeline run against a different candidate dataset, precomputation must be run first so that vectors and offset indexes correspond to the new data).*

---

## 12. Running the Application

To run the complete web application, open two PowerShell terminals:

### Terminal 1 — Backend API Server
```powershell
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
- API Documentation: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health`

### Terminal 2 — Frontend Recruiter Dashboard
```powershell
cd frontend
npm run dev
```
- Web Application: `http://localhost:3000`

---

## 13. Running the Ranking Pipeline from CLI

To execute the screening pipeline directly via command line without starting the web UI:

```powershell
python run_pipeline.py
```

This script parses the active job description, executes the 4-stage retrieval pipeline over the dataset, and outputs:
- `submission.csv`
- `backend/app/ranking_results.json`

---

## 14. Output Artifacts

- **`submission.csv`**: Challenge submission output containing 100 ranked candidates.
  - **Schema**: `candidate_id, rank, score, reasoning`
  - **Constraints**: Ranks 1 to 100, unique candidate IDs, scores sorted descending, factual reasoning text.
- **`backend/app/ranking_results.json`**: Persistence artifact containing detailed score breakdowns, matched skills, missing skills, and anomaly records. Used by backend endpoints to ensure score unification across pages.

---

## 15. Main Application Pages

- **Landing Page (`/`)**: Overview of active job description, platform metrics, and screening launch options.
- **Screening Workspace (`/rank` or `/rankings`)**: Interactive ranking table with candidate cards, Sentinel Fit Scores (`/100`), critical skills matched, missing skills, and score breakdown popovers.
- **Candidate Details (`/candidate/[id]`)**: Full candidate profile breakdown including Sentinel Fit Score, 6 sub-score meters, matched/missing skill lists, factual recommendation text, risk flags, career history, education, and behavioral signals.
- **Analytics Dashboard (`/analytics`)**: Cohort demographic insights including top universities, location distribution, work mode preferences, education distribution, and top missing skills.

---

## 16. API Endpoints

- **GET `/health`**: Server health check (`{"status": "healthy"}`).
- **POST `/api/rank`**: Triggers candidate screening run using uploaded `.docx`, `.txt`, or `.md` Job Description.
- **GET `/api/top100`**: Retrieves Top 100 ranked candidates for the active JD.
- **GET `/api/candidate/{candidate_id}`**: Retrieves candidate detail profile, score breakdown, and persistent evaluation data.
- **GET `/api/analytics`**: Computes server-side demographic aggregations across the active screening cohort.

---

## 17. Verification Commands

Run developer verification checks to validate repository health:

### Backend Unit Test Suite:
```powershell
.venv\Scripts\pytest
```
*(Latest Status: 17 passed)*

### Backend Syntax Compilation:
```powershell
.venv\Scripts\python.exe -m compileall backend
```
*(Latest Status: 0 errors)*

### Frontend TypeScript Check:
```powershell
cd frontend
npx tsc --noEmit
```
*(Latest Status: 0 errors)*

### Frontend Production Build:
```powershell
cd frontend
npm run build
```
*(Latest Status: Compiled successfully)*

---

## 18. Key Design Decisions

1. **Staged Funnel Retrieval**: Cheaper sparse TF-IDF and BM25 filtering prune 99% of candidates before dense neural embedding matching is applied, guaranteeing fast execution times.
2. **Persistent Evaluation Artifact**: Candidate evaluation results are saved to `ranking_results.json`, ensuring Candidate Details and Rankings pages display 100% numerically unified scores.
3. **Structured API Data**: Frontend pages consume structured arrays (`critical_skills_matched`, `missing_critical_skills`) rather than parsing generated reasoning text.
4. **Server-Side Analytics Aggregation**: Demographic charts on `/analytics` are aggregated on the backend in 1 pass, eliminating client-side N+1 candidate requests.

---

## 19. Known Limitations

- **Dataset Dependency**: Running precomputation and screening requires the external challenge dataset (`candidates.jsonl`).
- **Cohort-Relative Scores**: Skill rarity weighting evaluates skill scarcity within the active applicant pool, making scores relative to the current candidate cohort.
- **Browser Automation Context**: Automated Playwright browser testing may depend on local Chrome CDP WebSocket availability (`port 9222`).

---

## 20. Challenge Context

Developed for the **Redrob Intelligent Candidate Discovery & Ranking Challenge** (India.RUNS Data & AI Challenge).
