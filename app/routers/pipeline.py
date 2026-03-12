# app/routers/pipeline.py
"""
On-Demand Company Onboarding Pipeline

POST /api/v1/pipeline/onboard/{ticker}

Automatically onboards ANY company by:
0. Registering company in Snowflake (if not exists)
1. Collecting SEC 10-K filings
2. Collecting job/patent signals
3. Running CS3 scoring
4. Indexing evidence into ChromaDB

This enables ANY US-listed company to work with search + justification,
not just the original 5 (NVDA, JPM, WMT, GE, DG).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from src.services.retrieval.hybrid import HybridRetriever
from src.services.retrieval.dimension_mapper import DimensionMapper
from src.services.integration.cs2_client import CS2Evidence, SourceType, SignalCategory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

# Track onboarding status in memory
_onboarding_status: dict = {}

BASE_URL = "http://localhost:8000"

# Industry ID mapping — matches Snowflake seed data
SECTOR_TO_INDUSTRY_ID = {
    "Technology":         "550e8400-e29b-41d4-a716-446655440003",  # Business Services
    "Financial Services": "550e8400-e29b-41d4-a716-446655440005",
    "Healthcare":         "550e8400-e29b-41d4-a716-446655440002",
    "Industrials":        "550e8400-e29b-41d4-a716-446655440001",
    "Retail":             "550e8400-e29b-41d4-a716-446655440004",
    "Consumer":           "550e8400-e29b-41d4-a716-446655440004",
    "Energy":             "550e8400-e29b-41d4-a716-446655440001",
    "Other":              "550e8400-e29b-41d4-a716-446655440003",
}


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class OnboardingStatus(BaseModel):
    ticker: str
    status: str
    message: str
    steps_completed: list[str]
    steps_remaining: list[str]
    evidence_count: int = 0
    final_score: Optional[float] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_indexed(ticker: str) -> bool:
    """Check if a ticker already has evidence in ChromaDB."""
    try:
        retriever = HybridRetriever()
        results = retriever.search(query="AI technology data", top_k=1, company_id=ticker.upper())
        return len(results) > 0
    except Exception:
        return False


async def _get_or_create_company(client: httpx.AsyncClient, ticker: str, sector: str) -> Optional[str]:
    """
    Get company_id from CS1 — create it if it doesn't exist.
    Returns company_id string or None if failed.
    """
    # Try to find existing company by ticker
    try:
        response = await client.get(
            "/api/v1/companies",
            params={"ticker": ticker, "limit": 10},
        )
        if response.status_code == 200:
            companies = response.json()
            for c in companies:
                if str(c.get("ticker", "")).upper() == ticker.upper():
                    logger.info(f"company_found: {ticker} id={c['id']}")
                    return str(c["id"])
    except Exception as e:
        logger.warning(f"company_lookup_failed: {ticker} — {e}")

    # Company not found — create it
    try:
        industry_id = SECTOR_TO_INDUSTRY_ID.get(sector, SECTOR_TO_INDUSTRY_ID["Technology"])

        response = await client.post(
            "/api/v1/companies",
            json={
                "name": ticker,          # Will be updated if we know the name
                "ticker": ticker.upper(),
                "industry_id": industry_id,
                "position_factor": 0.0,
            },
        )
        response.raise_for_status()
        company = response.json()
        company_id = str(company["id"])
        logger.info(f"company_created: {ticker} id={company_id}")
        return company_id

    except Exception as e:
        logger.error(f"company_create_failed: {ticker} — {e}")
        return None


async def _fetch_evidence(ticker: str) -> list:
    """Fetch evidence for a ticker from the evidence API."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/evidence",
            params={"company_id": ticker.upper()},
        )
        response.raise_for_status()
        return response.json()


def _to_cs2_evidence(raw: dict) -> Optional[CS2Evidence]:
    """Convert raw evidence dict to CS2Evidence object."""
    try:
        return CS2Evidence(
            evidence_id=str(raw["evidence_id"]),
            company_id=str(raw["company_id"]),
            source_type=SourceType(raw["source_type"]),
            signal_category=SignalCategory(raw["signal_category"]),
            content=raw.get("content") or "",
            extracted_at=datetime.now(),
            confidence=float(raw.get("confidence") or 0.5),
            fiscal_year=raw.get("fiscal_year"),
            source_url=raw.get("source_url"),
        )
    except Exception as e:
        logger.warning(f"skipping_evidence: {raw.get('evidence_id')} — {e}")
        return None


# ---------------------------------------------------------------------------
# Background onboarding task
# ---------------------------------------------------------------------------

async def _run_onboarding(ticker: str, sector: str) -> None:
    """Full onboarding pipeline for a new company."""
    ticker = ticker.upper()
    status = _onboarding_status[ticker]
    status["started_at"] = datetime.now().isoformat()

    async with httpx.AsyncClient(timeout=300.0, base_url=BASE_URL) as client:

        # ------------------------------------------------------------------
        # Step 0: Register company in Snowflake
        # ------------------------------------------------------------------
        try:
            status["message"] = "Registering company..."
            company_id = await _get_or_create_company(client, ticker, sector)

            if company_id:
                status["steps_completed"].append(f"Company registered (id: {company_id[:8]}...)")
            else:
                status["steps_completed"].append("Company registration: failed — using ticker only")

            status["steps_remaining"].remove("Register company")

        except Exception as e:
            logger.warning(f"onboarding_step0_failed: {ticker} — {e}")
            status["steps_completed"].append("Company registration: skipped")
            status["steps_remaining"].remove("Register company")

        # ------------------------------------------------------------------
        # Step 1: Collect SEC documents
        # ------------------------------------------------------------------
        try:
            status["message"] = "Collecting SEC 10-K filings..."

            response = await client.post(
                "/api/v1/documents/collect",
                json={
                    "ticker": ticker,
                    "filing_types": ["10-K"],
                    "limit_per_type": 1,
                    "steps": ["download", "parse", "clean", "chunk"],
                },
            )
            response.raise_for_status()
            doc_result = response.json()
            chunks = doc_result.get("chunks_created", 0)

            status["steps_completed"].append(f"SEC filings collected ({chunks} chunks)")
            status["steps_remaining"].remove("Collect SEC filings")

        except Exception as e:
            logger.warning(f"onboarding_step1_failed: {ticker} — {e}")
            status["steps_completed"].append("SEC filings: skipped")
            status["steps_remaining"].remove("Collect SEC filings")

        # ------------------------------------------------------------------
        # Step 2: Collect signals
        # ------------------------------------------------------------------
        try:
            status["message"] = "Collecting job & patent signals..."

            response = await client.post(
                f"/api/v1/signals/collect/{ticker}",
                params={"years": 3},
            )
            response.raise_for_status()

            status["steps_completed"].append("Signals collected")
            status["steps_remaining"].remove("Collect signals")

        except Exception as e:
            logger.warning(f"onboarding_step2_failed: {ticker} — {e}")
            status["steps_completed"].append("Signals: skipped")
            status["steps_remaining"].remove("Collect signals")

        # ------------------------------------------------------------------
        # Step 3: Run CS3 scoring
        # ------------------------------------------------------------------
        try:
            status["message"] = "Running Org-AI-R scoring..."

            response = await client.post(
                f"/api/v1/scoring/score/{ticker}",
                params={"sector": sector},
            )
            response.raise_for_status()
            task_id = response.json().get("task_id")

            # Poll for completion (max 3 minutes)
            final_score = None
            for _ in range(36):
                await asyncio.sleep(5)
                status_resp = await client.get(f"/api/v1/scoring/status/{task_id}")
                if status_resp.status_code == 200:
                    data = status_resp.json()
                    if data.get("status") == "completed":
                        final_score = data.get("final_score")
                        break
                    elif data.get("status") == "failed":
                        break

            status["final_score"] = final_score
            status["steps_completed"].append(
                f"Scoring completed (Org-AI-R: {final_score:.1f})" if final_score else "Scoring completed"
            )
            status["steps_remaining"].remove("Run CS3 scoring")

        except Exception as e:
            logger.warning(f"onboarding_step3_failed: {ticker} — {e}")
            status["steps_completed"].append("Scoring: skipped")
            status["steps_remaining"].remove("Run CS3 scoring")

        # ------------------------------------------------------------------
        # Step 4: Index evidence into ChromaDB
        # ------------------------------------------------------------------
        try:
            status["message"] = "Indexing evidence into ChromaDB..."

            raw_evidence = await _fetch_evidence(ticker)

            if raw_evidence:
                evidence_list = [
                    ev for raw in raw_evidence
                    if (ev := _to_cs2_evidence(raw)) and ev.content.strip()
                ]

                if evidence_list:
                    retriever = HybridRetriever()
                    mapper = DimensionMapper()
                    count = retriever.index_evidence(evidence_list, mapper)
                    status["evidence_count"] = count

                    # Mark as indexed
                    try:
                        ids = [e.evidence_id for e in evidence_list]
                        await client.post(
                            "/api/v1/evidence/mark-indexed",
                            json={"evidence_ids": ids},
                        )
                    except Exception:
                        pass

                    status["steps_completed"].append(f"Indexed {count} evidence items into ChromaDB")
                else:
                    status["steps_completed"].append("ChromaDB indexing: no valid evidence")
            else:
                status["steps_completed"].append("ChromaDB indexing: no evidence found")

            status["steps_remaining"].remove("Index into ChromaDB")

        except Exception as e:
            logger.warning(f"onboarding_step4_failed: {ticker} — {e}")
            status["steps_completed"].append(f"ChromaDB indexing: failed")
            status["steps_remaining"].remove("Index into ChromaDB")

    # Done!
    status["status"] = "completed"
    status["message"] = (
        f"✅ {ticker} is ready! "
        f"Evidence indexed: {status['evidence_count']}. "
        f"Use /api/v1/search?company_id={ticker} or "
        f"/api/v1/justification/{ticker}/{{dimension}}"
    )
    status["completed_at"] = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/onboard/{ticker}", response_model=OnboardingStatus)
async def onboard_company(
    ticker: str,
    background_tasks: BackgroundTasks,
    sector: str = "Technology",
    force: bool = False,
) -> OnboardingStatus:
    """
    Onboard ANY company for AI-readiness search and justification.

    Steps:
    0. Register company in Snowflake (if not exists)
    1. Collect SEC 10-K filings
    2. Collect job & patent signals
    3. Run Org-AI-R scoring (CS3)
    4. Index evidence into ChromaDB (CS4)

    After onboarding completes (~3-5 min), the company works with:
    - GET /api/v1/search?company_id={ticker}
    - GET /api/v1/justification/{ticker}/{dimension}
    - POST /api/v1/justification/{ticker}/ic-prep

    Args:
        ticker: Any US stock ticker e.g. AAPL, MSFT, TSLA, AMZN
        sector:  Company sector e.g. Technology, Retail, Healthcare
        force:   Re-onboard even if already indexed
    """
    ticker = ticker.upper()

    # Check if already being onboarded
    if ticker in _onboarding_status:
        existing = _onboarding_status[ticker]
        if existing["status"] in ("onboarding", "checking"):
            return OnboardingStatus(**existing)

    # Check if already indexed
    if not force and _is_indexed(ticker):
        result = OnboardingStatus(
            ticker=ticker,
            status="already_onboarded",
            message=f"✅ {ticker} is already indexed. Use /api/v1/search or /api/v1/justification/{ticker}/{{dimension}}",
            steps_completed=["Company registered", "SEC filings", "Signals", "Scoring", "ChromaDB indexing"],
            steps_remaining=[],
        )
        _onboarding_status[ticker] = result.model_dump()
        return result

    # Initialize status
    _onboarding_status[ticker] = {
        "ticker": ticker,
        "status": "onboarding",
        "message": f"Starting onboarding for {ticker}...",
        "steps_completed": [],
        "steps_remaining": [
            "Register company",
            "Collect SEC filings",
            "Collect signals",
            "Run CS3 scoring",
            "Index into ChromaDB",
        ],
        "evidence_count": 0,
        "final_score": None,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None,
    }

    background_tasks.add_task(_run_onboarding, ticker, sector)
    return OnboardingStatus(**_onboarding_status[ticker])


@router.get("/onboard/{ticker}/status", response_model=OnboardingStatus)
async def get_onboarding_status(ticker: str) -> OnboardingStatus:
    """Check onboarding status. Poll until status == 'completed'."""
    ticker = ticker.upper()

    if ticker not in _onboarding_status:
        if _is_indexed(ticker):
            return OnboardingStatus(
                ticker=ticker,
                status="already_onboarded",
                message=f"✅ {ticker} is already indexed and ready.",
                steps_completed=["Company registered", "SEC filings", "Signals", "Scoring", "ChromaDB indexing"],
                steps_remaining=[],
            )
        raise HTTPException(
            status_code=404,
            detail=f"No onboarding job for {ticker}. Start with POST /api/v1/pipeline/onboard/{ticker}",
        )

    return OnboardingStatus(**_onboarding_status[ticker])


@router.get("/supported-sectors")
async def get_supported_sectors() -> dict:
    """List supported sectors for onboarding."""
    return {
        "sectors": list(SECTOR_TO_INDUSTRY_ID.keys()),
        "note": "Use the closest matching sector for best scoring accuracy.",
    }