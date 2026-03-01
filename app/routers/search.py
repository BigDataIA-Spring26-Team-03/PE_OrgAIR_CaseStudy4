# app/routers/search.py

from functools import lru_cache
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.search import SearchResultResponse
from src.services.retrieval.hybrid import HybridRetriever

router = APIRouter(prefix="/search", tags=["Search"])


@lru_cache
def get_retriever() -> HybridRetriever:
    """Singleton HybridRetriever — initialises ChromaDB + BM25 once."""
    return HybridRetriever()


@router.get("", response_model=List[SearchResultResponse])
def search_evidence(
    query: str = Query(..., min_length=1, description="Natural language search query"),
    company_id: Optional[str] = Query(None, description="Filter by company ticker e.g. NVDA"),
    dimension: Optional[str] = Query(
        None,
        description=(
            "Filter by CS3 dimension. One of: data_infrastructure, ai_governance, "
            "technology_stack, talent, leadership, use_case_portfolio, culture"
        ),
    ),
    source_types: Optional[List[str]] = Query(
        None, description="Filter by evidence source types e.g. sec_10k_item_1"
    ),
    top_k: int = Query(10, ge=1, le=50, description="Number of results to return"),
    min_confidence: float = Query(
        0.0, ge=0.0, le=1.0, description="Minimum evidence confidence (0.0–1.0)"
    ),
) -> List[SearchResultResponse]:
    """
    Hybrid evidence search combining dense ChromaDB vector search and BM25
    keyword search, merged via Reciprocal Rank Fusion (RRF).

    Results are sorted by combined RRF score (highest first).
    """
    try:
        results = get_retriever().search(
            query=query,
            top_k=top_k,
            company_id=company_id,
            dimension=dimension,
            source_types=source_types,
            min_confidence=min_confidence,
        )
        return [
            SearchResultResponse(
                doc_id=r.doc_id,
                content=r.content,
                metadata=r.metadata,
                score=r.score,
                retrieval_method=r.retrieval_method,
            )
            for r in results
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
