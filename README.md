# PE Org-AI-R Platform
## Case Study 4 — RAG & Search Engine
### From Scored Evidence to Cited Investment Justifications

**Course:** Big Data and Intelligent Analytics
**Instructor:** Professor Sri Krishnamurthy
**Term:** Spring 2026

## Team 3

- Ishaan Samel
- Ayush Fulsundar
- Vaishnavi Srinivas

---

## 🚀 Live Application

| Component | Link |
|-----------|------|
| Demo Video | TBD |
| Interactive Codelab | [CS4 RAG & Search Codelab](https://codelabs-preview.appspot.com/?file_id=1vbScSJyPROzPjuzx6h-lVBne2yIizObxuDUvmVDJmBI#12) |

---

## 📌 Executive Summary

Case Study 4 implements the RAG (Retrieval-Augmented Generation) & Search layer of the PE Org-AI-R platform.

Building on:

- Case Study 1 → Platform Foundation (FastAPI, Snowflake, Redis, Docker)
- Case Study 2 → Evidence Collection & Signal Extraction
- Case Study 3 → Risk-adjusted, sector-calibrated scoring engine
- Case Study 4 → RAG-powered search, score justification, and IC meeting preparation

The CS4 layer answers the critical PE question:

> *"Why did this company score 72 on Data Infrastructure?"*

It transforms raw Org-AI-R scores into **cited, evidence-backed investment justifications** suitable for IC (Investment Committee) presentations.

Key capabilities:

- Hybrid semantic + keyword evidence search (Dense + BM25 + RRF fusion)
- HyDE query enhancement for better retrieval
- Score justification generation with cited evidence
- IC Meeting Prep package generation across all 7 dimensions
- Dynamic leadership signals via Wikidata + Wikipedia enrichment

---

## 🏗 System Architecture Overview

```text
+---------------------------+               +--------------------------------+
|          User             |               |       Airflow (8081)           |
| (Private Equity Analyst)  |               | dags/evidence_indexing_dag.py  |
+------------+--------------+               +---------------+----------------+
             |                                              |
             | (search, justify, IC prep)                   | (scheduled indexing)
             v                                              v
+---------------------------+               +--------------------------------+
|    Streamlit (8501)       | <-----------> |        FastAPI (8000)          |
| streamlit_app/app.py      |   REST calls  |   app.main:app + routers       |
+------------+--------------+               +---------------+----------------+
             |                                              |
             |                              +---------------+----------------+
             |                              |     CS4 Service Layer          |
             |                              |--------------------------------|
             |                              | src/services/search/           |
             |                              |   vector_store.py              |
             |                              | src/services/retrieval/        |
             |                              |   hybrid.py (Dense+BM25+RRF)   |
             |                              |   hyde.py (query enhancement)  |
             |                              | src/services/justification/    |
             |                              |   generator.py                 |
             |                              | src/services/integration/      |
             |                              |   cs1_client.py                |
             |                              |   cs2_client.py                |
             |                              |   cs3_client.py                |
             |                              +---------------+----------------+
             |                                              |
             v                                              v
+---------------------------+               +--------------------------------+
|    ChromaDB (local)       |               |         Snowflake DB           |
|  chroma_data/             |               |   companies, signals,          |
|  Dense vector index       |               |   assessments, dimension       |
|  BM25 sparse index        |               |   scores, evidence             |
+---------------------------+               +--------------------------------+
                                                           ^
                                                           |
                                       +-------------------+------------------+
                                       |         Evidence Layer (CS2)         |
                                       |  app/pipelines/ + app/routers/       |
                                       |--------------------------------------|
                                       | SEC EDGAR → S3 → parse → chunk      |
                                       | board_collector.py (dynamic CIK)    |
                                       | patent_signals.py (dynamic USPTO)   |
                                       | leadership_signals.py (Wikidata)    |
                                       | glassdoor_collector.py              |
                                       | pipeline.py (on-demand onboarding)  |
                                       +--------------------------------------+

Storage:
- ChromaDB: dense vector index + BM25 sparse index for hybrid search
- Snowflake: companies, signals, dimension scores, evidence metadata
- AWS S3: raw/parsed SEC documents

Ports:
- FastAPI: 8000 | Streamlit: 8501 | Airflow: 8081
```

---

## 🔍 CS4 Core Components

### 1️⃣ Integration Layer

Connects CS4 to all upstream case studies.

**CS1 Client** — fetches company metadata (ticker, sector, market cap)
**CS2 Client** — loads evidence chunks with source type, confidence, dimension
**CS3 Client** — retrieves dimension scores, rubric criteria, level keywords

---

### 2️⃣ Multi-Provider LLM Router (LiteLLM)

Routes LLM calls across providers with fallback:

```
Primary: Claude (Anthropic)
Fallback: GPT-4 (OpenAI)
```

Supports:
- Score justification generation
- IC meeting prep synthesis
- Evidence quality assessment

---

### 3️⃣ Hybrid Retrieval (Dense + BM25 + RRF)

**Dense retrieval** — ChromaDB with sentence-transformers embeddings (semantic similarity)

**BM25 sparse retrieval** — keyword-based exact matching

**RRF Fusion** — Reciprocal Rank Fusion combines both rankings for best results

```
Final Score = 1/(k + rank_dense) + 1/(k + rank_bm25)
```

Filters available:
- `company_id` — filter by ticker
- `dimension` — filter by AI readiness dimension
- `min_confidence` — minimum evidence confidence threshold
- `top_k` — number of results

---

### 4️⃣ HyDE Query Enhancement

HyDE (Hypothetical Document Embedding) improves retrieval by:

1. Taking the original query
2. Generating a hypothetical answer with LLM
3. Embedding the hypothetical answer
4. Using it to retrieve real evidence

Result: better semantic matching for complex PE questions.

---

### 5️⃣ Score Justification Generator

For any company + dimension combination, generates:

- Score and rubric level (1-5)
- 95% confidence interval
- Evidence strength (strong/moderate/weak)
- Rubric criteria matched
- Supporting evidence items with citations
- Gaps preventing a higher score
- LLM-generated IC-ready summary (150-200 words)

---

### 6️⃣ IC Meeting Prep Workflow

Generates a complete Investment Committee package:

- Portfolio Org-AI-R score
- Executive summary
- Key strengths (top 3)
- Key gaps (top 3)
- Risk factors
- Recommendation (PROCEED / PROCEED WITH CAUTION / DO NOT PROCEED)
- Dimension-by-dimension justifications

---

### 8️⃣ Dynamic Signal Collection 

**Board Governance** — dynamic CIK lookup via SEC official ticker map for any company

**Patent Signals** — dynamic USPTO name resolution via SEC EDGAR + USPTO assignee API

**Leadership Signals** — 3-source enrichment:
- SEC DEF 14A proxy statements (board governance)
- Wikidata — current C-suite and board members for any public company
- Wikipedia — AI background detection from executive articles

---

## 📡 API Endpoints

### Search
```
GET /api/v1/search
  ?query=AI talent hiring machine learning
  &company_id=NVDA
  &dimension=talent
  &top_k=10
  &min_confidence=0.8
```

### Score Justification
```
GET /api/v1/justification/{ticker}/{dimension}
```

### IC Meeting Prep
```
POST /api/v1/justification/{ticker}/ic-prep
Body: { "focus_dimensions": ["data_infrastructure", "talent"] }
```

---

## 🗄 Infrastructure & Persistence

### Vector Database
- ChromaDB (local, `./chroma_data`)
- Dense embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- BM25 sparse index in-memory

### Database
- Snowflake (primary analytics storage)

### Document Storage
- AWS S3 for SEC filings & raw documents

### Orchestration
- Airflow DAG (`evidence_indexing_dag.py`)
- Batch evidence indexing automation

### Containerization
- Dockerfile + docker-compose.yml

---

## 📂 Project Structure

```bash
PE_ORGAIR_CASESTUDY4/
│
├── app/                          # FastAPI application layer
│   ├── pipelines/
│   │   ├── board_collector.py    # Dynamic CIK lookup (any company)
│   │   ├── patent_signals.py     # Dynamic USPTO name lookup
│   │   ├── leadership_signals.py # Wikidata + Wikipedia enrichment
│   │   └── ...
│   ├── routers/
│   │   ├── search.py             # Evidence search endpoint
│   │   ├── justification.py      # Score justification endpoint
│   │   ├── pipeline.py           # On-demand onboarding (NEW)
│   │   └── signals.py            # Signal collection
│   └── services/
│
├── src/
│   ├── services/
│   │   ├── integration/          # CS1/CS2/CS3 clients
│   │   ├── retrieval/
│   │   │   ├── hybrid.py         # Dense + BM25 + RRF fusion
│   │   │   └── hyde.py           # HyDE query enhancement
│   │   ├── search/
│   │   │   └── vector_store.py   # ChromaDB wrapper
│   │   └── justification/
│   │       └── generator.py      # Score justification LLM
│
├── dags/
│   └── evidence_indexing_dag.py  # Airflow batch indexing
│
├── scripts/
│   └── index_evidence.py         # Dynamic evidence indexing (any ticker)
│
├── streamlit_app/
│   ├── app.py                    # Full dashboard + CS4 pages
│   └── api_client.py             # API client with CS4 methods
│
├── tests/                        # 81 passing tests
├── results/                      # Scoring outputs (NVDA, JPM, WMT, GE, DG)
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## ▶️ How to Run

### Install Dependencies

```bash
poetry install
poetry run scrapling install  # install browser for stealth scraping
```

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=...
SNOWFLAKE_ACCOUNT=...
SNOWFLAKE_USER=...
SNOWFLAKE_PASSWORD=...
SNOWFLAKE_DATABASE=...
SNOWFLAKE_WAREHOUSE=...
USPTO_API_KEY=...

# Optional
OPENAI_API_KEY=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
REDIS_URL=...
```

### Index Evidence

```bash
# Index original 5 companies
poetry run python scripts/index_evidence.py

# Index any new company
poetry run python scripts/index_evidence.py AAPL
poetry run python scripts/index_evidence.py MSFT GOOGL TSLA
```

### Run Tests

```bash
poetry run pytest  # 81 tests, 1 skipped
```

### Run the Application

#### Start FastAPI Backend

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API available at:
- http://localhost:8000
- Swagger Docs: http://localhost:8000/docs

#### Start Streamlit Dashboard

```bash
poetry run streamlit run streamlit_app/app.py
```

Streamlit available at:
- http://localhost:8501

#### Run Airflow

```bash
docker-compose up --build
```

Airflow available at:
- http://localhost:8081

---

## 🧪 Testing & Validation

- 81 unit and integration tests passing
- All 3 CS4 endpoints verified (Search, Justification, IC Prep)
- All 5 original tickers × 7 dimensions = 35 combinations tested
- New companies tested: MSFT, AMZN, JNJ, AAPL

---

## 👥 Team Contributions

### Ayush Fulsundar
- CS1/CS2/CS3 Integration clients
- Hybrid retrieval (Dense + BM25 + RRF)
- HyDE query enhancement
- Vector store (ChromaDB)
- Evidence indexing pipeline
- Airflow evidence indexing DAG

### Ishaan Samel
- Score Justification Generator
- IC Meeting Prep Workflow
- Analyst Notes Collector
- LiteLLM multi-provider router
- Justification API endpoint
- Streamlit CS4 pages (Evidence Search, Score Justification, Analyst notes)

### Vaishnavi Srinivas
- On-demand company onboarding pipeline 
- Dynamic CIK lookup for board governance
- Dynamic USPTO name resolution for patents
- Wikidata + Wikipedia leadership enrichment


---

## 🤖 AI Usage Disclosure

AI tools used during development:

- ChatGPT — debugging, architectural refinement, documentation structuring
- Claude — debugging support, structured test refinement, implementation assistance

---

## 📜 License

Academic project for QuantUniversity — Spring 2026
