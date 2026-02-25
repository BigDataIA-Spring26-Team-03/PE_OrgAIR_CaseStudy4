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
    AI_GOVERNANCE = "ai_governance"
    TECHNOLOGY_STACK = "technology_stack"
    TALENT = "talent"
    LEADERSHIP = "leadership"
    USE_CASE_PORTFOLIO = "use_case_portfolio"
    CULTURE = "culture"


class ScoreLevel(int, enum.Enum):
    """
    Five-band score levels used by CS3 rubrics.

    Band mapping:
        LEVEL_5  80 – 100  Excellent
        LEVEL_4  60 –  79  Good
        LEVEL_3  40 –  59  Adequate
        LEVEL_2  20 –  39  Developing
        LEVEL_1   0 –  19  Nascent
    """
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    LEVEL_5 = 5

    @property
    def name_label(self) -> str:
        """Human-readable label for IC reports."""
        _labels: Dict[int, str] = {
            5: "Excellent",
            4: "Good",
            3: "Adequate",
            2: "Developing",
            1: "Nascent",
        }
        return _labels[self.value]

    @property
    def score_range(self) -> Tuple[int, int]:
        """Inclusive (low, high) integer range for this level."""
        _ranges: Dict[int, Tuple[int, int]] = {
            5: (80, 100),
            4: (60, 79),
            3: (40, 59),
            2: (20, 39),
            1: (0, 19),
        }
        return _ranges[self.value]

    @classmethod
    def from_score(cls, score: float) -> "ScoreLevel":
        """Derive the level from a raw 0-100 score value."""
        for level in reversed(cls):          # highest first
            low, _ = level.score_range
            if score >= low:
                return level
        return cls.LEVEL_1


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DimensionScore:
    """
    A single dimension score as returned by the CS3 scoring engine.

    confidence_interval is a (lower, upper) tuple representing the 95% CI
    around the point estimate stored in score.
    """
    dimension: Dimension
    score: float                              # 0.0 – 100.0
    level: ScoreLevel
    confidence_interval: Tuple[float, float]  # (lower_95, upper_95)
    evidence_count: int
    last_updated: str                         # ISO-8601 date string


@dataclass
class RubricCriteria:
    """
    Rubric criteria for one (dimension, level) pair from the CS3 rubric table.

    keywords are used by the JustificationGenerator to match evidence text.
    quantitative_thresholds hold numeric benchmarks, e.g.
        {"ai_job_ratio": 0.25, "data_quality_pct": 70}
    """
    dimension: Dimension
    level: ScoreLevel
    criteria_text: str
    keywords: List[str]
    quantitative_thresholds: Dict[str, float] = field(default_factory=dict)


@dataclass
class CompanyAssessment:
    """
    Full company assessment returned by GET /api/v1/assessments/{company_id}.

    Composite scores:
        org_air_score  — top-level Org-AI-R composite
        vr_score       — V^R (Value Readiness) sub-score
        hr_score       — H^R (Human Readiness) sub-score
        synergy_score  — synergy component

    Risk adjustments:
        talent_concentration  — Herfindahl-style concentration index (0-1)
        position_factor       — signed relative-to-sector adjustment
    """
    company_id: str
    assessment_date: str                              # ISO-8601 date string

    # Composite scores
    vr_score: float
    hr_score: float
    synergy_score: float
    org_air_score: float

    # 95% CI on the org_air_score
    confidence_interval: Tuple[float, float]

    # Per-dimension breakdown — keyed by Dimension enum
    dimension_scores: Dict[Dimension, DimensionScore]

    # Risk adjustment factors
    talent_concentration: float
    position_factor: float


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class CS3Client:
    """
    Async HTTP client for the CS3 Scoring Engine API.

    Usage (mirrors CS1Client / CS2Client pattern):
        async with CS3Client() as client:
            assessment = await client.get_assessment("NVDA")
            score = await client.get_dimension_score("NVDA", Dimension.TALENT)
            rubrics = await client.get_rubric(Dimension.TALENT, ScoreLevel.LEVEL_4)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_assessment(self, company_id: str) -> CompanyAssessment:
        """
        Fetch the full company assessment including all 7 dimension scores.

        Calls: GET /api/v1/assessments/{company_id}
        """
        client = self._get_client()
        response = await client.get(f"/api/v1/assessments/{company_id}")
        response.raise_for_status()
        return self._map_assessment(response.json())

    async def get_dimension_score(
        self,
        company_id: str,
        dimension: Dimension,
    ) -> DimensionScore:
        """
        Fetch a single dimension score for a company.

        Calls: GET /api/v1/assessments/{company_id}/dimensions/{dimension}

        Prefer this over get_assessment() when only one dimension is needed —
        it avoids fetching and mapping all 7 scores.
        """
        client = self._get_client()
        response = await client.get(
            f"/api/v1/assessments/{company_id}/dimensions/{dimension.value}"
        )
        response.raise_for_status()
        return self._map_dimension_score(dimension, response.json())

    async def get_rubric(
        self,
        dimension: Dimension,
        level: Optional[ScoreLevel] = None,
    ) -> List[RubricCriteria]:
        """
        Fetch rubric criteria for a dimension.

        Args:
            dimension: Which of the 7 V^R dimensions to fetch criteria for.
            level:     Specific score level (1-5). If None, all 5 levels are
                       returned, ordered level 1 → 5.

        Calls: GET /api/v1/rubrics/{dimension}[?level={level}]
        """
        params: Dict[str, int] = {}
        if level is not None:
            params["level"] = level.value

        client = self._get_client()
        response = await client.get(
            f"/api/v1/rubrics/{dimension.value}",
            params=params,
        )
        response.raise_for_status()

        return [self._map_rubric(dimension, item) for item in response.json()]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _map_assessment(self, data: dict) -> CompanyAssessment:
        """
        Map a raw assessment dict to a CompanyAssessment dataclass.

        Handles:
        - Nested dimension_scores dict (str key → score dict).
        - Converts CI list/tuple from API into a Python tuple.
        - Gracefully defaults missing composite scores to 0.0.
        """
        # Build the per-dimension score map
        dim_scores: Dict[Dimension, DimensionScore] = {}
        for dim_str, score_data in data.get("dimension_scores", {}).items():
            try:
                dim = Dimension(dim_str)
            except ValueError:
                logger.warning(
                    "cs3_unknown_dimension",
                    extra={"dimension": dim_str},
                )
                continue
            dim_scores[dim] = self._map_dimension_score(dim, score_data)

        return CompanyAssessment(
            company_id=str(data["company_id"]),
            assessment_date=data.get("assessment_date", ""),
            vr_score=float(data.get("vr_score", 0.0)),
            hr_score=float(data.get("hr_score", 0.0)),
            synergy_score=float(data.get("synergy_score", 0.0)),
            org_air_score=float(data.get("org_air_score", 0.0)),
            confidence_interval=self._parse_ci(data.get("confidence_interval")),
            dimension_scores=dim_scores,
            talent_concentration=float(data.get("talent_concentration", 0.0)),
            position_factor=float(data.get("position_factor", 0.0)),
        )

    @staticmethod
    def _map_dimension_score(dimension: Dimension, data: dict) -> DimensionScore:
        """
        Map a raw score dict to a DimensionScore dataclass.

        The API may return level as an int (1-5) — coerce to ScoreLevel enum.
        Falls back to deriving level from score if level key is missing.
        """
        score = float(data.get("score", 0.0))

        raw_level = data.get("level")
        if raw_level is not None:
            level = ScoreLevel(int(raw_level))
        else:
            level = ScoreLevel.from_score(score)

        return DimensionScore(
            dimension=dimension,
            score=score,
            level=level,
            confidence_interval=CS3Client._parse_ci(data.get("confidence_interval")),
            evidence_count=int(data.get("evidence_count", 0)),
            last_updated=data.get("last_updated", ""),
        )

    @staticmethod
    def _map_rubric(dimension: Dimension, data: dict) -> RubricCriteria:
        """Map a raw rubric dict to a RubricCriteria dataclass."""
        return RubricCriteria(
            dimension=dimension,
            level=ScoreLevel(int(data["level"])),
            criteria_text=data.get("criteria_text", ""),
            keywords=data.get("keywords") or [],
            quantitative_thresholds=data.get("quantitative_thresholds") or {},
        )

    @staticmethod
    def _parse_ci(raw: object) -> Tuple[float, float]:
        """
        Safely parse a confidence interval from the API response.

        The API returns a 2-element list, e.g. [62.1, 74.3].
        Returns (0.0, 0.0) if the field is absent or malformed.
        """
        try:
            lower, upper = raw  # type: ignore[misc]
            return (float(lower), float(upper))
        except (TypeError, ValueError):
            return (0.0, 0.0)

    def _get_client(self) -> httpx.AsyncClient:
        """Return the active async client, raising if not in context manager."""
        if self._client is None:
            raise RuntimeError(
                "CS3Client must be used as an async context manager: "
                "`async with CS3Client() as client:`"
            )
        return self._client