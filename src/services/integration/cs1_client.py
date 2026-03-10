# src/services/integration/cs1_client.py
from __future__ import annotations

import enum
import logging
import warnings
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Sector(str, enum.Enum):
    """
    PE-relevant industry sectors.
    """
    TECHNOLOGY          = "Technology"
    HEALTHCARE          = "Healthcare"
    FINANCIAL_SERVICES  = "Financial Services"   
    INDUSTRIALS         = "Industrials"
    CONSUMER            = "Consumer"
    ENERGY              = "Energy"
    REAL_ESTATE         = "Real Estate"         
    OTHER               = "Other"

    @classmethod
    def from_raw(cls, raw: str) -> Optional["Sector"]:
        """
        Examples:
            "Technology"        → Sector.TECHNOLOGY
            "financial services"→ Sector.FINANCIAL_SERVICES
            "FinancialServices" → Sector.FINANCIAL_SERVICES  (legacy format)
            "Aerospace"         → None  (logged as warning)
        """
        if not raw:
            return None

        # Normalize: lowercase + collapse spaces for comparison
        normalized = raw.strip().lower().replace("  ", " ")

        # Build a lookup from normalized value → enum member
        lookup = {m.value.lower(): m for m in cls}

        # Direct match first (e.g. "Technology" → "technology")
        if normalized in lookup:
            return lookup[normalized]

        # Legacy no-space format fallback (e.g. "FinancialServices")
        lookup_nospace = {m.value.lower().replace(" ", ""): m for m in cls}
        normalized_nospace = normalized.replace(" ", "")
        if normalized_nospace in lookup_nospace:
            return lookup_nospace[normalized_nospace]

        logger.warning("cs1_unknown_sector", extra={"raw_sector": raw})
        return None


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Company:
    """
    CS1 Company metadata.

    Required fields (always present from CS1 API):
        company_id, ticker, name, position_factor

    Optional CS4-specific fields (not yet in CS1 API — will be None):
        sector, sub_sector, market_cap_percentile,
        revenue_millions, employee_count, fiscal_year_end
    """
    company_id: str
    ticker: str
    name: str
    position_factor: float = 0.0
    industry_id: Optional[str] = None

    # CS4-specific — not yet returned by CS1 API
    sector: Optional[Sector] = None
    sub_sector: Optional[str] = None
    market_cap_percentile: Optional[float] = None
    revenue_millions: Optional[float] = None
    employee_count: Optional[int] = None
    fiscal_year_end: Optional[str] = None


@dataclass
class Portfolio:
    """A PE portfolio with associated companies."""
    portfolio_id: str
    name: str
    companies: List[Company] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class CS1Client:
    """
    Async HTTP client for the CS1 Platform API.

    Usage:
        async with CS1Client() as client:
            company = await client.get_company("NVDA")
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

    async def __aenter__(self) -> "CS1Client":
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

    async def get_company(self, ticker: str) -> Company:
        """
        Fetch a single company by ticker symbol.


        """
        ticker_upper = ticker.upper()
        client = self._get_client()

        # Try direct ticker filter first (avoids fetching all companies)
        try:
            response = await client.get(
                "/api/v1/companies",
                params={"ticker": ticker_upper, "limit": 5},
            )
            response.raise_for_status()
            data = response.json()
            for item in data:
                if str(item.get("ticker", "")).upper() == ticker_upper:
                    return self._map_company(item)
        except Exception:
            pass  # fall through to full scan

        # Fallback: fetch all and scan (works even without ticker filter support)
        companies = await self._fetch_all_companies(limit=200, offset=0)
        for company in companies:
            if company.ticker and company.ticker.upper() == ticker_upper:
                return company

        raise ValueError(
            f"Company with ticker '{ticker_upper}' not found in CS1. "
            "Ensure the company exists in the CS1 database."
        )

    async def list_companies(
        self,
        sector: Optional[Sector] = None,
        min_revenue: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Company]:
        """
        List companies with optional client-side filtering.

        """
        companies = await self._fetch_all_companies(limit=limit, offset=offset)

        if sector is not None:
            companies = [c for c in companies if c.sector == sector]

        if min_revenue is not None:
            companies = [
                c for c in companies
                if c.revenue_millions is not None
                and c.revenue_millions >= min_revenue
            ]

        return companies

    async def get_portfolio_companies(self, portfolio_id: str) -> List[Company]:
        """
        Fetch all companies in a PE portfolio.

        """
        raise NotImplementedError(
            f"get_portfolio_companies('{portfolio_id}'): "
            "The /api/v1/portfolios endpoint is not yet implemented in CS1. "
            "Use list_companies() or get_company() per ticker instead."
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_all_companies(
        self, limit: int, offset: int
    ) -> List[Company]:
        """Paginated GET /api/v1/companies call."""
        client = self._get_client()
        response = await client.get(
            "/api/v1/companies",
            params={"limit": limit, "offset": offset},
        )
        response.raise_for_status()
        return [self._map_company(item) for item in response.json()]

    def _map_company(self, data: dict) -> Company:
        """
        Map a raw CS1 API response dict to a Company dataclass.

        CHANGE 5: sector now uses Sector.from_raw() so "Financial Services"
        and "FinancialServices" both parse correctly instead of crashing.

        CS1 actual response shape (verified from your app):
        {
            "id": "uuid-string",
            "ticker": "NVDA",
            "name": "NVIDIA Corporation",
            "industry_id": "uuid-string",
            "position_factor": 0.428332
        }
        """
        raw_sector = data.get("sector") or data.get("industry") or ""

        return Company(
            company_id=str(data.get("id", "")),
            ticker=str(data.get("ticker") or "").upper(),
            name=data.get("name", ""),
            industry_id=str(data.get("industry_id", "")) or None,
            position_factor=float(data.get("position_factor", 0.0)),
            # CHANGE 5: safe sector parsing instead of direct Sector(raw_sector)
            sector=Sector.from_raw(raw_sector) if raw_sector else None,
            # Fields CS1 doesn't return yet — intentionally None
            sub_sector=None,
            market_cap_percentile=None,
            revenue_millions=None,
            employee_count=None,
            fiscal_year_end=None,
        )

    def _get_client(self) -> httpx.AsyncClient:
        """Return the active async client, raising if not in context manager."""
        if self._client is None:
            raise RuntimeError(
                "CS1Client must be used as an async context manager: "
                "`async with CS1Client() as client:`"
            )
        return self._client