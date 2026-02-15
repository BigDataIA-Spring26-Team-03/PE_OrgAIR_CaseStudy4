# app/routers/culture.py

from typing import List
from fastapi import APIRouter, HTTPException, Query
import json
from datetime import datetime
import uuid as uuid_lib

from app.models.culture import (
    CultureSignalResponse,
    CultureSignalSummary,
    CultureSignalListResponse
)
from app.services.snowflake import db

router = APIRouter(prefix="/culture-signals", tags=["Culture Signals"])


# ============================================================================
# LIST ALL SIGNALS
# ============================================================================

@router.get("", response_model=CultureSignalListResponse)
async def list_all_signals(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """List ALL culture signals across all companies."""
    
    offset = (page - 1) * limit
    
    count_result = db.execute_query("SELECT COUNT(*) as total FROM culture_signals")
    total = count_result[0].get('TOTAL') or count_result[0].get('total') if count_result else 0
    
    query = f"""
        SELECT * FROM culture_signals
        ORDER BY created_at DESC
        LIMIT {limit} OFFSET {offset}
    """
    
    results = db.execute_query(query)
    
    items = [
        CultureSignalSummary(
            id=row.get('ID') or row.get('id'),
            company_id=row.get('COMPANY_ID') or row.get('company_id'),
            ticker=row.get('TICKER') or row.get('ticker'),
            overall_score=row.get('OVERALL_SCORE') or row.get('overall_score'),
            avg_rating=row.get('AVG_RATING') or row.get('avg_rating'),
            review_count=row.get('REVIEW_COUNT') or row.get('review_count'),
            confidence=row.get('CONFIDENCE') or row.get('confidence'),
            created_at=row.get('CREATED_AT') or row.get('created_at')
        )
        for row in results
    ]
    
    pages = (total + limit - 1) // limit if total > 0 else 0
    
    return CultureSignalListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages
    )


# ============================================================================
# LIST SIGNALS BY TICKER
# ============================================================================

@router.get("/ticker/{ticker}", response_model=List[CultureSignalResponse])
async def list_signals_by_ticker(ticker: str):
    """List all culture signals for a specific company (by ticker)."""
    
    query = f"""
        SELECT * FROM culture_signals
        WHERE ticker = '{ticker.upper()}'
        ORDER BY created_at DESC
    """
    
    results = db.execute_query(query)
    
    if not results:
        return []
    
    signals = []
    for row in results:
        positive_keywords = json.loads(row.get('POSITIVE_KEYWORDS_FOUND') or row.get('positive_keywords_found') or '[]')
        negative_keywords = json.loads(row.get('NEGATIVE_KEYWORDS_FOUND') or row.get('negative_keywords_found') or '[]')
        
        signals.append(CultureSignalResponse(
            id=row.get('ID') or row.get('id'),
            company_id=row.get('COMPANY_ID') or row.get('company_id'),
            ticker=row.get('TICKER') or row.get('ticker'),
            innovation_score=row.get('INNOVATION_SCORE') or row.get('innovation_score'),
            data_driven_score=row.get('DATA_DRIVEN_SCORE') or row.get('data_driven_score'),
            change_readiness_score=row.get('CHANGE_READINESS_SCORE') or row.get('change_readiness_score'),
            ai_awareness_score=row.get('AI_AWARENESS_SCORE') or row.get('ai_awareness_score'),
            overall_score=row.get('OVERALL_SCORE') or row.get('overall_score'),
            review_count=row.get('REVIEW_COUNT') or row.get('review_count'),
            avg_rating=row.get('AVG_RATING') or row.get('avg_rating'),
            current_employee_ratio=row.get('CURRENT_EMPLOYEE_RATIO') or row.get('current_employee_ratio'),
            confidence=row.get('CONFIDENCE') or row.get('confidence'),
            positive_keywords_found=positive_keywords,
            negative_keywords_found=negative_keywords,
            created_at=row.get('CREATED_AT') or row.get('created_at'),
            updated_at=row.get('UPDATED_AT') or row.get('updated_at')
        ))
    
    return signals


# ============================================================================
# LIST ALL REVIEWS
# ============================================================================

@router.get("/reviews")
async def list_all_reviews(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200)
):
    """List ALL reviews across all companies."""
    
    offset = (page - 1) * limit
    
    query = f"""
        SELECT 
            gr.*,
            cs.ticker,
            cs.overall_score as culture_score
        FROM glassdoor_reviews gr
        LEFT JOIN culture_signals cs ON gr.culture_signal_id = cs.id
        ORDER BY gr.review_date DESC
        LIMIT {limit} OFFSET {offset}
    """
    
    results = db.execute_query(query)
    
    reviews = [
        {
            "id": row.get('ID') or row.get('id'),
            "company_id": row.get('COMPANY_ID') or row.get('company_id'),
            "ticker": row.get('TICKER') or row.get('ticker'),
            "review_id": row.get('REVIEW_ID') or row.get('review_id'),
            "rating": float(row.get('RATING') or row.get('rating')),
            "title": row.get('TITLE') or row.get('title'),
            "pros": row.get('PROS') or row.get('pros'),
            "cons": row.get('CONS') or row.get('cons'),
            "advice_to_management": row.get('ADVICE_TO_MANAGEMENT') or row.get('advice_to_management'),
            "is_current_employee": row.get('IS_CURRENT_EMPLOYEE') or row.get('is_current_employee'),
            "job_title": row.get('JOB_TITLE') or row.get('job_title'),
            "review_date": str(row.get('REVIEW_DATE') or row.get('review_date')),
            "culture_score": float(row.get('CULTURE_SCORE') or row.get('culture_score')) if (row.get('CULTURE_SCORE') or row.get('culture_score')) else None
        }
        for row in results
    ]
    
    return reviews


# ============================================================================
# LIST REVIEWS BY TICKER
# ============================================================================

@router.get("/reviews/ticker/{ticker}")
async def list_reviews_by_ticker(ticker: str):
    """List all reviews for a specific company (by ticker)."""
    
    query = f"""
        SELECT 
            gr.*,
            cs.ticker,
            cs.overall_score as culture_score
        FROM glassdoor_reviews gr
        LEFT JOIN culture_signals cs ON gr.culture_signal_id = cs.id
        WHERE cs.ticker = '{ticker.upper()}'
        ORDER BY gr.review_date DESC
    """
    
    results = db.execute_query(query)
    
    reviews = [
        {
            "id": row.get('ID') or row.get('id'),
            "company_id": row.get('COMPANY_ID') or row.get('company_id'),
            "ticker": row.get('TICKER') or row.get('ticker'),
            "review_id": row.get('REVIEW_ID') or row.get('review_id'),
            "rating": float(row.get('RATING') or row.get('rating')),
            "title": row.get('TITLE') or row.get('title'),
            "pros": row.get('PROS') or row.get('pros'),
            "cons": row.get('CONS') or row.get('cons'),
            "advice_to_management": row.get('ADVICE_TO_MANAGEMENT') or row.get('advice_to_management'),
            "is_current_employee": row.get('IS_CURRENT_EMPLOYEE') or row.get('is_current_employee'),
            "job_title": row.get('JOB_TITLE') or row.get('job_title'),
            "review_date": str(row.get('REVIEW_DATE') or row.get('review_date')),
            "culture_score": float(row.get('CULTURE_SCORE') or row.get('culture_score')) if (row.get('CULTURE_SCORE') or row.get('culture_score')) else None
        }
        for row in results
    ]
    
    return {
        "ticker": ticker.upper(),
        "review_count": len(reviews),
        "avg_rating": round(sum(r['rating'] for r in reviews) / len(reviews), 2) if reviews else 0,
        "reviews": reviews
    }


# ============================================================================
# LIST SCORES
# ============================================================================

@router.get("/scores")
async def list_all_scores(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """List ALL scores (simple view)."""
    
    offset = (page - 1) * limit
    
    query = f"""
        SELECT 
            ticker,
            overall_score,
            avg_rating,
            review_count,
            confidence,
            created_at
        FROM culture_signals
        ORDER BY overall_score DESC
        LIMIT {limit} OFFSET {offset}
    """
    
    results = db.execute_query(query)
    
    scores = [
        {
            "ticker": row.get('TICKER') or row.get('ticker'),
            "overall_score": float(row.get('OVERALL_SCORE') or row.get('overall_score')),
            "avg_rating": float(row.get('AVG_RATING') or row.get('avg_rating')),
            "review_count": row.get('REVIEW_COUNT') or row.get('review_count'),
            "confidence": float(row.get('CONFIDENCE') or row.get('confidence')),
            "created_at": row.get('CREATED_AT') or row.get('created_at')
        }
        for row in results
    ]
    
    return {
        "scores": scores,
        "count": len(scores)
    }


@router.get("/scores/ticker/{ticker}")
async def list_scores_by_ticker(ticker: str):
    """List scores for a specific company (by ticker)."""
    
    query = f"""
        SELECT 
            ticker,
            overall_score,
            innovation_score,
            data_driven_score,
            change_readiness_score,
            ai_awareness_score,
            avg_rating,
            review_count,
            confidence,
            created_at
        FROM culture_signals
        WHERE ticker = '{ticker.upper()}'
        ORDER BY created_at DESC
    """
    
    results = db.execute_query(query)
    
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No culture scores found for {ticker}"
        )
    
    scores = [
        {
            "ticker": row.get('TICKER') or row.get('ticker'),
            "overall_score": float(row.get('OVERALL_SCORE') or row.get('overall_score')),
            "innovation_score": float(row.get('INNOVATION_SCORE') or row.get('innovation_score')),
            "data_driven_score": float(row.get('DATA_DRIVEN_SCORE') or row.get('data_driven_score')),
            "change_readiness_score": float(row.get('CHANGE_READINESS_SCORE') or row.get('change_readiness_score')),
            "ai_awareness_score": float(row.get('AI_AWARENESS_SCORE') or row.get('ai_awareness_score')),
            "avg_rating": float(row.get('AVG_RATING') or row.get('avg_rating')),
            "review_count": row.get('REVIEW_COUNT') or row.get('review_count'),
            "confidence": float(row.get('CONFIDENCE') or row.get('confidence')),
            "created_at": row.get('CREATED_AT') or row.get('created_at')
        }
        for row in results
    ]
    
    return {
        "ticker": ticker.upper(),
        "scores": scores,
        "count": len(scores)
    }


# ============================================================================
# COLLECTION ENDPOINTS
# ============================================================================

@router.post("/collect/{ticker}", status_code=201)
async def collect_by_ticker(
    ticker: str,
    use_cache: bool = Query(True, description="Use cached data if available")
):
    """
    Collect culture data for a specific company (by ticker).
    
    Triggers Glassdoor collector, analyzes reviews, saves to Snowflake.
    """
    
    # Get company_id from ticker
    company_query = f"SELECT id FROM companies WHERE ticker = '{ticker.upper()}'"
    company_result = db.execute_query(company_query)
    
    if not company_result:
        raise HTTPException(
            status_code=404,
            detail=f"Company {ticker} not found. Add company first."
        )
    
    company_id = company_result[0].get('ID') or company_result[0].get('id')
    
    # Run collector
    try:
        from app.pipelines.glassdoor_collector import collect_glassdoor_data
        
        culture_data = await collect_glassdoor_data(ticker.upper(), use_cache=use_cache)
        
        # Save to database
        signal_id = str(uuid_lib.uuid4())
        
        insert_sql = f"""
            INSERT INTO culture_signals (
                id, company_id, ticker,
                innovation_score, data_driven_score, change_readiness_score, ai_awareness_score,
                overall_score, review_count, avg_rating, current_employee_ratio, confidence,
                positive_keywords_found, negative_keywords_found, created_at
            ) VALUES (
                '{signal_id}', 
                '{company_id}', 
                '{ticker.upper()}',
                {float(culture_data.get('innovation_score', 50))}, 
                {float(culture_data.get('data_driven_score', 50))}, 
                {float(culture_data.get('change_readiness_score', 50))}, 
                {float(culture_data.get('ai_awareness_score', 50))},
                {float(culture_data['culture_score'])}, 
                {culture_data['review_count']}, 
                {float(culture_data['avg_rating'])}, 
                {float(culture_data.get('current_employee_ratio', 0.5))}, 
                {float(culture_data['confidence'])},
                '{json.dumps(culture_data.get('positive_keywords_found', []))}', 
                '{json.dumps(culture_data.get('negative_keywords_found', []))}', 
                CURRENT_TIMESTAMP()
            )
        """
        
        db.execute_update(insert_sql)
        
        return {
            "message": f"Culture signal collected for {ticker}",
            "ticker": ticker.upper(),
            "signal_id": signal_id,
            "culture_score": culture_data['culture_score'],
            "innovation_score": culture_data.get('innovation_score'),
            "data_driven_score": culture_data.get('data_driven_score'),
            "change_readiness_score": culture_data.get('change_readiness_score'),
            "ai_awareness_score": culture_data.get('ai_awareness_score'),
            "review_count": culture_data['review_count'],
            "avg_rating": culture_data['avg_rating'],
            "confidence": culture_data['confidence'],
            "rationale": culture_data.get('rationale')
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Collection failed: {str(e)}")


@router.post("/collect-all")
async def collect_all_companies(
    use_cache: bool = Query(True, description="Use cached data")
):
    """Collect culture signals for ALL companies."""
    
    companies_query = "SELECT id, ticker FROM companies ORDER BY ticker"
    companies = db.execute_query(companies_query)
    
    if not companies:
        raise HTTPException(status_code=404, detail="No companies found")
    
    collected = []
    failed = []
    
    for company in companies:
        ticker = company.get('TICKER') or company.get('ticker')
        
        try:
            result = await collect_by_ticker(ticker, use_cache=use_cache)
            collected.append(result)
        except Exception as e:
            failed.append({
                "ticker": ticker,
                "error": str(e)
            })
    
    return {
        "status": "completed",
        "total_companies": len(companies),
        "collected": len(collected),
        "failed": len(failed),
        "collected_tickers": [c['ticker'] for c in collected],
        "failed_tickers": [f['ticker'] for f in failed]
    }