# app/routers/justification.py

from functools import lru_cache
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException

from app.models.justification import (
    CitedEvidenceResponse,
    ICMeetingPackageResponse,
    ICPrepRequest,
    ScoreJustificationResponse,
)
from src.services.justification.generator import JustificationGenerator, ScoreJustification
from src.services.workflows.ic_prep import ICPrepWorkflow, ICMeetingPackage
from src.services.integration.cs3_client import Dimension

router = APIRouter(prefix="/justification", tags=["Justification"])


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

@lru_cache
def get_generator() -> JustificationGenerator:
    """Singleton JustificationGenerator — initialises CS3 client + HybridRetriever once."""
    return JustificationGenerator()


@lru_cache
def get_ic_workflow() -> ICPrepWorkflow:
    """Singleton ICPrepWorkflow — initialises CS1, CS3 clients + JustificationGenerator once."""
    return ICPrepWorkflow()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_dimension(dimension: str) -> Dimension:
    """Validate a dimension string and return the Dimension enum. Raises 400 if invalid."""
    try:
        return Dimension(dimension)
    except ValueError:
        valid = [d.value for d in Dimension]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid dimension '{dimension}'. Valid values: {valid}",
        )


def _justification_to_response(j: ScoreJustification) -> ScoreJustificationResponse:
    """Convert a ScoreJustification dataclass to its Pydantic response model."""
    return ScoreJustificationResponse(
        company_id=j.company_id,
        dimension=j.dimension.value if isinstance(j.dimension, Dimension) else str(j.dimension),
        score=j.score,
        level=j.level,
        level_name=j.level_name,
        confidence_interval=list(j.confidence_interval),
        rubric_criteria=j.rubric_criteria,
        rubric_keywords=j.rubric_keywords,
        supporting_evidence=[
            CitedEvidenceResponse(
                evidence_id=e.evidence_id,
                content=e.content,
                source_type=e.source_type,
                source_url=e.source_url,
                confidence=e.confidence,
                matched_keywords=e.matched_keywords,
                relevance_score=e.relevance_score,
            )
            for e in j.supporting_evidence
        ],
        gaps_identified=j.gaps_identified,
        generated_summary=j.generated_summary,
        evidence_strength=j.evidence_strength,
    )


def _ic_package_to_response(pkg: ICMeetingPackage) -> ICMeetingPackageResponse:
    """Flatten ICMeetingPackage dataclass to its Pydantic response model."""
    dim_justifications: Dict[str, ScoreJustificationResponse] = {
        dim.value: _justification_to_response(j)
        for dim, j in pkg.dimension_justifications.items()
    }
    return ICMeetingPackageResponse(
        company_id=pkg.company.company_id,
        company_ticker=pkg.company.ticker,
        company_name=pkg.company.name,
        org_air_score=pkg.assessment.org_air_score,
        vr_score=pkg.assessment.vr_score,
        hr_score=pkg.assessment.hr_score,
        executive_summary=pkg.executive_summary,
        key_strengths=pkg.key_strengths,
        key_gaps=pkg.key_gaps,
        risk_factors=pkg.risk_factors,
        recommendation=pkg.recommendation,
        generated_at=pkg.generated_at.isoformat(),
        total_evidence_count=pkg.total_evidence_count,
        avg_evidence_strength=pkg.avg_evidence_strength,
        dimension_justifications=dim_justifications,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{company_id}/{dimension}", response_model=ScoreJustificationResponse)
async def get_justification(company_id: str, dimension: str) -> ScoreJustificationResponse:
    """
    Generate a score justification for a single CS3 dimension.

    """
    dim = _parse_dimension(dimension)
    try:
        justification = await get_generator().generate_justification(
            company_id=company_id,
            dimension=dim,
        )
        return _justification_to_response(justification)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{company_id}/ic-prep", response_model=ICMeetingPackageResponse)
async def prepare_ic_meeting(
    company_id: str,
    payload: ICPrepRequest = Body(default=ICPrepRequest()),
) -> ICMeetingPackageResponse:
    """
    Generate a complete IC meeting evidence package.

    """
    focus_dimensions: Optional[List[Dimension]] = None
    if payload.focus_dimensions:
        focus_dimensions = [_parse_dimension(d) for d in payload.focus_dimensions]

    try:
        pkg = await get_ic_workflow().prepare_meeting(
            company_id=company_id,
            focus_dimensions=focus_dimensions,
        )
        return _ic_package_to_response(pkg)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
