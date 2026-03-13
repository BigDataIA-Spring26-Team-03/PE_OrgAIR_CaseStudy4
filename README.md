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

|  Architecture Diagram Link | [DrawIo](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&dark=auto#R%3Cmxfile%3E%3Cdiagram%20name%3D%22Page-1%22%20id%3D%22vvvNC2ssrUZW0RcfceHz%22%3E1Vxdc6M2FP01zLQPyQDiw35MbCdNm53NhHa2fcooINtqMKICx3F%2FfSVAGIRsEyI3TnYmCxcB0jnS1blXIgaYrN5uKUyX30iEYsM2ozcDTA3btkaOy%2F7jlm1p8cZ%2BaVhQHFWFdoYA%2F4sqo1lZ1zhCWatgTkic47RtDEmSoDBv2SClZNMuNidx%2B60pXKCOIQhh3LX%2BwFG%2BLK0j29%2FZf0F4sRRvtrxxeWUFReGqJdkSRmTTMIGZASaUkLw8Wr1NUMzBE7iU993suVpXjKIk73OD3b2hekaWb0Vzc%2FTGrl0v81XMDBY7nJMkr2ixPHFe3cCvwxgvEnYcsqciygzlM19hvK6eOQkcZjBmtjEyjTE%2FfpixX9%2Fp4uLq7uKRHQbbLEcrdnBFwyXOGY9riqrnIMrq1Khu1bhbRFYop1tWZNnAH1Rgb3ZceWZlE08R59t2T4NVT1nUT96ByQ4qPPeQYX4cXEsB7hzH8YTEhOE6TUjCzNdZTskLkowdzKcwhxxYsqYhGz62%2BdPsjdGTwPjnQbjaXVztDq4tWF0dsCo6eRdWStZJhKIKsg3vQEEKQ351w5ySBKNhg7nL%2F3WwZFe84qciomEvfxSEdYAPZqxV5mx6e8U6tsduZbCAa8u8%2BI17HxzjZJENYsDtMmBZbQbsNgNjHQz08hpnxcAfwcPv37kvebhrMHB1V7QiZ60Yhr93HH9LTHYVASMdBIAvR8AP%2FIKj0v%2FwZtomN6QowrDBB3pD4TrHr4i3jRJWPaSPF1saF76pnxfny%2FFyG8Msiwi7cUdDuI7Ludak6BWjzcl8k2O2x4YW5%2BR%2BOQ7ucfKCorukHht3rG6scjtG%2FibPvEkkywdPFaohAdp0uK7%2BIQEr7FHUkdRdfgph0p7lG5zxRwgdRGi%2BJAvCpMtsZ%2B0iq4aFohgWXqYVFygaWd36QDCr6X6t6Es45ZAuUF7dJUFVV6MfevZA9OwB6LEH0u2f7LJ5CVjAUhn%2BYoYL89IEwjDlMJj12bZ59oAoZs3jkr8wlrUo8WjLEX0k9e6JYCCW4GNYesWgb2HpfHksnYFYOucyqq8ohdtGgZSP1mz%2FoHc8adB7UmAtlZd9qVSeHZQ16Hn3CV2MO5BK92PDYmz68rCwv%2FqwEG8%2BrD2yDV7FsAjRm9LAPhLqMy0QuWgUOb3j%2FUnADc0cy%2BwVRygJubRjN8cozDFJBskJS%2FDf0BO%2B09YTF86RXqyYax9ZnWCyiJFxNIdjjSVFL7%2FNbb8NxkWyI0fXXPxlHxw3qmFSZ%2FU%2BIDT3cMyujOxnUAvNg4LymUAaPYUlw4ReptuGloy2CVzhkHeBO55%2FiAl5WaeDOsHouMQHbVKABklpK9IP54J8mUx4yvCCeb5sH%2FAiG8HOh2U0e4h5yzsB8oq8w7kgHyMYIZotcapGv5WAYLc3ExCaGJDcH7BOwIAiw3AuDGQofEoZpDFOUBv7KtMZLtfJSyamJM8Y8wcEYBD%2Bfhd%2FOffs%2BPrxh94wtaTgqK%2FwbUob8GnSBpxY2iCLdUH%2FHdIGSNImCAnFyYKLnGTBeuAwVWN2u5XvSqpG0ubg0FrRAFXjHVQ1nbfpVTVA0Z2BBv%2FSM30mL3up0mmdvoAqUfu0gmnK4oKd3%2FFZwYhFC0nGZK6%2BtJnIWqrXuHS4GaCQOOdOA10%2FUxw%2BZWwctkiI0Wux%2FG%2BJ0QrckzFxArUJFJrn3Kl4pYZIJS%2F5YQjjcM0mBEKzBjFZERxc1FPFiUixZX%2BpgxSFDDp3UrJtguhiW%2BvPkCRzEY3XnIwZdm4RmrFfPwWzb8NW5hXqqA7YhTo9gToCirWXT6RFyA3zPTTtdqDUpMwxE2a8Cdy1DeLD7SZLrFF7nndN%2FXzAakPSe9WqgrMhalXEQ5%2BcugXyrDA%2BnLo9Ur6duh2gsQQsJ8sSQjSah%2B%2BQ0vJOrMer28JLeXCVFneYAYI0XA7q%2BpbCF3lS5k6W1I7j7u8DfTu%2Fo%2BjrjgZntAde7ozCEXqe9wmVWX9DCwrL7KsZw21LMU0CVvWbInt7UwY6YYy17lGRc0X6XY%2BjULDngv5y%2B8z3mXK%2Fk1OMXrlzr8GfsmgB1ZP09bdiOi5PHh9vtHl%2FmQHX1U%2BBQrmeCwV%2Fr7Mcz3EohsACJQ0O7lkd7u%2B%2F7aQSzouCAzeiHIf%2FFKk6R6FRzwX%2BO74fcYVQXmZMUorSBvywaIeG4FmBvG3Zl20h6nj%2B5Qk6v0KK6kB%2FPp%2FboRL9yHv23F6JUsiU0zbjiiMhOWqGZHyHz8X9dy7%2B0W6pjkcK%2FGGXpi4W5FS11P3rNNiHGPDOl4FftlO%2B2xwlS8ggXvH67Uj4Z40KDPEqpeS1unoit%2B%2B5JwDeP1%2FgSVKsTfLaVSsFTb%2BTcAj%2FCC5inOV8%2F5uZ4%2FCFS6P%2Fx%2BvrQX90vuhPlpSs4JRPqZi9%2Fa25OKmQPZo8PpD8vXuCPg8r1N8b6Yqx8r5dLG84LzaxVMd%2FVSzy493WFX4idq4YndjYtTrsqNHVv3dr%2FBlQXVrA6g0XPzm%2Bz8e1dUM4LL0gBa%2Fi06K96QW5PBgdLO%2BM3UPlP5yOENU5m8%2BUHijKWE1EaHBfRscDnFGP75NsmQsNiQf3wHj60ASAvD0TgD9%2BNs0elHSgDnKK4CrGvLtNYbYUk7MBrkauaTXmh8bOMZEMMo2JbRRrbL9K0Vx9oYgzHoroYmf8LjTAAEoVySR5Fvc8DfOJ8C1fgMMbmOXFZ00Faybv4DVrrJlZhy1mlMPv5rWdMGuZq001g1gbKwailALseEUdLHq9XFu2hCk%2FDLcxV0UU7ONSYqZnerXWXAe1lhBkesaEvAvPl1Laro4Eq9fLz50W3SAhm3kMX5phREhWKUxw8YVr3YPr7tsw8eWcYR1aBbkUUvvS1OI4Ojp0L7fUG%2FJeq2wV9EeDi6sfgVFu56qZoHDDTcXXrxEJ16vBSWwV4OAw4EAH4FAMpHer5SFLaBGbguvpxOgIXuHOPiFmEJ9j9YJBZ5O1h0nDNL6vHsz7NLtvu4fKH%2Fn6o%2FM2OUIuO5qWrz%2FEl2L%2Fy4bGY2SfR0DnS1LErsgcGHCx093f8yiL7%2F4qCpj9Bw%3D%3D%3C%2Fdiagram%3E%3C%2Fmxfile%3E#%7B%22pageId%22%3A%22vvvNC2ssrUZW0RcfceHz%22%7D) |
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
