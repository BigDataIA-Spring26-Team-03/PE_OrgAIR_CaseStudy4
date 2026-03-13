from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
from typing import List, Optional

from app.models.signal import CompanySignalSummary, ExternalSignal, SignalCategory, SignalSource


class AIBackgroundType(str, Enum):
    CHIEF_AI_OFFICER = "CHIEF_AI_OFFICER"
    AI_COMPANY_VETERAN = "AI_COMPANY_VETERAN"
    PHD_AI_ML = "PHD_AI_ML"
    ML_PUBLICATIONS = "ML_PUBLICATIONS"
    AI_PATENTS = "AI_PATENTS"
    AI_BOARD_MEMBER = "AI_BOARD_MEMBER"
    AI_CERTIFICATION = "AI_CERTIFICATION"
    AI_KEYWORDS_ONLY = "AI_KEYWORDS_ONLY"


AI_INDICATOR_SCORES: dict[AIBackgroundType, float] = {
    AIBackgroundType.CHIEF_AI_OFFICER: 1.0,
    AIBackgroundType.AI_COMPANY_VETERAN: 0.9,
    AIBackgroundType.PHD_AI_ML: 0.8,
    AIBackgroundType.ML_PUBLICATIONS: 0.7,
    AIBackgroundType.AI_PATENTS: 0.6,
    AIBackgroundType.AI_BOARD_MEMBER: 0.5,
    AIBackgroundType.AI_CERTIFICATION: 0.3,
    AIBackgroundType.AI_KEYWORDS_ONLY: 0.1,
}


ROLE_WEIGHTS: dict[str, float] = {
    "ceo": 1.0,
    "cto": 0.9,
    "cdo": 0.85,
    "cai": 1.0,
    "vp": 0.7,
}


@dataclass(frozen=True)
class LeadershipProfile:
    name: str
    title: str
    company: str
    ai_indicators: List[AIBackgroundType]
    url: Optional[str] = None
    observed_date: Optional[str] = None


def _normalize(s: str) -> str:
    return (s or "").strip().lower()


def _role_weight(title: str) -> float:
    t = _normalize(title)

    if "chief ai officer" in t or "cai" in t:
        return ROLE_WEIGHTS["cai"]
    if t.startswith("ceo") or "chief executive" in t:
        return ROLE_WEIGHTS["ceo"]
    if t.startswith("cto") or "chief technology" in t:
        return ROLE_WEIGHTS["cto"]
    if t.startswith("cdo") or "chief data" in t:
        return ROLE_WEIGHTS["cdo"]
    if t.startswith("vp") or "vice president" in t:
        return ROLE_WEIGHTS["vp"]

    # default for other leadership titles (COO, CFO, SVP, etc.)
    return 0.5


def _max_indicator_score(indicators: List[AIBackgroundType]) -> float:
    if not indicators:
        return 0.0
    return max(AI_INDICATOR_SCORES.get(i, 0.0) for i in indicators)


def calculate_leadership_score_0_1(executives: List[LeadershipProfile]) -> float:
    """
    Weighted average of AI indicators across leadership team:
        sum(role_weight * max_ai_indicator) / sum(role_weight)
    This avoids penalizing companies just for listing more executives.
    """
    if not executives:
        return 0.0

    weighted_sum = 0.0
    weight_sum = 0.0

    for e in executives:
        w = _role_weight(e.title)
        weight_sum += w
        weighted_sum += w * _max_indicator_score(e.ai_indicators)

    return min(weighted_sum / (weight_sum or 1.0), 1.0)


def _signal_id(company_id: str, name: str, title: str, url: Optional[str]) -> str:
    raw = f"{company_id}|leadership|exec|{name}|{title}|{url or ''}"
    return sha256(raw.encode("utf-8")).hexdigest()


def leadership_profiles_to_signals(company_id: str, executives: List[LeadershipProfile]) -> List[ExternalSignal]:
    """
    Per-executive signals (drill-down rows).
    Score is the executive's max AI indicator (0-100).
    Role weight + weighted contribution live in metadata for auditability.
    """
    now = datetime.utcnow()
    signals: List[ExternalSignal] = []

    for e in executives:
        ai_score = _max_indicator_score(e.ai_indicators)
        role_w = _role_weight(e.title)

        # Individual score (not weighted) for interpretability
        score_0_100 = int(round(ai_score * 100))

        meta = {
            "company": e.company,
            "executive_name": e.name,
            "executive_title": e.title,
            "ai_indicators": [i.value for i in e.ai_indicators],
            "max_indicator_score": ai_score,
            "role_weight": role_w,
            "weighted_contribution": role_w * ai_score,
            "observed_date": e.observed_date,
            "calculation": "individual_score = max_ai_indicator; aggregation uses role_weight",
        }

        signals.append(
            ExternalSignal(
                id=_signal_id(company_id, e.name, e.title, e.url),
                company_id=company_id,
                category=SignalCategory.LEADERSHIP_SIGNALS,
                source=SignalSource.external,
                signal_date=now,
                score=score_0_100,
                title=f"{e.name} — {e.title}",
                url=e.url,
                metadata_json=json.dumps(meta, default=str),
            )
        )

    return signals


def aggregate_leadership_signals(company_id: str, leadership_signals: List[ExternalSignal]) -> CompanySignalSummary:
    """
    Produce CompanySignalSummary.leadership_score from per-exec ExternalSignals.
    This is the roll-up that other pipeline components can consume.
    """
    if not leadership_signals:
        leadership_score = 0
    else:
        executives: List[LeadershipProfile] = []
        for s in leadership_signals:
            try:
                meta = json.loads(s.metadata_json or "{}")
                indicators = [AIBackgroundType(x) for x in meta.get("ai_indicators", [])]
                executives.append(
                    LeadershipProfile(
                        name=meta.get("executive_name", s.title or "Unknown"),
                        title=meta.get("executive_title", ""),
                        company=meta.get("company", ""),
                        ai_indicators=indicators,
                        url=s.url,
                        observed_date=meta.get("observed_date"),
                    )
                )
            except Exception:
                continue

        score_0_1 = calculate_leadership_score_0_1(executives)
        leadership_score = int(round(score_0_1 * 100))

    return CompanySignalSummary(
        company_id=company_id,
        jobs_score=0,
        tech_score=0,
        patents_score=0,
        leadership_score=leadership_score,
        composite_score=0,
        last_updated_at=datetime.utcnow(),
    )


def leadership_profiles_to_aggregated_signal(
    company_id: str,
    executives: List[LeadershipProfile],
) -> ExternalSignal:
    """
    One aggregated leadership ExternalSignal (summary row).
    ID is deterministic based on executives content so repeated runs don't insert duplicates.
    """
    now = datetime.utcnow()

    if not executives:
        meta = {
            "executive_count": 0,
            "company": "",
            "executives": [],
            "aggregated_score": 0,
            "calculation_method": "weighted_avg(role_weight × max_ai_indicator) / sum(role_weight)",
            "calculation": "No executives analyzed",
        }
        payload = json.dumps(meta, sort_keys=True, default=str)
        signal_id = sha256(f"{company_id}|leadership|aggregated|{payload}".encode()).hexdigest()

        return ExternalSignal(
            id=signal_id,
            company_id=company_id,
            category=SignalCategory.LEADERSHIP_SIGNALS,
            source=SignalSource.external,
            signal_date=now,
            score=0,
            title="Leadership Team AI Expertise (0 executives)",
            url=None,
            metadata_json=json.dumps(meta, default=str),
        )

    score_0_1 = calculate_leadership_score_0_1(executives)
    score_0_100 = int(round(score_0_1 * 100))

    exec_details = []
    for e in executives:
        ai_score = _max_indicator_score(e.ai_indicators)
        role_w = _role_weight(e.title)
        exec_details.append(
            {
                "name": e.name,
                "title": e.title,
                "ai_indicators": [i.value for i in e.ai_indicators],
                "max_indicator_score": round(ai_score, 3),
                "role_weight": round(role_w, 3),
                "weighted_contribution": round(role_w * ai_score, 3),
                "individual_score": int(round(ai_score * 100)),
                "observed_date": e.observed_date,
                "url": e.url,
            }
        )

    # Stable ordering
    exec_details_sorted = sorted(exec_details, key=lambda x: (x["name"].lower(), x["title"].lower()))

    meta = {
        "executive_count": len(executives),
        "company": executives[0].company if executives else "",
        "aggregated_score": score_0_100,
        "calculation_method": "weighted_avg(role_weight × max_ai_indicator) / sum(role_weight)",
        "executives": exec_details_sorted,
    }

    # Deterministic ID based on aggregated content
    payload = json.dumps(meta, sort_keys=True, default=str)
    signal_id = sha256(f"{company_id}|leadership|aggregated|{payload}".encode()).hexdigest()

    return ExternalSignal(
        id=signal_id,
        company_id=company_id,
        category=SignalCategory.LEADERSHIP_SIGNALS,
        source=SignalSource.external,
        signal_date=now,
        score=score_0_100,
        title=f"Leadership Team AI Expertise ({len(executives)} executives)",
        url=None,
        metadata_json=json.dumps(meta, default=str),
    )

# ===========================================================================
# WIKIDATA + WIKIPEDIA ENRICHMENT
# Dynamic leadership collection for any public company
# ===========================================================================

import requests as _requests
import logging as _logging

_logger = _logging.getLogger(__name__)

_WIKI_HEADERS = {"User-Agent": "PE-OrgAIR research@example.com"}

_WIKI_AI_INDICATOR_MAP = {
    "chief ai officer": AIBackgroundType.CHIEF_AI_OFFICER,
    "chief artificial intelligence": AIBackgroundType.CHIEF_AI_OFFICER,
    "openai": AIBackgroundType.AI_COMPANY_VETERAN,
    "deepmind": AIBackgroundType.AI_COMPANY_VETERAN,
    "google brain": AIBackgroundType.AI_COMPANY_VETERAN,
    "anthropic": AIBackgroundType.AI_COMPANY_VETERAN,
    "phd": AIBackgroundType.PHD_AI_ML,
    "computer science": AIBackgroundType.PHD_AI_ML,
    "research scientist": AIBackgroundType.PHD_AI_ML,
    "machine learning": AIBackgroundType.AI_KEYWORDS_ONLY,
    "artificial intelligence": AIBackgroundType.AI_KEYWORDS_ONLY,
    "deep learning": AIBackgroundType.AI_KEYWORDS_ONLY,
    "neural network": AIBackgroundType.AI_KEYWORDS_ONLY,
    "data science": AIBackgroundType.AI_KEYWORDS_ONLY,
    "cloud computing": AIBackgroundType.AI_KEYWORDS_ONLY,
    "software engineer": AIBackgroundType.AI_KEYWORDS_ONLY,
    "technology": AIBackgroundType.AI_KEYWORDS_ONLY,
    "engineer": AIBackgroundType.AI_KEYWORDS_ONLY,
    "cloud": AIBackgroundType.AI_KEYWORDS_ONLY,
    "data": AIBackgroundType.AI_KEYWORDS_ONLY,
}

_WIKIDATA_ROLE_MAP = {
    "P169": "CEO",
    "P488": "Chairperson",
    "P3320": "Board Member",
    "P1037": "Director",
}


def _get_wikipedia_text(name: str) -> str:
    """Get full Wikipedia article text for an executive."""
    try:
        resp = _requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "titles": name,
                "prop": "extracts",
                "explaintext": True,
                "format": "json"
            },
            headers=_WIKI_HEADERS,
            timeout=10
        )
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            return page.get("extract", "").lower()
    except Exception as e:
        _logger.debug(f"Wikipedia fetch failed for {name}: {e}")
    return ""


def _detect_ai_indicators(wiki_text: str) -> List[AIBackgroundType]:
    """Detect AI background indicators from Wikipedia text."""
    found = set()
    for keyword, indicator in _WIKI_AI_INDICATOR_MAP.items():
        if keyword in wiki_text:
            found.add(indicator)
    return list(found)


def _get_wikidata_company_id(company_name: str) -> Optional[str]:
    """Find Wikidata entity ID for a company."""
    try:
        resp = _requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbsearchentities",
                "search": company_name,
                "language": "en",
                "type": "item",
                "format": "json",
                "limit": 1
            },
            headers=_WIKI_HEADERS,
            timeout=10
        )
        results = resp.json().get("search", [])
        return results[0]["id"] if results else None
    except Exception as e:
        _logger.warning(f"Wikidata search failed for {company_name}: {e}")
        return None


def _get_wikidata_executives(wikidata_id: str, company_name: str) -> List[dict]:
    """Get current executives from Wikidata for a company."""
    executives = []
    for prop, role in _WIKIDATA_ROLE_MAP.items():
        try:
            resp = _requests.get(
                "https://www.wikidata.org/w/api.php",
                params={
                    "action": "wbgetclaims",
                    "entity": wikidata_id,
                    "property": prop,
                    "format": "json"
                },
                headers=_WIKI_HEADERS,
                timeout=10
            )
            claims = resp.json().get("claims", {}).get(prop, [])
            for c in claims:
                # Skip former executives (with end time P582)
                if "P582" in c.get("qualifiers", {}):
                    continue
                val = c.get("mainsnak", {}).get("datavalue", {}).get("value", {})
                entity_id = val.get("id") if isinstance(val, dict) else None
                if not entity_id:
                    continue
                # Get executive name
                resp2 = _requests.get(
                    "https://www.wikidata.org/w/api.php",
                    params={
                        "action": "wbgetentities",
                        "ids": entity_id,
                        "props": "labels",
                        "language": "en",
                        "format": "json"
                    },
                    headers=_WIKI_HEADERS,
                    timeout=10
                )
                entity = resp2.json().get("entities", {}).get(entity_id, {})
                name = entity.get("labels", {}).get("en", {}).get("value", "")
                if name:
                    executives.append({"name": name, "role": role, "company": company_name})
        except Exception as e:
            _logger.debug(f"Wikidata {prop} fetch failed: {e}")
    return executives


def _resolve_company_name(company_name: str) -> str:
    """Resolve ticker-style names to full company names via SEC EDGAR."""
    # If name looks like a ticker (short, all caps), look up real name
    if len(company_name) <= 5 and company_name.upper() == company_name:
        try:
            resp = _requests.get(
                "https://www.sec.gov/files/company_tickers.json",
                headers=_WIKI_HEADERS, timeout=10
            )
            if resp.status_code == 200:
                for entry in resp.json().values():
                    if str(entry.get("ticker", "")).upper() == company_name.upper():
                        full_name = entry.get("title", "")
                        if full_name:
                            # Clean SEC format: "AMAZON COM INC" -> "Amazon"
                            import re as _re
                            clean = full_name.title()
                            # Remove trailing legal suffixes
                            clean = _re.sub(r'\b(Inc|Corp|Co|Ltd|Llc|Com|Holdings|Group|Corporation|Limited|Incorporated)\b\.?', '', clean)
                            # Remove extra whitespace
                            clean = ' '.join(clean.split())
                            # Take first meaningful word(s) - max 2 words
                            words = clean.split()
                            clean = ' '.join(words[:2]) if len(words) > 2 else clean
                            clean = clean.strip()
                            _logger.info(f"Resolved {company_name} -> {clean}")
                            return clean
        except Exception:
            pass
    return company_name


def collect_leadership_profiles_from_web(
    company_name: str,
    company_id: str,
) -> List[LeadershipProfile]:
    """
    Collect LeadershipProfile objects for any public company using:
    1. Wikidata — current C-suite and board members
    2. Wikipedia — AI background detection from article text

    Works for any publicly listed company. Falls back gracefully.
    """
    # Resolve ticker-style names to full company names
    company_name = _resolve_company_name(company_name)
    _logger.info(f"Collecting web leadership profiles for {company_name}")

    wikidata_id = _get_wikidata_company_id(company_name)
    if not wikidata_id:
        _logger.warning(f"No Wikidata ID found for {company_name}")
        return []

    raw_executives = _get_wikidata_executives(wikidata_id, company_name)
    _logger.info(f"Wikidata: found {len(raw_executives)} executives for {company_name}")

    profiles = []
    seen_names = set()

    for exec_data in raw_executives:
        name = exec_data["name"]
        if name in seen_names:
            continue
        seen_names.add(name)

        # Get Wikipedia text for AI background detection
        wiki_text = _get_wikipedia_text(name)
        ai_indicators = _detect_ai_indicators(wiki_text)

        # Default to AI_KEYWORDS_ONLY if tech executive with no specific indicators
        if not ai_indicators and wiki_text and any(
            kw in wiki_text for kw in ["microsoft", "amazon", "google", "apple", "meta", "tech"]
        ):
            ai_indicators = [AIBackgroundType.AI_KEYWORDS_ONLY]

        profiles.append(
            LeadershipProfile(
                name=name,
                title=exec_data["role"],
                company=company_name,
                ai_indicators=ai_indicators,
                url=f"https://en.wikipedia.org/wiki/{name.replace(' ', '_')}",
                observed_date=datetime.utcnow().strftime("%Y-%m-%d"),
            )
        )

    _logger.info(f"Web leadership: {len(profiles)} profiles collected for {company_name}")
    return profiles