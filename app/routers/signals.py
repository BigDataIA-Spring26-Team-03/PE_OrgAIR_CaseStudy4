# app/routers/signals.py
"""
Unified External Signals API Endpoints

ALL endpoints use TICKER (not company_id) for easy access.
Comprehensive AI/ML signal collection with no arbitrary limits.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
import json
import structlog

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.models.signal import ExternalSignal, SignalCategory, SignalSource
from app.services.snowflake import SnowflakeService

# Import all collectors
from app.pipelines.job_signals import scrape_job_postings, job_postings_to_signals
from app.pipelines.tech_signals import scrape_tech_signal_inputs, tech_inputs_to_signals
from app.pipelines.patent_signals import collect_patent_signals_real, COMPANY_USPTO_NAMES
from app.pipelines.external_signals_orchestrator import build_company_signal_summary

logger = structlog.get_logger()
router = APIRouter(prefix="/signals", tags=["signals"])


# ============================================================================
# 🎯 UNIFIED COLLECTION ENDPOINT - COMPREHENSIVE AI/ML SEARCH
# ============================================================================

@router.post("/collect/{ticker}")
async def collect_all_signals(
    ticker: str,
    background_tasks: BackgroundTasks,
    years: int = Query(default=5, ge=1, le=10, description="Years for patent search"),
    job_location: str = Query(default="United States", description="Job search location"),
):
    """
    🎯 Collect ALL 4 signal types for a company - COMPREHENSIVE SEARCH

    What it does:
    1. Jobs: Searches 10+ AI/ML job types
    2. Tech Stack: Scrapes company website for AI technologies
    3. Patents: Calls USPTO API for AI patents
    4. Leadership: Uses latest board governance signal persisted in Snowflake

    Then:
    - Inserts all signals into external_signals table
    - Re-aggregates category scores from Snowflake
    - Updates company_signal_summaries
    """
    db = SnowflakeService()
    try:
        company_query = """
            SELECT id, name, ticker
            FROM companies
            WHERE ticker = %(ticker)s AND is_deleted = FALSE
        """
        companies = db.execute_query(company_query, {"ticker": ticker.upper()})

        if not companies:
            raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found in database")

        company = companies[0]

        background_tasks.add_task(
            run_comprehensive_collection_task,
            company_id=company["id"],
            company_name=company["name"],
            ticker=ticker.upper(),
            years=years,
            job_location=job_location,
        )

        return {
            "status": "accepted",
            "message": f"Comprehensive signal collection started for {ticker}",
            "company": company,
            "collection_scope": {
                "jobs": "10+ AI/ML role types, unlimited results",
                "tech_stack": "Full website technology scan",
                "patents": f"All AI patents ({years} years)",
                "leadership": "From board governance signal (Snowflake)",
            },
            "note": "Collection running in background. Check /api/v1/signals/summary for results.",
        }
    finally:
        db.close()


@router.post("/collect/patents/{ticker}")
async def collect_patents_only(
    ticker: str,
    background_tasks: BackgroundTasks,
    years: int = Query(default=5, ge=1, le=10),
):
    db = SnowflakeService()
    try:
        company_query = """
            SELECT id, name, ticker
            FROM companies
            WHERE ticker = %(ticker)s AND is_deleted = FALSE
        """
        companies = db.execute_query(company_query, {"ticker": ticker.upper()})

        if not companies:
            raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

        company = companies[0]

        background_tasks.add_task(
            run_patent_only_task,
            company_id=company["id"],
            company_name=company["name"],
            ticker=ticker.upper(),
            years=years,
        )

        return {"status": "accepted", "message": f"Patent collection started for {ticker}", "company": company}
    finally:
        db.close()


@router.post("/collect/jobs/{ticker}")
async def collect_jobs_only(
    ticker: str,
    background_tasks: BackgroundTasks,
    job_location: str = Query(default="United States"),
):
    db = SnowflakeService()
    try:
        company_query = """
            SELECT id, name, ticker
            FROM companies
            WHERE ticker = %(ticker)s AND is_deleted = FALSE
        """
        companies = db.execute_query(company_query, {"ticker": ticker.upper()})

        if not companies:
            raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

        company = companies[0]

        background_tasks.add_task(
            run_jobs_only_task,
            company_id=company["id"],
            company_name=company["name"],
            ticker=ticker.upper(),
            job_location=job_location,
        )

        return {"status": "accepted", "message": f"Comprehensive job search started for {ticker}", "company": company}
    finally:
        db.close()


@router.post("/collect/all")
async def collect_all_companies(
    background_tasks: BackgroundTasks,
    years: int = Query(default=5, ge=1, le=10),
):
    background_tasks.add_task(run_batch_collection_task, years=years)
    return {
        "status": "accepted",
        "message": "Batch collection started",
        "companies": list(COMPANY_USPTO_NAMES.keys()),
        "note": "Check /api/v1/signals/summary for progress",
    }


# ============================================================================
# RETRIEVAL ENDPOINTS - ALL USE TICKER
# ============================================================================

@router.get("/company/{ticker}")
async def get_signals_by_ticker(ticker: str):
    db = SnowflakeService()
    try:
        company_query = """
            SELECT id
            FROM companies
            WHERE ticker = %(ticker)s AND is_deleted = FALSE
        """
        companies = db.execute_query(company_query, {"ticker": ticker.upper()})

        if not companies:
            raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

        company_id = companies[0]["id"]

        signals_query = """
            SELECT
                id, company_id, category, source, signal_date,
                raw_value, normalized_score, confidence,
                metadata, created_at
            FROM external_signals
            WHERE company_id = %(company_id)s
            ORDER BY signal_date DESC, created_at DESC
        """
        signals = db.execute_query(signals_query, {"company_id": company_id})

        if not signals:
            raise HTTPException(status_code=404, detail=f"No signals found for {ticker}")

        return {"ticker": ticker.upper(), "company_id": company_id, "signal_count": len(signals), "signals": signals}
    finally:
        db.close()


@router.get("/company/{ticker}/category/{category}")
async def get_signals_by_ticker_and_category(ticker: str, category: str):
    valid_categories = ["jobs", "tech", "patents", "leadership"]
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Valid: {valid_categories}")

    db = SnowflakeService()
    try:
        company_query = """
            SELECT id
            FROM companies
            WHERE ticker = %(ticker)s AND is_deleted = FALSE
        """
        companies = db.execute_query(company_query, {"ticker": ticker.upper()})
        if not companies:
            raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

        company_id = companies[0]["id"]

        category_map = {
            "jobs": "technology_hiring",
            "tech": "digital_presence",
            "patents": "innovation_activity",
            "leadership": "leadership_signals",
        }
        db_category = category_map.get(category, category)

        signals_query = """
            SELECT
                id, company_id, category, source, signal_date,
                raw_value, normalized_score, confidence,
                metadata, created_at
            FROM external_signals
            WHERE company_id = %(company_id)s
              AND category = %(category)s
            ORDER BY signal_date DESC, created_at DESC
        """
        signals = db.execute_query(signals_query, {"company_id": company_id, "category": db_category})

        return {"ticker": ticker.upper(), "category": category, "signal_count": len(signals), "signals": signals}
    finally:
        db.close()


@router.get("/summary")
async def get_all_summaries():
    db = SnowflakeService()
    try:
        query = """
            SELECT
                css.company_id,
                css.ticker,
                c.name as company_name,
                css.technology_hiring_score as jobs_score,
                css.innovation_activity_score as patents_score,
                css.digital_presence_score as tech_score,
                css.leadership_signals_score as leadership_score,
                css.composite_score,
                css.signal_count,
                css.last_updated
            FROM company_signal_summaries css
            JOIN companies c ON css.company_id = c.id
            WHERE c.is_deleted = FALSE
            ORDER BY css.composite_score DESC
        """
        summaries = db.execute_query(query)
        return {"count": len(summaries), "summaries": summaries}
    finally:
        db.close()


@router.get("/summary/{ticker}")
async def get_summary_by_ticker(ticker: str):
    db = SnowflakeService()
    try:
        query = """
            SELECT
                css.company_id,
                css.ticker,
                c.name as company_name,
                css.technology_hiring_score as jobs_score,
                css.innovation_activity_score as patents_score,
                css.digital_presence_score as tech_score,
                css.leadership_signals_score as leadership_score,
                css.composite_score,
                css.signal_count,
                css.last_updated
            FROM company_signal_summaries css
            JOIN companies c ON css.company_id = c.id
            WHERE css.ticker = %(ticker)s
              AND c.is_deleted = FALSE
        """
        summaries = db.execute_query(query, {"ticker": ticker.upper()})
        if not summaries:
            raise HTTPException(status_code=404, detail=f"No summary found for {ticker}")
        return summaries[0]
    finally:
        db.close()


# ============================================================================
# HELPERS
# ============================================================================

def _fetch_category_scores_from_db(db: SnowflakeService, company_id: str) -> dict[str, int]:
    """
    Aggregate category scores from Snowflake external_signals for this company.
    Uses AVG(normalized_score) per category.
    """
    rows = db.execute_query(
        """
        SELECT category, AVG(normalized_score) AS avg_score
        FROM external_signals
        WHERE company_id = %(company_id)s
        GROUP BY category
        """,
        {"company_id": company_id},
    )

    by_cat: dict[str, int] = {}
    for r in rows:
        cat = r.get("category")
        avg_score = r.get("avg_score")
        if cat and avg_score is not None:
            by_cat[str(cat)] = int(round(float(avg_score)))

    return {
        "jobs": by_cat.get("technology_hiring", 0),
        "tech": by_cat.get("digital_presence", 0),
        "patents": by_cat.get("innovation_activity", 0),
        "leadership": by_cat.get("leadership_signals", 0),
    }


def _count_total_signals(db: SnowflakeService, company_id: str) -> int:
    """
    Total number of signals for a company in external_signals.
    We use this for company_signal_summaries.signal_count so the upsert doesn't
    depend on "inserted_count this run".
    """
    rows = db.execute_query(
        """
        SELECT COUNT(*) AS n
        FROM external_signals
        WHERE company_id = %(company_id)s
        """,
        {"company_id": company_id},
    )
    if not rows:
        return 0
    return int(rows[0].get("n") or 0)


def _leadership_signal_from_latest_board(
    db: SnowflakeService, company_id: str, ticker: str
) -> Optional[ExternalSignal]:
    """
    Create ONE aggregated leadership_signals ExternalSignal from the latest
    board_governance_signals row for this company.
    """
    rows = db.execute_query(
        """
        SELECT
            id,
            ticker,
            governance_score,
            has_tech_committee,
            has_ai_expertise,
            has_data_officer,
            has_independent_majority,
            has_risk_tech_oversight,
            has_ai_strategy,
            ai_experts,
            evidence,
            confidence,
            created_at
        FROM board_governance_signals
        WHERE company_id = %(company_id)s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"company_id": company_id},
    )

    if not rows:
        return None

    r = rows[0]

    flags = {
        "has_tech_committee": bool(r.get("has_tech_committee")),
        "has_ai_expertise": bool(r.get("has_ai_expertise")),
        "has_data_officer": bool(r.get("has_data_officer")),
        "has_independent_majority": bool(r.get("has_independent_majority")),
        "has_risk_tech_oversight": bool(r.get("has_risk_tech_oversight")),
        "has_ai_strategy": bool(r.get("has_ai_strategy")),
    }

    meta = {
        "source_table": "board_governance_signals",
        "board_governance_signal_id": str(r.get("id")),
        "ticker": str(r.get("ticker") or ticker),
        "flags": flags,
        "ai_experts": r.get("ai_experts"),
        "evidence": r.get("evidence"),
        "confidence": float(r.get("confidence") or 0.0),
        "created_at": str(r.get("created_at")),
    }

    meta_json = json.dumps(meta, default=str)

    return ExternalSignal(
        id=f"{company_id}-leadership-board-{r.get('id')}",
        company_id=company_id,
        category=SignalCategory.LEADERSHIP_SIGNALS,
        source=SignalSource.external,
        signal_date=datetime.utcnow(),
        score=int(round(float(r.get("governance_score") or 0.0))),
        title="Board governance & AI oversight (SEC DEF 14A)",
        url=None,
        metadata_json=meta_json,
    )


# ============================================================================
# BACKGROUND TASKS - THE WORKERS
# ============================================================================

@router.post("/collect/internal/run/{ticker}")
async def run_collection_inline_for_debug(ticker: str):
    """
    Optional helper to run collection inline without BackgroundTasks.
    """
    db = SnowflakeService()
    try:
        companies = db.execute_query(
            """
            SELECT id, name, ticker
            FROM companies
            WHERE ticker = %(ticker)s AND is_deleted = FALSE
            """,
            {"ticker": ticker.upper()},
        )
        if not companies:
            raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

        company = companies[0]
        await run_comprehensive_collection_task(
            company_id=company["id"],
            company_name=company["name"],
            ticker=ticker.upper(),
            years=5,
            job_location="United States",
        )
        return {"ok": True, "ticker": ticker.upper()}
    finally:
        db.close()


async def run_comprehensive_collection_task(
    company_id: str,
    company_name: str,
    ticker: str,
    years: int,
    job_location: str,
):
    """
    COMPREHENSIVE collection - ALL AI/ML jobs, no limits!
    """
    db = SnowflakeService()
    try:
        all_signals: list[ExternalSignal] = []

        logger.info("🚀 Starting comprehensive collection", ticker=ticker, company_id=company_id, company_name=company_name)

        # ========================================
        # 1. JOBS - COMPREHENSIVE SEARCH
        # ========================================
        try:
            all_jobs = []
            comprehensive_searches = [
                "machine learning engineer",
                "data scientist",
                "AI engineer",
                "artificial intelligence engineer",
                "deep learning engineer",
                "MLOps engineer",
                "research scientist machine learning",
                "NLP engineer",
                "natural language processing",
                "computer vision engineer",
                "data engineer machine learning",
                "AI researcher",
                "ML platform engineer",
                "AI product manager",
            ]

            logger.info("Starting comprehensive job search", queries=len(comprehensive_searches), ticker=ticker)

            for search_query in comprehensive_searches:
                try:
                    jobs = scrape_job_postings(
                        search_query=search_query,
                        sources=["indeed", "google"],
                        location=job_location,
                        max_results_per_source=100,
                        target_company_name=company_name,
                    )
                    all_jobs.extend(jobs)
                    if jobs:
                        logger.info("✓ Query found jobs", query=search_query[:30], count=len(jobs))
                except Exception as e:
                    logger.warning("Search query failed", query=search_query, error=str(e))

            # Deduplicate by URL
            seen_urls = set()
            unique_jobs = []
            for job in all_jobs:
                job_url = job.url or ""
                if job_url:
                    if job_url not in seen_urls:
                        seen_urls.add(job_url)
                        unique_jobs.append(job)
                else:
                    unique_jobs.append(job)

            job_signals = job_postings_to_signals(company_id, unique_jobs)
            all_signals.extend(job_signals)

            logger.info("✅ Jobs collection complete", total_found=len(all_jobs), unique=len(unique_jobs), signals=len(job_signals))
        except Exception as e:
            logger.exception("Job collection failed", error=str(e))

        # ========================================
        # 2. TECH STACK
        # ========================================
        try:
            domain = db.get_primary_domain_by_company_id(company_id)
            if domain:
                tech_inputs = scrape_tech_signal_inputs(company=company_name, company_domain_or_url=domain)
                tech_signals = tech_inputs_to_signals(company_id, tech_inputs)
                all_signals.extend(tech_signals)
                logger.info("✅ Tech stack collected", count=len(tech_signals))
            else:
                logger.warning("⚠️ No domain found, skipping tech signals")
        except Exception as e:
            logger.exception("Tech collection failed", error=str(e))

        # ========================================
        # 3. PATENTS
        # ========================================
        try:
            uspto_name = COMPANY_USPTO_NAMES.get(ticker)
            if uspto_name:
                patent_signals = await collect_patent_signals_real(
                    company_id=company_id,
                    company_name=company_name,
                    uspto_name=uspto_name,
                    years=years,
                )
                all_signals.extend(patent_signals)
                logger.info("✅ Patents collected", count=len(patent_signals), score=(patent_signals[0].score if patent_signals else 0))
            else:
                logger.warning("⚠️ No USPTO name mapping", ticker=ticker)
        except Exception as e:
            logger.exception("Patent collection failed", error=str(e))

        # ========================================
        # 4. LEADERSHIP (board + Wikidata + Wikipedia + senior jobs)
        # ========================================
        try:
            # Primary: board governance from SEC DEF 14A
            board_signal = _leadership_signal_from_latest_board(db, company_id=company_id, ticker=ticker)
            board_score = board_signal.score if board_signal else 0

            # Secondary: senior AI job postings score
            senior_job_score = 0
            senior_count = 0
            try:
                senior_count = sum(
                    1 for s in job_signals
                    if any(t.lower() in (s.title or "").lower() for t in ["director", "vp", "chief", "head of"])
                )
                senior_job_score = min(senior_count * 10, 40)
                logger.info("Senior job postings for leadership", count=senior_count, score=senior_job_score)
            except Exception:
                pass

            if board_signal:
                # Enrich board score with Wikidata when score is low
                wiki_boost = 0
                if board_score < 50:
                    try:
                        from app.pipelines.leadership_signals import (
                            collect_leadership_profiles_from_web,
                            calculate_leadership_score_0_1,
                        )
                        web_profiles = collect_leadership_profiles_from_web(company_name, company_id)
                        if web_profiles:
                            wiki_score = int(round(calculate_leadership_score_0_1(web_profiles) * 100))
                            wiki_boost = wiki_score
                            logger.info("✅ Wikidata enrichment", wiki_score=wiki_score)
                    except Exception as wiki_err:
                        logger.debug(f"Wikidata enrichment skipped: {wiki_err}")

                # Only blend if it improves the score
                if wiki_boost > 0 and senior_job_score > 0:
                    blended = int(round(0.5 * board_score + 0.3 * wiki_boost + 0.2 * senior_job_score))
                    combined_score = max(board_score, blended)
                elif wiki_boost > 0:
                    blended = int(round(0.6 * board_score + 0.4 * wiki_boost))
                    combined_score = max(board_score, blended)
                elif senior_job_score > 0:
                    blended = int(round(0.7 * board_score + 0.3 * senior_job_score))
                    combined_score = max(board_score, blended)
                else:
                    combined_score = board_score

                board_signal = ExternalSignal(
                    id=board_signal.id,
                    company_id=board_signal.company_id,
                    category=board_signal.category,
                    source=board_signal.source,
                    signal_date=board_signal.signal_date,
                    score=combined_score,
                    title=board_signal.title,
                    url=board_signal.url,
                    metadata_json=board_signal.metadata_json,
                )
                all_signals.append(board_signal)
                logger.info("✅ Leadership aggregated (board+wiki+jobs)", board=board_score, wiki=wiki_boost, jobs=senior_job_score, combined=combined_score)

            else:
                # No board data — use Wikidata + Wikipedia as primary source
                try:
                    from app.pipelines.leadership_signals import (
                        collect_leadership_profiles_from_web,
                        leadership_profiles_to_aggregated_signal,
                    )
                    web_profiles = collect_leadership_profiles_from_web(company_name, company_id)
                    if web_profiles:
                        web_signal = leadership_profiles_to_aggregated_signal(company_id, web_profiles)
                        if senior_job_score > 0:
                            blended = int(round(0.7 * web_signal.score + 0.3 * senior_job_score))
                            web_signal = ExternalSignal(
                                id=web_signal.id, company_id=web_signal.company_id,
                                category=web_signal.category, source=web_signal.source,
                                signal_date=web_signal.signal_date, score=blended,
                                title=web_signal.title, url=web_signal.url,
                                metadata_json=web_signal.metadata_json,
                            )
                        all_signals.append(web_signal)
                        logger.info("✅ Leadership from Wikidata+Wikipedia", score=web_signal.score, profiles=len(web_profiles))
                    elif senior_job_score > 0:
                        import json as _json
                        leadership_signal = ExternalSignal(
                            id=f"{company_id}-leadership-jobs",
                            company_id=company_id,
                            category=SignalCategory.LEADERSHIP_SIGNALS,
                            source=SignalSource.external,
                            signal_date=datetime.utcnow(),
                            score=senior_job_score,
                            title=f"Leadership signals from {senior_count} senior job postings",
                            url=None,
                            metadata_json=_json.dumps({"source": "job_postings", "senior_count": senior_count}),
                        )
                        all_signals.append(leadership_signal)
                        logger.info("✅ Leadership from senior jobs only", score=senior_job_score)
                    else:
                        logger.warning("⚠️ No leadership signals found", ticker=ticker)
                except Exception as web_err:
                    logger.warning(f"⚠️ Web leadership collection failed: {web_err}")

        except Exception as e:
            logger.exception("❌ Leadership pipeline failed", error=str(e))

        # ========================================
        # STORE IN SNOWFLAKE + RE-AGGREGATE SCORES FROM DB
        # ========================================
        inserted_count = 0
        if all_signals:
            inserted_count = db.insert_external_signals(all_signals)

        scores = _fetch_category_scores_from_db(db, company_id=company_id)
        total_signal_count = _count_total_signals(db, company_id=company_id)

        summary = build_company_signal_summary(
            company_id=company_id,
            jobs_score=scores["jobs"],
            tech_score=scores["tech"],
            patents_score=scores["patents"],
            leadership_score=scores["leadership"],
        )

        # IMPORTANT: write total count (not just inserted_count)
        db.upsert_company_signal_summary(summary, signal_count=total_signal_count)

        logger.info(
            "🎉 Collection complete!",
            ticker=ticker,
            inserted_signals=inserted_count,
            total_signals=total_signal_count,
            jobs_score=scores["jobs"],
            tech_score=scores["tech"],
            patents_score=scores["patents"],
            leadership_score=scores["leadership"],
            composite_score=summary.composite_score,
        )

    except Exception as e:
        logger.error("❌ Collection failed", ticker=ticker, error=str(e))
    finally:
        db.close()


async def run_patent_only_task(company_id: str, company_name: str, ticker: str, years: int):
    try:
        db = SnowflakeService()

        from app.pipelines.patent_signals import get_uspto_name
        uspto_name = get_uspto_name(ticker, company_name)
        if not uspto_name:
            logger.error("No USPTO mapping", ticker=ticker)
            return

        patent_signals = await collect_patent_signals_real(
            company_id=company_id,
            company_name=company_name,
            uspto_name=uspto_name,
            years=years,
        )

        inserted_count = 0
        if patent_signals:
            inserted_count = db.insert_external_signals(patent_signals)

        scores = _fetch_category_scores_from_db(db, company_id=company_id)
        total_signal_count = _count_total_signals(db, company_id=company_id)

        summary = build_company_signal_summary(
            company_id=company_id,
            jobs_score=scores["jobs"],
            tech_score=scores["tech"],
            patents_score=scores["patents"],
            leadership_score=scores["leadership"],
        )
        db.upsert_company_signal_summary(summary, signal_count=total_signal_count)

        logger.info("✅ Patents collected", ticker=ticker, inserted=inserted_count, total=total_signal_count, composite=summary.composite_score)

    except Exception as e:
        logger.error("Patent task failed", ticker=ticker, error=str(e))
    finally:
        try:
            db.close()
        except Exception:
            pass


async def run_jobs_only_task(company_id: str, company_name: str, ticker: str, job_location: str):
    try:
        db = SnowflakeService()
        all_jobs = []

        searches = [
            "machine learning engineer",
            "data scientist",
            "AI engineer",
            "MLOps engineer",
            "deep learning",
            "NLP engineer",
        ]

        for query in searches:
            try:
                jobs = scrape_job_postings(
                    search_query=query,
                    sources=["indeed", "google"],
                    location=job_location,
                    max_results_per_source=100,
                    target_company_name=company_name,
                )
                all_jobs.extend(jobs)
            except Exception as e:
                logger.warning(f"Query '{query}' failed", error=str(e))

        seen = set()
        unique = []
        for job in all_jobs:
            if job.url and job.url not in seen:
                seen.add(job.url)
                unique.append(job)
            elif not job.url:
                unique.append(job)

        inserted_count = 0
        if unique:
            job_signals = job_postings_to_signals(company_id, unique)
            inserted_count = db.insert_external_signals(job_signals)

        scores = _fetch_category_scores_from_db(db, company_id=company_id)
        total_signal_count = _count_total_signals(db, company_id=company_id)

        summary = build_company_signal_summary(
            company_id=company_id,
            jobs_score=scores["jobs"],
            tech_score=scores["tech"],
            patents_score=scores["patents"],
            leadership_score=scores["leadership"],
        )
        db.upsert_company_signal_summary(summary, signal_count=total_signal_count)

        logger.info("✅ Jobs collected", ticker=ticker, inserted=inserted_count, total=total_signal_count, jobs_score=scores["jobs"], composite=summary.composite_score)

    except Exception as e:
        logger.error("Jobs task failed", ticker=ticker, error=str(e))
    finally:
        try:
            db.close()
        except Exception:
            pass


async def run_batch_collection_task(years: int):
    try:
        for ticker in COMPANY_USPTO_NAMES.keys():
            db = SnowflakeService()
            try:
                companies = db.execute_query(
                    """
                    SELECT id, name
                    FROM companies
                    WHERE ticker = %(ticker)s AND is_deleted = FALSE
                    """,
                    {"ticker": ticker},
                )

                if companies:
                    await run_comprehensive_collection_task(
                        company_id=companies[0]["id"],
                        company_name=companies[0]["name"],
                        ticker=ticker,
                        years=years,
                        job_location="United States",
                    )

                    import asyncio
                    await asyncio.sleep(30)

            finally:
                db.close()

    except Exception as e:
        logger.error("Batch collection failed", error=str(e))