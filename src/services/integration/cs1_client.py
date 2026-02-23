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
    """PE-relevant industry sectors."""
    TECHNOLOGY = "Technology"
    HEALTHCARE = "Healthcare"
    FINANCIAL_SERVICES = "FinancialServices"
    INDUSTRIALS = "Industrials"
    CONSUMER = "Consumer"
    ENERGY = "Energy"
    REAL_ESTATE = "RealEstate"
    OTHER = "Other"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Company:
    """
    CS1 Company metadata.
    """
    company_id: str          # maps from CompanyResponse.id (UUID → str)
    ticker: str
    name: str

    # CS4-specific fields — not yet in the API response
    sector: Optional[Sector] = None
    sub_sector: Optional[str] = None
    market_cap_percentile: Optional[float] = None
    revenue_millions: Optional[float] = None
    employee_count: Optional[int] = None
    fiscal_year_end: Optional[str] = None

    # Preserve raw API fields for downstream use
    industry_id: Optional[str] = None
    position_factor: float = 0.0


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
        Fetch a company by ticker symbol.
        """
        ticker_upper = ticker.upper()
        # Fetch up to 200 companies; in practice portfolios are small.
        companies = await self._fetch_all_companies(limit=200, offset=0)
        for company in companies:
            if company.ticker and company.ticker.upper() == ticker_upper:
                return company
        raise ValueError(
            f"Company with ticker '{ticker_upper}' not found. "
            "Ensure the company exists in the CS1 database."
        )

    async def list_companies(
        self,
        sector: Optional[Sector] = None,
        min_revenue: Optional[float] = None,
        limit: int = 10,
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
                if c.revenue_millions is not None and c.revenue_millions >= min_revenue
            ]

        return companies

    async def get_portfolio_companies(self, portfolio_id: str) -> List[Company]:
        """
        Fetch companies in a portfolio.

      
        """
        warnings.warn(
            "get_portfolio_companies: the /api/v1/portfolios endpoint is not "
            "yet implemented. Returning empty list.",
            UserWarning,
            stacklevel=2,
        )
        logger.warning(
            "cs1_portfolio_endpoint_not_implemented",
            extra={"portfolio_id": portfolio_id},
        )
        return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_all_companies(
        self, limit: int, offset: int
    ) -> List[Company]:
        """Make the paginated GET /api/v1/companies call."""
        client = self._get_client()
        response = await client.get(
            "/api/v1/companies",
            params={"limit": limit, "offset": offset},
        )
        response.raise_for_status()
        return [self._map_company(item) for item in response.json()]

    def _map_company(self, data: dict) -> Company:
        """
        Map a raw CompanyResponse dict to a CS4 Company dataclass.

        """
        return Company(
            company_id=str(data.get("id", "")),
            ticker=str(data.get("ticker") or "").upper(),
            name=data.get("name", ""),
            industry_id=str(data.get("industry_id", "")) or None,
            position_factor=float(data.get("position_factor", 0.0)),
            # CS4-specific fields not yet in API
            sector=None,
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
