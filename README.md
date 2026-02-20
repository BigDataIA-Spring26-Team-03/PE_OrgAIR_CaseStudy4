# PE Org-AI-R Platform  
## Case Study 3 — AI Scoring Engine  
### From Evidence to Calibrated AI Readiness Scores  

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
|------------|------|
| Demo Video | https://youtu.be/qa3jQ8_GIr0 |
| Interactive Codelab | https://codelabs-preview.appspot.com/?file_id=1Iza8HTzKo2jdCG3gzKNTNFgZx7HNH_amvO5q0_4Bm_0#10 |

---

## 📌 Executive Summary

Case Study 3 implements the Organizational AI-Readiness (Org-AI-R) Scoring Engine for the PE Org-AI-R platform.

Building on:

- Case Study 1 → Platform Foundation (FastAPI, Snowflake, Redis, Docker)  
- Case Study 2 → Evidence Collection & Signal Extraction  
- Case Study 3 → Risk-adjusted, sector-calibrated scoring engine  

The Org-AI-R engine transforms structured governance, technology, talent, culture, and external signals into:

- Risk-adjusted AI maturity scores  
- Sector-relative benchmarking  
- Interaction-based synergy modeling  
- SEM-based confidence intervals  
- Private equity decision-support metrics  

The final output is a statistically defensible AI readiness score suitable for portfolio benchmarking and investment evaluation.

---

## 🏗 System Architecture Overview

The system is composed of five major layers:

- Data Ingestion Layer (CS2)  
- FastAPI Backend (CS1 Foundation)  
- Org-AI-R Scoring Engine (CS3)  
- Persistence Layer (Snowflake + Redis + S3)  
- Visualization Layer (Streamlit)  
## 🏗 Architecture Diagram

```text
+----------------------------+                 +------------------------------+
|            User            |                 |        Airflow (8081)        |
|   (Private Equity Viewer)  |                 |  dags/org_air_scoring_dag.py |
+-------------+--------------+                 +--------------+---------------+
              |                                               |
              | (views scores, triggers runs)                 | (scheduled/batch runs)
              v                                               v
+----------------------------+                 +------------------------------+
|     Streamlit (8501)       | <-------------> |        FastAPI (8000)         |
| app/streamlit_app/app.py   |   REST calls    |   app.main:app + routers      |
+-------------+--------------+                 +--------------+---------------+
              |                                               |
              |                                               |
              |                                               v
              |                                +------------------------------+
              |                                |   Integration Service Layer  |
              |                                |  src/scoring/integration.py  |
              |                                +--------------+---------------+
              |                                               |
              |                                               v
              |                                +------------------------------+
              |                                |   Org-AI-R Scoring Engine    |
              |                                |        src/scoring/          |
              |                                |------------------------------|
              |                                | evidence_mapper.py           |
              |                                | rubric_scorer.py             |
              |                                | talent_concentration.py      |
              |                                | vr_calculator.py             |
              |                                | position_factor.py           |
              |                                | hr_calculator.py             |
              |                                | synergy_calculator.py        |
              |                                | confidence.py (SEM)          |
              |                                | org_air_calculator.py        |
              |                                +--------------+---------------+
              |                                               |
              v                                               v
+----------------------------+                 +------------------------------+
|     Redis Cache (optional) |                 |         Snowflake DB          |
|   app/services/redis_*.py  |                 |   app/services/snowflake.py   |
+----------------------------+                 +--------------+---------------+
                                                              ^
                                                              |
                                                              |  reads CS2 evidence/signals
                                                              |
                                      +-----------------------+------------------------+
                                      |                Evidence Layer (CS2)            |
                                      |              app/pipelines/ + scripts/         |
                                      |------------------------------------------------|
                                      | SEC EDGAR -> S3 -> parse -> chunk              |
                                      | glassdoor_collector.py  -> Snowflake           |
                                      | board_collector + llm_extractor -> Snowflake   |
                                      | external_signals_orchestrator -> Snowflake     |
                                      +-----------------------+------------------------+

Storage:
- AWS S3: raw/parsed SEC documents (used by CS2 pipelines)
- Snowflake: signals + scoring outputs + confidence bounds
- Redis: caching for repeated reads (optional)
Ports:
- FastAPI: 8000  | Streamlit: 8501 | Airflow: 8081

```

## 📊 Org-AI-R Scoring Framework

The scoring engine consists of:

- 7 Dimension Scores  
- Vᴿ (Idiosyncratic AI Readiness)  
- Position Factor (Pᶠ)  
- Hᴿ (Relative AI Strength)  
- Synergy Interaction  
- SEM-Based Confidence Interval  

---

## 🔢 Final Formula

Org-AI-R = (1 − β) × Weighted Components + β × Synergy  

Where:

- α = 0.60 (dimension emphasis)  
- β = 0.12 (synergy weight)  
- δ = 0.15 (position amplification factor)  

All numerical calculations use `Decimal` for financial-grade precision and reproducibility.

---

## 🧩 Core Scoring Components (CS3)

### 1️⃣ Evidence Mapper

Maps structured CS2 signals into 7 Org-AI-R dimensions:

- Data Infrastructure  
- AI Governance  
- Technology Stack  
- Talent  
- Leadership  
- Use Case Portfolio  
- Culture  

Features:

- Weighted signal-to-dimension mapping matrix  
- Primary & secondary weights  
- Reliability adjustment  
- Default midpoint score (50) if evidence absent  
- Property-based boundedness validation  

---

### 2️⃣ Rubric Scorer

Implements a 5-level calibrated rubric per dimension.

**Scoring Process:**

- Normalize evidence  
- Match qualitative keywords  
- Evaluate quantitative signals  
- Assign level (1–5)  
- Interpolate within score band  

Ensures qualitative inputs produce deterministic numerical outputs.

---

### 3️⃣ Talent Concentration Risk

Models key-person dependency:

TC = 0.4L + 0.3T + 0.2S + 0.1M  

Bounded to [0,1]

**Risk Adjustment:**

TalentRiskAdj = 1 − 0.15 × max(0, TC − 0.25)

High concentration reduces effective readiness.

---

### 4️⃣ Vᴿ – Idiosyncratic AI Readiness

- Weighted dimension aggregation  
- Coefficient of Variation (CV) penalty:

Penalty = 1 − 0.25 × CV  

Encourages balanced capability development.

Includes structured audit logging for traceability.

---

### 5️⃣ Position Factor (Pᶠ)

PF = 0.6 × VR_component + 0.4 × MarketCap_component  

Bounded to [-1,1]

Captures sector-relative AI standing.

---

### 6️⃣ Hᴿ Adjustment

Hᴿ = HR_base × (1 + δ × PF)

δ = 0.15  

Leaders are amplified; laggards are penalized.

---

### 7️⃣ Synergy Component

Synergy = (Vᴿ × Hᴿ / 100) × Alignment × TimingFactor  

Models interaction between readiness and sector position.

---

### 8️⃣ SEM-Based Confidence Interval

Implements:

- Spearman-Brown reliability correction  
- Standard Error of Measurement (SEM)  

Outputs:

- Lower bound  
- Upper bound  
- Confidence score  

Bounds clipped to [0,100].

Ensures statistical defensibility.

---

## 🗄 Infrastructure & Persistence

### Database
- Snowflake (primary analytics storage)  
- CS3 schema includes scoring results tables  

### Caching
- Redis for performance optimization  

### Document Storage
- AWS S3 for SEC filings & raw documents  

### Orchestration
- Airflow DAG (`org_air_scoring_dag.py`)  
- Supports batch scoring automation  

### Containerization
- Dockerfile  
- docker-compose.yml  

---

## 📂 Project Structure

```bash
PE_ORGAIR_CASESTUDY3/
│
├── app/                        # FastAPI application layer
│   ├── core/
│   ├── database/
│   ├── models/
│   ├── pipelines/
│   ├── routers/
│   ├── services/
│   └── streamlit_app/
│
├── src/
│   ├── scoring/                # Org-AI-R scoring engine
│   └── pipelines/
│
├── dags/                       # Airflow DAG
├── scripts/                    # Operational scripts
├── tests/                      # Unit + property tests
├── results/                    # Sample scoring outputs
├── docs/                       # Architecture diagrams
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## ▶️ How to Run

### Install Dependencies

```bash
poetry install
```

---

### Run Tests

```bash
poetry run pytest
```

---

### Run the Application

#### Start FastAPI Backend

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

FastAPI will be available at:
- http://localhost:8000  
- Swagger Docs: http://localhost:8000/docs  

---

#### Start Streamlit Dashboard

```bash
poetry run streamlit run app/streamlit_app/app.py
```

Streamlit will be available at:
- http://localhost:8501  

---

### Run Airflow (Orchestration Layer)


```bash
docker-compose up --build
```

Airflow will be available at:
- http://localhost:8081  

Airflow DAG:
- `org_air_scoring_dag.py`

Airflow enables:
- Scheduled batch scoring
- Automated pipeline orchestration
- Persistent scoring runs across companies

---

This executes the complete Org-AI-R scoring pipeline:
- Evidence retrieval  
- Dimension scoring  
- Vᴿ calculation  
- Position factor adjustment  
- Synergy modeling  
- Final Org-AI-R computation  
- SEM-based confidence interval estimation  
- Snowflake persistence  

---

### Service Ports Summary

- FastAPI → http://localhost:8000  
- Swagger Docs → http://localhost:8000/docs  
- Streamlit → http://localhost:8501  
- Airflow → http://localhost:8081  


### Score a Company


poetry run python scripts/run_scoring.py --ticker NVDA


---

### Pipeline Execution:

- Evidence retrieval  
- Dimension scoring  
- Vᴿ calculation  
- Position adjustment  
- Synergy modeling  
- Org-AI-R computation  
- Confidence interval estimation  
- Snowflake persistence  

---

## 🧪 Testing & Validation

Implemented:

- Unit tests  
- Property-based testing (Hypothesis)  
- Bounds validation (0–100)  
- Deterministic scoring checks  
- Portfolio validation across 5 companies  

---

## 👥 Team Contributions

### Ayush Fulsundar

- Evidence Mapper  
- Rubric Scorer (7 dimensions)  
- Board Composition Analyzer  
- Talent Concentration Calculator  
- Decimal utilities  
- VRCalculator with audit logging  
- Property-based tests  
- Integration Service (pipeline orchestration)  

### Ishaan Samel

- Glassdoor Culture Collector  
- Position Factor Calculator  
- HRCalculator (δ = 0.15)  
- SynergyCalculator  
- SEM-based Confidence Calculator  
- OrgAIRCalculator  
- Integration Service (pipeline orchestration)
- Streamlit  

### Vaishnavi Srinivas

- External signals data collection  

---

## 🤖 AI Usage Disclosure

AI tools used during development:

- ChatGPT — debugging, architectural refinement, documentation structuring, test case validation  
- Claude — debugging support and structured test refinement  

---

## 📜 License

Academic project for QuantUniversity — Spring 2026
