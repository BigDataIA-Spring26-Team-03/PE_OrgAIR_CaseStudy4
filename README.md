# Case Study 3: AI Scoring Engine

**"From Evidence to Calibrated AI Readiness Scores"**

**Course:** Big Data and Intelligent Analytics  
**Instructor:** Professor Sri Krishnamurthy  
**Term:** Spring 2026

**Team 3:**
- Ishaan Samel
- Ayush Fulsundar
- Vaishnavi Srinivas

---

## 🧠 Project Overview

Case Study 3 implements the **Organizational AI-Readiness (Org-AI-R) Scoring Engine** for the PE-OrgAIR platform.

**Building on:**
- **Case Study 1** → Platform foundation
- **Case Study 2** → Evidence ingestion layer

This case study transforms structured evidence into a **risk-adjusted, sector-calibrated, confidence-bounded AI readiness score**.

### Key Focus Areas

Unlike CS2, which focuses on collecting evidence, **CS3 focuses on:**

- Dimension-level scoring
- Risk adjustments
- Position normalization
- Synergy modeling
- Confidence interval estimation

The final output is a **statistically defensible Org-AI-R score** suitable for private equity benchmarking.

---

## 📊 Scoring Framework Overview

As defined in the Scoring Engine specification (Sections 1–4), the Org-AI-R framework consists of:

1. **Dimension Scoring**
2. **Vᴿ** (Idiosyncratic AI Readiness)
3. **Position Factor (Pᶠ)**
4. **Hᴿ** (Relative AI Strength)
5. **Synergy Adjustment**
6. **SEM-Based Confidence Interval**

### The Final Formula
```
Org-AI-R = (1 − β) × Weighted Components + β × Synergy
```

**Where:**
- α = 0.60 (dimension emphasis)
- β = 0.12 (synergy weight)
- δ = 0.15 (position amplification factor)

---

## ⚖️ System Architecture

### High-Level Flow
```
CS1 Platform
     ↓
CS2 Evidence Signals
     ↓
CS3 Scoring Engine
     ↓
Org-AI-R + Confidence Interval
     ↓
Persist Back to Platform
```

### Detailed Pipeline
```
Evidence Signals (CS2)
    ↓
Evidence → Dimension Mapping (7 Dimensions)
    ↓
Rubric-Based Dimension Scoring
    ↓
Talent Concentration Calculation
    ↓
Vᴿ Computation (with CV Penalty)
    ↓
Position Factor (Sector Relative)
    ↓
Hᴿ Adjustment
    ↓
Synergy Calculation
    ↓
Org-AI-R Final Score
    ↓
SEM Confidence Interval
```

---

## 📂 Project Structure
```
PE_OrgAIR_CaseStudy3/
├── src/
│   ├── scoring/
│   │   ├── evidence_mapper.py          # Evidence-to-dimension mapping
│   │   ├── rubric_scorer.py            # Rubric-based evaluation
│   │   ├── vr_calculator.py            # Idiosyncratic readiness
│   │   ├── position_factor.py          # Sector-relative positioning
│   │   ├── hr_calculator.py            # Relative AI strength
│   │   ├── synergy_calculator.py       # Interaction effects
│   │   ├── talent_concentration.py     # Key-person risk
│   │   ├── confidence.py               # SEM confidence intervals
│   │   └── orgair_calculator.py        # Final score composition
│   │
│   ├── pipelines/
│   │   ├── glassdoor_collector.py      # Culture data ingestion
│   │   └── board_analyzer.py           # Governance assessment
│   │
│   └── integration_service.py          # Platform integration
│
├── tests/                              # Unit & property-based tests
├── results/                            # Scoring outputs
└── README.md                           # Project documentation
```

---

## 🔧 Core Components Implemented

### 1️⃣ Evidence-to-Dimension Mapping (Task 5.0a)

CS2 produced **4 signal categories**.  
CS3 requires **7 scoring dimensions**:

1. 🗄️ Data Infrastructure
2. ⚖️ AI Governance
3. 💻 Technology Stack
4. 👥 Talent
5. 🎯 Leadership
6. 📋 Use Case Portfolio
7. 🌟 Culture

#### Implementation Details

- Weighted signal-to-dimension mapping matrix
- Primary and secondary weight allocation
- Reliability-adjusted aggregation
- Confidence propagation
- Default score of 50 if evidence is missing
- Property-based tests to ensure boundedness [0,100]

This aligns with the dimension mapping table defined in the framework.

---

### 2️⃣ Rubric-Based Scoring (Task 5.0b)

Each dimension is evaluated using **5-level rubric criteria**.

**Scoring process:**

1. Normalize evidence text
2. Evaluate quantitative indicators
3. Match rubric keywords
4. Assign level (1–5)
5. Interpolate within score band

This ensures **qualitative evidence** translates into **calibrated numerical scores**.

---

### 3️⃣ Culture & Governance Enrichment (Tasks 5.0c & 5.0d)

#### 🌟 Glassdoor Culture Collector

**Extracts:**
- Innovation sentiment
- Data-driven orientation
- AI awareness
- Change readiness

**Implements:**
- Recency weighting
- Employee status multiplier
- Confidence scaling

#### ⚖️ Board Composition Analyzer

**Governance scoring based on:**
- Digital/AI committee presence
- AI expertise at board level
- CAIO/CDO/CTO presence
- Risk oversight mechanisms
- AI integration in strategy

**Scoring Range:**
- Base governance score: 20
- Maximum: 100

---

### 4️⃣ Talent Concentration (Task 5.0e)

Models **key-person dependency risk**.

**Formula:**
```
TC = 0.4 × leadership_ratio +
     0.3 × team_size_factor +
     0.2 × skill_concentration +
     0.1 × individual_mentions
```

**Bounded:** [0,1]

**Risk adjustment applied to Vᴿ:**
```
TalentRiskAdj = 1 − 0.15 × max(0, TC − 0.25)
```

Higher concentration reduces effective readiness.

---

## 📈 Vᴿ – Idiosyncratic AI Readiness

**Vᴿ** combines dimension scores using sector-specific weights.

**Includes:**
- Coefficient of Variation (CV) penalty
- Talent concentration penalty

**CV penalty:**
```
penalty = 1 − 0.25 × CV
```

Encourages **balanced AI capability** across dimensions.

All calculations use `Decimal` for **financial-grade precision**.

---

## 📊 Position Factor (Pᶠ)

AI readiness must be evaluated **relative to sector peers**.

**Formula:**
```
PF = 0.6 × VR_component + 0.4 × MarketCap_component
```

**Bounded:** [-1,1]

This measures **relative AI standing** within industry context.

---

## 📉 Hᴿ Adjustment

Position-adjusted readiness:
```
Hᴿ = HR_base × (1 + δ × PF)
```

**Where:** δ = 0.15

Leaders receive **amplification**; laggards are **penalized**.

---

## 🔄 Synergy Component

Captures **interaction** between readiness and relative position.
```
Synergy = (Vᴿ × Hᴿ / 100) × Alignment × TimingFactor
```

Weighted into final score using **β = 0.12**.

---

## 📐 Final Org-AI-R Score
```
Org-AI-R = (1 − β) × weighted_components + β × synergy
```

**Where:**
- **α** = 0.60 (dimension emphasis)
- **β** = 0.12 (synergy weight)
- **δ** = 0.15 (position amplification)

---

## 📏 Confidence Interval (SEM)

Implements **reliability-based uncertainty modeling** using:

- Spearman-Brown correction
- Standard Error of Measurement (SEM)

**Outputs:**
- Lower bound
- Upper bound
- Confidence score

Ensures **statistical defensibility** of results.

---

## 🧪 Testing & Validation

Our implementation includes:

- Property-based testing (Hypothesis)
- Deterministic scoring
- Bounds validation (0–100)
- Portfolio validation across 5 companies

---

## 📊 Portfolio Results

Validated against expected ranges:

| Company | Expected Maturity | Score Range |
|---------|------------------|-------------|
| **NVIDIA** | High AI maturity | 85-95 |
| **JPMorgan** | Strong enterprise AI | 75-85 |
| **Walmart** | Operational AI deployment | 65-75 |
| **GE** | Industrial AI transformation | 60-70 |
| **Dollar General** | Limited AI capability | 40-50 |

Results align with benchmark expectations defined in the scoring framework.

---

## ▶️ How to Run

### Score a Single Company
```bash
poetry run python scripts/run_scoring.py --ticker NVDA
```

**Pipeline executes:**

1. Dimension mapping
2. Vᴿ computation
3. Position factor calculation
4. Hᴿ adjustment
5. Synergy modeling
6. Org-AI-R final score
7. Confidence interval estimation
8. Results persistence

---

## 🎥 Demo Video

Watch our complete scoring engine demonstration:

[![Demo Video](https://img.shields.io/badge/Watch-Demo%20Video-red?style=for-the-badge&logo=google-drive)](#) <!-- ADD YOUR GOOGLE DRIVE LINK HERE -->

[📹 View Demo Video](#) <!-- ADD YOUR GOOGLE DRIVE LINK HERE -->

---

## 📚 Interactive Codelab

Follow our step-by-step interactive tutorial:

[📖 **Open Codelab: AI Scoring Engine - From Evidence to Calibrated Scores**](<https://codelabs-preview.appspot.com/?file_id=1Iza8HTzKo2jdCG3gzKNTNFgZx7HNH_amvO5q0_4Bm_0#10>) 

---

## 🎯 What This Enables

Case Study 3 provides:

- **Risk-adjusted AI maturity scoring**
- **Sector-relative benchmarking**
- **Confidence-bounded analytics**
- **Structured AI-readiness modeling**
- **Private equity decision support**

This scoring engine enables portfolio managers to make **data-driven investment decisions** based on quantified AI readiness metrics.

---

## 🔗 Related Case Studies

- [**Case Study 1**: Platform Foundation](<https://github.com/BigDataIA-Spring26-Team-03/PE_OrgAIR_CaseStudy1>) 
- [**Case Study 2**: Evidence Collection](<https://github.com/BigDataIA-Spring26-Team-03/PE_OrgAIR_CaseStudy2>) 

---

## 📦 Requirements

See `requirements.txt` for full dependencies. Key packages:

- `snowflake-connector-python`
- `pandas`
- `numpy`
- `scipy`
- `hypothesis` (for property-based testing)
- `pydantic` (for data validation)
- `python-decimal` (for financial precision)

---

## 👥 Team Contributions


- **Ishaan Samel** – 
- **Ayush Fulsundar** – 
- **Vaishnavi Srinivas** – 

---

## 📝 License

Academic project for QuantUniversity — Spring 2026

- **Team Members** for collaborative development and validation

---

**Built with ❤️ by Team 3 | Spring 2026**
