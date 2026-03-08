# src/services/integration/cs3_client.py
from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Dimension(str, enum.Enum):
    """The 7 V^R dimensions scored by CS3."""
    DATA_INFRASTRUCTURE = "data_infrastructure"
    AI_GOVERNANCE       = "ai_governance"
    TECHNOLOGY_STACK    = "technology_stack"
    TALENT              = "talent"
    LEADERSHIP          = "leadership"
    USE_CASE_PORTFOLIO  = "use_case_portfolio"
    CULTURE             = "culture"


class ScoreLevel(int, enum.Enum):
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    LEVEL_5 = 5

    @property
    def name_label(self) -> str:
        return {5: "Excellent", 4: "Good", 3: "Adequate", 2: "Developing", 1: "Nascent"}[self.value]

    @property
    def score_range(self) -> Tuple[int, int]:
        return {5: (80,100), 4: (60,79), 3: (40,59), 2: (20,39), 1: (0,19)}[self.value]

    @classmethod
    def from_score(cls, score: float) -> "ScoreLevel":
        for level in reversed(cls):
            low, _ = level.score_range
            if score >= low:
                return level
        return cls.LEVEL_1


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DimensionScore:
    dimension: Dimension
    score: float
    level: ScoreLevel
    confidence_interval: Tuple[float, float]
    evidence_count: int
    last_updated: str


@dataclass
class RubricCriteria:
    dimension: Dimension
    level: ScoreLevel
    criteria_text: str
    keywords: List[str]
    quantitative_thresholds: Dict[str, float] = field(default_factory=dict)


@dataclass
class CompanyAssessment:
    company_id: str
    assessment_date: str
    vr_score: float
    hr_score: float
    synergy_score: float
    org_air_score: float
    confidence_interval: Tuple[float, float]
    dimension_scores: Dict[Dimension, DimensionScore]
    talent_concentration: float
    position_factor: float


# ---------------------------------------------------------------------------
# Hardcoded rubrics (since /api/v1/rubrics doesn't exist)
# ---------------------------------------------------------------------------

HARDCODED_RUBRICS: Dict[str, Dict[int, RubricCriteria]] = {
    "data_infrastructure": {
        5: RubricCriteria(Dimension.DATA_INFRASTRUCTURE, ScoreLevel.LEVEL_5,
            "Best-in-class data mesh architecture, >90% data quality, automated data contracts, real-time streaming at scale.",
            ["data mesh", "streaming", "data contract", "mlops", "lakehouse", "automated", "observability"]),
        4: RubricCriteria(Dimension.DATA_INFRASTRUCTURE, ScoreLevel.LEVEL_4,
            "Hybrid cloud infrastructure with 70-90% data quality. Centralized data platform, real-time pipelines, ML feature store.",
            ["cloud", "data pipeline", "data quality", "data lake", "feature store", "real-time", "governance", "etl", "warehouse"]),
        3: RubricCriteria(Dimension.DATA_INFRASTRUCTURE, ScoreLevel.LEVEL_3,
            "Basic data infrastructure with some cloud adoption. Ad-hoc pipelines, limited data quality controls.",
            ["cloud", "database", "pipeline", "analytics"]),
        2: RubricCriteria(Dimension.DATA_INFRASTRUCTURE, ScoreLevel.LEVEL_2,
            "On-premise legacy systems, quality <50%, siloed data stores.",
            ["legacy", "silos", "on-premise"]),
        1: RubricCriteria(Dimension.DATA_INFRASTRUCTURE, ScoreLevel.LEVEL_1,
            "No modern infrastructure, fragmented data, manual processes.",
            ["mainframe", "spreadsheets", "manual"]),
    },
    "ai_governance": {
        5: RubricCriteria(Dimension.AI_GOVERNANCE, ScoreLevel.LEVEL_5,
            "CAIO/CDO reports to CEO, board AI committee, comprehensive model risk management framework.",
            ["caio", "cdo", "board committee", "model risk"]),
        4: RubricCriteria(Dimension.AI_GOVERNANCE, ScoreLevel.LEVEL_4,
            "VP-level AI sponsor, documented AI policies, risk assessment process in place.",
            ["vp data", "ai policy", "risk framework"]),
        3: RubricCriteria(Dimension.AI_GOVERNANCE, ScoreLevel.LEVEL_3,
            "Director-level ownership, basic policies exist, IT-led governance structure.",
            ["director", "guidelines", "it governance"]),
        2: RubricCriteria(Dimension.AI_GOVERNANCE, ScoreLevel.LEVEL_2,
            "Informal governance only, no documented policies, ad-hoc oversight.",
            ["informal", "no policy", "ad-hoc"]),
        1: RubricCriteria(Dimension.AI_GOVERNANCE, ScoreLevel.LEVEL_1,
            "No governance structure, no AI oversight, unmanaged risk exposure.",
            ["none", "no oversight", "unmanaged"]),
    },
    "technology_stack": {
        5: RubricCriteria(Dimension.TECHNOLOGY_STACK, ScoreLevel.LEVEL_5,
            "Full MLOps platform (SageMaker, Vertex AI), feature store, model registry, automated pipelines.",
            ["sagemaker", "mlops", "feature store", "vertex ai", "model registry"]),
        4: RubricCriteria(Dimension.TECHNOLOGY_STACK, ScoreLevel.LEVEL_4,
            "ML platform adopted (Databricks ML, MLflow), experiment tracking, partial automation.",
            ["mlflow", "kubeflow", "databricks ml", "experiment tracking"]),
        3: RubricCriteria(Dimension.TECHNOLOGY_STACK, ScoreLevel.LEVEL_3,
            "Basic ML tools in use, manual deployment, notebook-based development.",
            ["jupyter", "notebooks", "manual deploy"]),
        2: RubricCriteria(Dimension.TECHNOLOGY_STACK, ScoreLevel.LEVEL_2,
            "Spreadsheet-based analytics only, no ML tooling, basic BI tools.",
            ["excel", "tableau only", "no ml"]),
        1: RubricCriteria(Dimension.TECHNOLOGY_STACK, ScoreLevel.LEVEL_1,
            "No analytics capability, manual reporting processes.",
            ["manual", "no tools"]),
    },
    "talent": {
        5: RubricCriteria(Dimension.TALENT, ScoreLevel.LEVEL_5,
            "Large AI/ML team (>20 specialists), <10% turnover, internal ML platform team, research capability.",
            ["ml platform", "ai research", "large team", "principal ml", "staff ml"]),
        4: RubricCriteria(Dimension.TALENT, ScoreLevel.LEVEL_4,
            "Established team (10-20 professionals), active hiring pipeline, retention programs.",
            ["data science team", "ml engineers", "active hiring", "retention"]),
        3: RubricCriteria(Dimension.TALENT, ScoreLevel.LEVEL_3,
            "Small team (3-10 data scientists), growing capability, some turnover challenges.",
            ["data scientist", "growing team"]),
        2: RubricCriteria(Dimension.TALENT, ScoreLevel.LEVEL_2,
            "1-2 data scientists, high turnover rate, limited technical depth.",
            ["junior", "contractor", "turnover"]),
        1: RubricCriteria(Dimension.TALENT, ScoreLevel.LEVEL_1,
            "No dedicated AI/ML talent, dependent on vendors/contractors.",
            ["no data scientist", "vendor only"]),
    },
    "leadership": {
        5: RubricCriteria(Dimension.LEADERSHIP, ScoreLevel.LEVEL_5,
            "CEO publicly champions AI, board AI/tech committee, documented multi-year AI strategic plan.",
            ["ceo ai", "board committee", "ai strategy"]),
        4: RubricCriteria(Dimension.LEADERSHIP, ScoreLevel.LEVEL_4,
            "C-suite sponsor (CTO/CDO), AI in strategy documents, executive engagement.",
            ["cto ai", "strategic priority", "executive"]),
        3: RubricCriteria(Dimension.LEADERSHIP, ScoreLevel.LEVEL_3,
            "VP-level sponsorship, departmental AI initiatives underway.",
            ["vp sponsor", "department initiative"]),
        2: RubricCriteria(Dimension.LEADERSHIP, ScoreLevel.LEVEL_2,
            "Limited executive awareness, IT-driven initiatives only.",
            ["it led", "limited awareness"]),
        1: RubricCriteria(Dimension.LEADERSHIP, ScoreLevel.LEVEL_1,
            "No executive sponsorship, AI not discussed at leadership level.",
            ["no sponsor", "not discussed"]),
    },
    "use_case_portfolio": {
        5: RubricCriteria(Dimension.USE_CASE_PORTFOLIO, ScoreLevel.LEVEL_5,
            "10+ production AI use cases, measurable ROI, enterprise-wide deployment.",
            ["production ai", "roi", "enterprise deployment", "scaled"]),
        4: RubricCriteria(Dimension.USE_CASE_PORTFOLIO, ScoreLevel.LEVEL_4,
            "5-10 production use cases, clear business value, scaling in progress.",
            ["use case", "production", "business value", "scaling"]),
        3: RubricCriteria(Dimension.USE_CASE_PORTFOLIO, ScoreLevel.LEVEL_3,
            "2-5 pilot projects, limited production deployments.",
            ["pilot", "proof of concept", "poc"]),
        2: RubricCriteria(Dimension.USE_CASE_PORTFOLIO, ScoreLevel.LEVEL_2,
            "1-2 experiments, no production deployments.",
            ["experiment", "testing", "no production"]),
        1: RubricCriteria(Dimension.USE_CASE_PORTFOLIO, ScoreLevel.LEVEL_1,
            "No AI use cases identified or deployed.",
            ["no use case", "no ai"]),
    },
    "culture": {
        5: RubricCriteria(Dimension.CULTURE, ScoreLevel.LEVEL_5,
            "AI-first culture, continuous learning programs, innovation celebrated, high AI literacy.",
            ["ai first", "innovation culture", "learning culture", "ai literacy"]),
        4: RubricCriteria(Dimension.CULTURE, ScoreLevel.LEVEL_4,
            "Strong data culture, regular AI training, cross-functional collaboration.",
            ["data culture", "training", "collaboration", "upskilling"]),
        3: RubricCriteria(Dimension.CULTURE, ScoreLevel.LEVEL_3,
            "Some AI awareness, ad-hoc training, siloed teams.",
            ["awareness", "ad-hoc training", "siloed"]),
        2: RubricCriteria(Dimension.CULTURE, ScoreLevel.LEVEL_2,
            "Limited AI awareness, resistance to change, no training programs.",
            ["resistance", "limited awareness", "no training"]),
        1: RubricCriteria(Dimension.CULTURE, ScoreLevel.LEVEL_1,
            "No AI culture, no awareness, traditional mindset.",
            ["traditional", "no awareness", "no culture"]),
    },
}


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class CS3Client:
    """
    Async HTTP client for the CS3 Scoring Engine.
    Uses /api/v1/scoring/results/{ticker} — the actual endpoint in this app.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "CS3Client":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, *_) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("CS3Client must be used as async context manager")
        return self._client

    async def get_assessment(self, company_id: str) -> CompanyAssessment:
        """
        Fetch full company assessment.
        Calls: GET /api/v1/scoring/results/{ticker}
        """
        client = self._get_client()
        response = await client.get(f"/api/v1/scoring/results/{company_id}")
        response.raise_for_status()
        return self._map_assessment(response.json())

    async def get_dimension_score(
        self,
        company_id: str,
        dimension: Dimension,
    ) -> DimensionScore:
        """
        Fetch a single dimension score.
        Extracts from /api/v1/scoring/results/{ticker}
        """
        assessment = await self.get_assessment(company_id)
        if dimension in assessment.dimension_scores:
            return assessment.dimension_scores[dimension]

        # Fallback: return a default score if dimension not found
        logger.warning(f"Dimension {dimension.value} not found for {company_id}, using default")
        return DimensionScore(
            dimension=dimension,
            score=50.0,
            level=ScoreLevel.from_score(50.0),
            confidence_interval=(40.0, 60.0),
            evidence_count=0,
            last_updated="",
        )

    async def get_rubric(
        self,
        dimension: Dimension,
        level: Optional[ScoreLevel] = None,
    ) -> List[RubricCriteria]:
        """
        Return rubric criteria from hardcoded table.
        (No /api/v1/rubrics endpoint exists in this app)
        """
        dim_rubrics = HARDCODED_RUBRICS.get(dimension.value, {})

        if level is not None:
            rubric = dim_rubrics.get(level.value)
            return [rubric] if rubric else []

        # Return all levels sorted 1→5
        return [dim_rubrics[lvl] for lvl in sorted(dim_rubrics.keys())]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _map_assessment(self, data: dict) -> CompanyAssessment:
        """Map /api/v1/scoring/results response to CompanyAssessment."""
        dim_scores: Dict[Dimension, DimensionScore] = {}

        for dim_str, score_data in data.get("dimension_scores", {}).items():
            try:
                dim = Dimension(dim_str)
            except ValueError:
                continue

            score = float(score_data.get("score", 0.0))
            level = ScoreLevel.from_score(score)

            # Get confidence interval from top-level confidence object
            ci = data.get("confidence", {})
            ci_lower = float(ci.get("ci_lower", score - 5))
            ci_upper = float(ci.get("ci_upper", score + 5))

            dim_scores[dim] = DimensionScore(
                dimension=dim,
                score=score,
                level=level,
                confidence_interval=(ci_lower, ci_upper),
                evidence_count=int(ci.get("evidence_count", 0)),
                last_updated=data.get("scored_at", ""),
            )

        return CompanyAssessment(
            company_id=data.get("ticker", ""),
            assessment_date=data.get("scored_at", ""),
            vr_score=float(data.get("vr_score", 0.0)),
            hr_score=float(data.get("hr_score", 0.0)),
            synergy_score=float(data.get("synergy_score", 0.0)),
            org_air_score=float(data.get("final_score", 0.0)),
            confidence_interval=(
                float(data.get("confidence", {}).get("ci_lower", 0.0)),
                float(data.get("confidence", {}).get("ci_upper", 0.0)),
            ),
            dimension_scores=dim_scores,
            talent_concentration=float(data.get("talent_concentration", 0.0)),
            position_factor=float(data.get("position_factor", 0.0)),
        )