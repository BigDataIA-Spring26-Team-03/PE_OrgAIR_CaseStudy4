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
| Demo Video | [Demo Video](https://youtu.be/ZU32gMl1m3g) |
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
- Analyst Notes Collector for post-LOI due diligence evidence
- On-demand company onboarding for any US-listed ticker
- Dynamic leadership signals via Wikidata + Wikipedia enrichment

---

## 🏗 System Architecture Overview

|  Architecture Diagram Link | [DrawIo](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=Untitled%20Diagram.drawio&dark=auto#R%3Cmxfile%3E%3Cdiagram%20name%3D%22Page-1%22%20id%3D%22mXZjyPXyZ2ihqhYl8gdt%22%3E1Vtdd9o4EP01nLP7QI%2B%2FMOaREEizTbc9od3uW46wBVZjW17ZQNhfvyN%2FW4hCHdF46Qk1smzke0ejO6NhYM7ClzuGYv8j9XAwMDTvZWDeDgxDd6wR%2FMdbDnmLPRnnDRtGvKJT3bAk%2F%2BKiUStat8TDSatjSmmQkrjd6NIowm7aakOM0X2725oG7W%2BN0QYfNSxdFBy3fiNe6uetjjGu299jsvHLb9btSX4mRGXn4kkSH3l032gy5wNzxihN86PwZYYDDl6JS37d4sTZamAMR%2BklFxjHFxT3SNJD%2BbgpfoFzN34aBtCgw%2BGaRmlBi%2B6Un4sL%2BHkUkE0Exy7cFTNoyO%2B5Q8G2uOdsaUHDYG4MHG0w4cef5%2FD2iW2G0%2FvhIxwuD0mKQziYMtcnKfC4Zbi4D2YwpsZwi4e7wzTEKTtAF7%2BBv1mAva%2B5GmtFW3EXo%2Fx8KD8X1lJYyqa6cw0mHBR4yrH1kkvATfYkDFCEBVRNCaprEgQzGlCWXWmuR%2FwftCcpo8%2B4PBPR6maNzvlLxsQtShGHm26ZC5OKPzl00mZLQyBovoNZF7mYn6RBAIQQGnUiRNeOGdH1SZuS4aRNyVgJJZIZUvLUIIXRbeRhr8B9z81vGSOXn92DS5Nwkb2OuIAzdvYS2NVlRCznM47y7d0UzN%2BGS8HdmTe6NvzAfRQJSLRJOsE9lqA9EuzfEOx%2FpAJsq79g3wUoSTwKF9ZQu9sg9zEawzuC993Qts%2BjbQnexlRi2qP%2Bov1Aomfs3UeZd1nA%2Bz2MAQZRY%2F%2BdrvjYaZJ2NvMLgB851wDe7i%2FwNxQxjy%2BujL4cGnDnvuZ2zrnQrWknvEejs3iPbQFv450Cx%2BImF8mWN19Zu62NErWiV43l2mi2cdUdBYYMsKJjXCuwX2PK3gg7niUzZcdYmZeZ8oqb8pObKw%2FK3sVNe%2B4EtSNB2mgDrZvqHQYguuoxzjFKYVBPCSh4FCRXgnksyA%2FbugbMbo9hDjDyMEt8El8Z6tJNl9pDdMlqoPZ6DPWm1HqnvEct%2FAoqlIHvtMG3zdE1wMc9Bj%2FB7lNMYgzhC26jXkQ2rr%2BNnpMy1rQHE36DpdmJgsl5ChxLvf3vPyT%2BV8Q2fy9WX%2Fd%2BEG7DBzwszaGXrHzBrs9hVmzuwuo51NVjjZ4ARPgrDAR7R6m6Y02YpTZOM8DvUapBylKfbiigMq9bC%2FxSoBhXTJpHoMoxYzhAKdm1R%2Fm6CW%2BeftQeyd8Zn8StDNLSpQzCOziaRxvwB53sTtclhqfZgqAQDE9F8ghwl%2Bpj8%2FVTGuswqceyKT2xxya6aErjIj33FKI4xs28xhg6eiTEUUJopG6yjwVhcQ1dYUqVck8QZ9sVI%2B5TAlbdwjvAu2zDQy9tn6%2F6mosCsmKoc9JURoFo9VeJVkypjO4JB389Dsqc0vvHHGVQcwgkXtJgJMlE37ByxTDu0hV1YEKWTxUnwxVWPsBcqrJ7wkRyiDDbHAblBoJLo3W5YVARMQGY%2BGSY3cPbb8v5x987MSBL9QkpElvMsSpJPJlSqf02DIir%2BBEjzc007qMaPKwJKBxop9s03qaqOIBgs8XBWFwTFHDA9Z8Jf0XC4Of13zFZ3fSfdYS3HLOL9V926ZQxdGh0iCmJ0qRx58%2B8oYZ4JITz1kTY8P25%2FnCQj6DmonqUC6eIZNOnl%2BJU3H9%2BnN5lvstGYZxdoS0xYjxM6iJSZZHoGZE6UrNIWFKRar3eRXkIO2tXuh%2FhOni1vmSRAFvEm1IEaQE6tITTbAnQLrKd50UePbgBwYX9K1kkrDYDo2ukYyypZu0JAf5hxWtsuFtKGcE7vgpU%2BN9CiICrBfzmY7ZU5x8eHxfKSBC0knEVrWRJVWtPWHh%2FuOXVLjjyEeijkA%2BwZuGfLc5gJGHM6K44qwh6W5CpYpysBnqpTO0J9N%2B3SUrWxC190AaDbOXxQoOBBxjJw8PHWsqSNOuuzg8JU8DWruKIpGK1Jzzc8w3oEOM0TwjFDMcNBlD2KAoSFzLwxYzwFaoxAOb1lcBfr9eGKwXfs1f26KJYDYG%2BPSRcFkY0xc1ImVdgDB8%2B3RcBHL%2FDO60T8o6kPEAwe3EXW1MSo1mbHiNPo1VRklFuijStPuIgfl0OA5KkvDxGS4n7zCVSB%2FxHl6y8zru249FVFD4C2H6PKZj5jIboljt2At%2F%2B0iDAkwigLk7nvOmLCSJVtk96DDyuC0iTIrTSpp%2FvG%2Fjfzb9k6C9QDA%2By2PFwIOkehcmmgFChJK68uq6oRMn63mMmRBF0ngXhCjVkGJqQLxLK8xSRwVNG1lNSqOifzxgdk9YlY1R%2B%2F1snjIRFd1z4uFMJoyrbLe%2F%2F6oRRTs4avS055fe%2FNTlizfsZchzjuuSUNvvjZF4HF4btEy5sPFlpmuDCjEuS3cuUYRQGhKNzixK%2FlFkDc%2BqMNL3h3hq%2FYygzfNpgZgyyfdI%2FBM9Yncjilc9ZlFI3fqrU3J94P%2BC%2FiwjjTMSpEQ2m016sROuwFYi1tSRd2FOKFyhJs5UqI1XjYVujXK4SCjU9x%2BtW61ytwBe1LG92eE01mIROS6xGFzRgFYi%2Bqhx99QPP2UjA%2Byjmh%2B4h4CKYmadoFTedTmTjTyXepVn6I2ZrSV4Rusu2bGuN3oECSyL%2FxPpevcRGZRLeWxn%2FPw6WEd2vA%2FTcDEirCVBPi6zaoduUuIgPYU5Yavi4rGKqV3xMvy0HeSGk8KsNj7rbsPOuiOznBedIqBae16nwyjX9GpXngQqolqxjyVeN5tdX8HEojK5QdNm%2FPguF8ZZQ%2FNJSzrNQ%2FKq6TvhY%2F8471%2Bb1r%2BXN%2BX8%3D%3C%2Fdiagram%3E%3C%2Fmxfile%3E#%7B%22pageId%22%3A%22mXZjyPXyZ2ihqhYl8gdt%22%7D) |
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
             |                              |   dimension_mapper.py          |
             |                              | src/services/justification/    |
             |                              |   generator.py                 |
             |                              | src/services/workflows/        |
             |                              |   ic_prep.py                   |
             |                              | src/services/collection/       |
             |                              |   analyst_notes.py             |
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
**Dimension Mapper** — maps evidence sources to the 7 Org-AI-R dimensions

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
- Analyst note summarization
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

### 7️⃣ Analyst Notes Collector

Indexes post-LOI due diligence evidence directly from PE analysts.

Supported note types:
- **Interview transcripts** — CTO, CDO, CFO conversations (confidence = 1.0)
- **Management meeting notes** — executive sessions (confidence = 1.0)
- **Site visit observations** — on-the-ground findings (confidence = 1.0)
- **DD findings** — due diligence investigation results (confidence = 1.0)
- **Data room summaries** — document repository analysis (confidence = 0.9)

Each note is tagged with:
- Dimensions discussed (maps to 7 Org-AI-R dimensions)
- Key findings and risk flags
- Assessor identity (audit trail)

Analyst notes are indexed into ChromaDB alongside SEC filings and signals, making them searchable and citable in justifications. Primary source confidence (1.0) means they rank highest in evidence retrieval.

---

### 8️⃣ On-Demand Company Onboarding

`POST /api/v1/pipeline/onboard/{ticker}`

Automatically onboards any US-listed company in 5 steps:

1. Register in Snowflake (dynamic industry mapping)
2. Collect SEC 10-K filings via EDGAR
3. Collect signals (jobs, patents, board governance, leadership)
4. Run CS3 scoring pipeline
5. Index evidence into ChromaDB

Works for **any** US-listed ticker — not just the original 5.

Tested: MSFT (351 items, 64.0), AMZN (391 items, 61.4), JNJ (127 items, 56.1), AAPL (227 items, 67.0)

---

### 9️⃣ Dynamic Signal Collection

**Board Governance** — dynamic CIK lookup via SEC official ticker map for any company

**Patent Signals** — dynamic USPTO name resolution via SEC EDGAR + USPTO assignee API. Uses `_text_phrase` search instead of exact match.

**Leadership Signals** — 3-source enrichment:
- SEC DEF 14A proxy statements (board governance)
- Wikidata — current C-suite and board members for any public company
- Wikipedia — AI background detection from executive articles (detects PHD, AI company veteran, ML keywords)

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

### On-Demand Onboarding
```
POST /api/v1/pipeline/onboard/{ticker}?sector=Technology
GET  /api/v1/pipeline/onboard/{ticker}/status
GET  /api/v1/pipeline/supported-sectors
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
│   │   ├── pipeline.py           # On-demand onboarding
│   │   └── signals.py            # Signal collection
│   └── services/
│
├── src/
│   ├── services/
│   │   ├── integration/          # CS1/CS2/CS3 clients
│   │   │   ├── cs1_client.py
│   │   │   ├── cs2_client.py
│   │   │   └── cs3_client.py
│   │   ├── retrieval/
│   │   │   ├── hybrid.py         # Dense + BM25 + RRF fusion
│   │   │   ├── hyde.py           # HyDE query enhancement
│   │   │   └── dimension_mapper.py
│   │   ├── search/
│   │   │   └── vector_store.py   # ChromaDB wrapper
│   │   ├── justification/
│   │   │   └── generator.py      # Score justification LLM
│   │   ├── workflows/
│   │   │   └── ic_prep.py        # IC meeting prep
│   │   └── collection/
│   │       └── analyst_notes.py  # Post-LOI due diligence notes
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

- 81 unit and integration tests passing (1 skipped intentional)
- All 3 CS4 endpoints verified (Search, Justification, IC Prep)
- All 5 original tickers × 7 dimensions = 35 combinations tested
- New companies tested: MSFT (351 items), AMZN (391 items), JNJ (127 items), AAPL (227 items)
- Evidence indexed: NVDA (435), JPM (1,756), WMT (317), GE (369), DG (797)

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
