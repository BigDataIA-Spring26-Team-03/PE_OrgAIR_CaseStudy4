# src/services/integration/cs2_client.py
from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SourceType(str, enum.Enum):
    """Evidence source types produced by CS2 collectors."""
    SEC_10K_ITEM_1 = "sec_10k_item_1"          # Business description
    SEC_10K_ITEM_1A = "sec_10k_item_1a"         # Risk factors
    SEC_10K_ITEM_7 = "sec_10k_item_7"           # MD&A
    JOB_POSTING_LINKEDIN = "job_posting_linkedin"
    JOB_POSTING_INDEED = "job_posting_indeed"
    PATENT_USPTO = "patent_uspto"
    PRESS_RELEASE = "press_release"
    GLASSDOOR_REVIEW = "glassdoor_review"        # From CS3 Task 5.0c
    BOARD_PROXY_DEF14A = "board_proxy_def14a"    # From CS3 Task 5.0d
    ANALYST_INTERVIEW = "analyst_interview"      # NEW: DD interviews
    DD_DATA_ROOM = "dd_data_room"               # NEW: Data room docs


class SignalCategory(str, enum.Enum):
    """Signal categories assigned by CS2 collectors."""
    TECHNOLOGY_HIRING = "technology_hiring"
    INNOVATION_ACTIVITY = "innovation_activity"
    DIGITAL_PRESENCE = "digital_presence"
    LEADERSHIP_SIGNALS = "leadership_signals"
    CULTURE_SIGNALS = "culture_signals"
    GOVERNANCE_SIGNALS = "governance_signals"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ExtractedEntity:
    """
    A structured entity extracted from evidence text by CS2 NLP pipeline.

    entity_type examples: "ai_investment", "technology", "person", "dollar_amount"
    char_start / char_end are byte offsets into CS2Evidence.content.
    """
    entity_type: str
    text: str
    char_start: int
    char_end: int
    confidence: float
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CS2Evidence:
    """
    A single evidence item returned by the CS2 Evidence Collection API.

    Mandatory fields mirror the CS2 API response schema.
    Optional fields may be absent for older evidence items or certain source types.
    indexed_in_cs4 / indexed_at are managed by CS4 (this service) after ingestion.
    """
    evidence_id: str
    company_id: str
    source_type: SourceType
    signal_category: SignalCategory
    content: str
    extracted_at: datetime
    confidence: float                                    # 0.0 – 1.0

    # Optional metadata
    fiscal_year: Optional[int] = None
    source_url: Optional[str] = None
    page_number: Optional[int] = None
    extracted_entities: List[ExtractedEntity] = field(default_factory=list)

    # Indexing status — written back by CS4 via mark_indexed()
    indexed_in_cs4: bool = False
    indexed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class CS2Client:
    """
    Async HTTP client for the CS2 Evidence Collection API.

    Usage (mirrors CS1Client pattern):
        async with CS2Client() as client:
            evidence = await client.get_evidence("NVDA")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 60.0,          # CS2 payloads can be large
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "CS2Client":
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

    async def get_evidence(
        self,
        company_id: str,
        source_types: Optional[List[SourceType]] = None,
        signal_categories: Optional[List[SignalCategory]] = None,
        min_confidence: float = 0.0,
        indexed: Optional[bool] = None,
        since: Optional[datetime] = None,
    ) -> List[CS2Evidence]:
        """
        Fetch evidence for a company with optional filters.

        Args:
            company_id:        Company ticker or internal UUID (e.g. "NVDA").
            source_types:      Restrict to specific source types (OR logic).
            signal_categories: Restrict to specific signal categories (OR logic).
            min_confidence:    Only return evidence with confidence >= this value.
            indexed:           True → only already-indexed; False → only unindexed;
                               None → all (default).
            since:             Only evidence extracted after this datetime.

        Returns:
            List of CS2Evidence objects, ordered by extracted_at descending
            (as returned by the API).
        """
        params: Dict[str, Any] = {"company_id": company_id}

        if source_types:
            params["source_types"] = ",".join(s.value for s in source_types)
        if signal_categories:
            params["signal_categories"] = ",".join(s.value for s in signal_categories)
        if min_confidence > 0.0:
            params["min_confidence"] = min_confidence
        if indexed is not None:
            params["indexed"] = indexed
        if since is not None:
            params["since"] = since.isoformat()

        client = self._get_client()
        response = await client.get("/api/v1/evidence", params=params)
        response.raise_for_status()

        return [self._map_evidence(item) for item in response.json()]

    async def mark_indexed(self, evidence_ids: List[str]) -> int:
        """
        Notify CS2 that these evidence items have been indexed in CS4.

        CS2 sets indexed_in_cs4=True and records indexed_at on its side.
        Returns the count of records actually updated.
        """
        if not evidence_ids:
            return 0

        client = self._get_client()
        response = await client.post(
            "/api/v1/evidence/mark-indexed",
            json={"evidence_ids": evidence_ids},
        )
        response.raise_for_status()
        updated: int = response.json().get("updated_count", 0)

        logger.info(
            "cs2_mark_indexed",
            extra={"updated_count": updated, "requested": len(evidence_ids)},
        )
        return updated

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _map_evidence(self, data: dict) -> CS2Evidence:
        """
        Map a raw evidence dict from the CS2 API to a CS2Evidence dataclass.

        Handles:
        - Missing optional fields gracefully (defaults to None / []).
        - Converts source_type / signal_category strings to enums.
        - Parses ISO-8601 extracted_at string to datetime.
        - Builds ExtractedEntity sub-objects from the nested list.
        """
        # Build extracted entities (may be absent for older records)
        raw_entities: List[dict] = data.get("extracted_entities") or []
        extracted_entities = [self._map_entity(e) for e in raw_entities]

        # Parse indexing timestamps when present
        indexed_at_raw = data.get("indexed_at")
        indexed_at: Optional[datetime] = (
            datetime.fromisoformat(indexed_at_raw) if indexed_at_raw else None
        )

        return CS2Evidence(
            evidence_id=str(data["evidence_id"]),
            company_id=str(data["company_id"]),
            source_type=SourceType(data["source_type"]),
            signal_category=SignalCategory(data["signal_category"]),
            content=data.get("content", ""),
            extracted_at=datetime.fromisoformat(data["extracted_at"]),
            confidence=float(data.get("confidence", 0.0)),
            # Optional metadata
            fiscal_year=data.get("fiscal_year"),          # int or None
            source_url=data.get("source_url"),
            page_number=data.get("page_number"),
            extracted_entities=extracted_entities,
            # Indexing status
            indexed_in_cs4=bool(data.get("indexed_in_cs4", False)),
            indexed_at=indexed_at,
        )

    @staticmethod
    def _map_entity(data: dict) -> ExtractedEntity:
        """Map a raw entity dict to an ExtractedEntity dataclass."""
        return ExtractedEntity(
            entity_type=data.get("entity_type", "unknown"),
            text=data.get("text", ""),
            char_start=int(data.get("char_start", 0)),
            char_end=int(data.get("char_end", 0)),
            confidence=float(data.get("confidence", 0.0)),
            attributes=data.get("attributes") or {},
        )

    def _get_client(self) -> httpx.AsyncClient:
        """Return the active async client, raising if not in context manager."""
        if self._client is None:
            raise RuntimeError(
                "CS2Client must be used as an async context manager: "
                "`async with CS2Client() as client:`"
            )
        return self._client