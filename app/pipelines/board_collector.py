# app/pipelines/board_collector.py
# SEC EDGAR proxy-statement scraper for board composition data.

import json
import re
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# SEC EDGAR CIK numbers for target companies
COMPANY_CIKS: Dict[str, str] = {
    "NVDA": "1045810",
    "JPM": "19617",
    "WMT": "104169",
    "GE": "40554",
    "DG": "34408",
}

# Polite EDGAR headers (required by SEC fair-access policy)
EDGAR_HEADERS = {
    "User-Agent": "PE-OrgAIR research@example.com",
    "Accept-Encoding": "gzip, deflate",
}


class BoardCompositionCollector:
    """Collect board composition data from SEC DEF 14A proxy statements."""

    def __init__(self, data_dir: str = "data/board"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect_board_data(
        self, ticker: str, use_cache: bool = True
    ) -> Dict:
        """
        Main entry point: return board data dict for *ticker*.

        Returns dict with keys:
            members  – list of member dicts
            committees – list of committee name strings
            strategy_text – proxy narrative mentioning AI/strategy
        """
        ticker = ticker.upper()

        if use_cache:
            cached = self.load_from_cache(ticker)
            if cached:
                return cached

        # Fetch & parse
        proxy_html = self._fetch_latest_proxy(ticker)
        if not proxy_html:
            logger.warning(f"No proxy HTML obtained for {ticker}, returning empty")
            return {"members": [], "committees": [], "strategy_text": ""}

        data = self.parse_proxy_html(proxy_html)
        self._cache_results(ticker, data)
        return data

    # ------------------------------------------------------------------
    # EDGAR fetching
    # ------------------------------------------------------------------

    def _fetch_latest_proxy(self, ticker: str) -> Optional[str]:
        """Fetch the most recent DEF 14A filing HTML from EDGAR."""
        cik = COMPANY_CIKS.get(ticker)
        if not cik:
            logger.warning(f"No CIK mapping for ticker {ticker}")
            return None

        # Step 1: find DEF 14A filing via EDGAR full-text search
        search_url = (
            "https://efts.sec.gov/LATEST/search-index"
            f"?q=%22DEF+14A%22&dateRange=custom"
            f"&startdt=2023-01-01&enddt=2025-12-31"
            f"&forms=DEF+14A"
            f"&entityName={cik}"
        )

        # Fallback: use the EDGAR submissions API (more reliable)
        submissions_url = (
            f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
        )

        try:
            logger.info(f"Fetching EDGAR submissions for {ticker} (CIK {cik})")
            resp = requests.get(submissions_url, headers=EDGAR_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            filings = data.get("filings", {}).get("recent", {})
            forms = filings.get("form", [])
            accessions = filings.get("accessionNumber", [])
            primary_docs = filings.get("primaryDocument", [])

            # Find latest DEF 14A
            for i, form in enumerate(forms):
                if form == "DEF 14A":
                    accession = accessions[i].replace("-", "")
                    doc = primary_docs[i]
                    filing_url = (
                        f"https://www.sec.gov/Archives/edgar/data/"
                        f"{cik}/{accession}/{doc}"
                    )
                    logger.info(f"Found DEF 14A for {ticker}: {filing_url}")
                    time.sleep(0.2)  # SEC rate-limit courtesy
                    doc_resp = requests.get(
                        filing_url, headers=EDGAR_HEADERS, timeout=30
                    )
                    doc_resp.raise_for_status()
                    return doc_resp.text

            logger.warning(f"No DEF 14A found in recent filings for {ticker}")
            return None

        except requests.RequestException as e:
            logger.error(f"EDGAR request failed for {ticker}: {e}")
            return None

    # ------------------------------------------------------------------
    # HTML parsing
    # ------------------------------------------------------------------

    def parse_proxy_html(self, html: str) -> Dict:
        """
        Parse proxy statement HTML to extract board composition data.

        Returns dict with members, committees, strategy_text.
        """
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True).lower()

        members = self._extract_members(soup, text)
        committees = self._extract_committees(soup, text)
        strategy_text = self._extract_strategy_text(text)

        return {
            "members": [self._member_to_dict(m) for m in members],
            "committees": committees,
            "strategy_text": strategy_text,
        }

    def _extract_members(
        self, soup: BeautifulSoup, full_text: str
    ) -> List[Dict]:
        """Extract board member information from proxy HTML."""
        members: List[Dict] = []
        seen_names: set = set()

        # Strategy 1: look for director nominee tables
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    name_text = cells[0].get_text(strip=True)
                    rest_text = " ".join(c.get_text(strip=True) for c in cells[1:])

                    # Heuristic: a name cell is short, title-case, and has no numbers
                    if (
                        5 < len(name_text) < 60
                        and not re.search(r"\d{4}", name_text)
                        and name_text not in seen_names
                    ):
                        is_independent = "independent" in rest_text.lower()
                        member = {
                            "name": name_text,
                            "title": self._guess_title(rest_text),
                            "bio": rest_text[:500],
                            "is_independent": is_independent,
                            "committees": self._extract_member_committees(rest_text),
                            "tenure_years": self._extract_tenure(rest_text),
                        }
                        members.append(member)
                        seen_names.add(name_text)

        # Strategy 2: look for bold/heading names in director sections
        if len(members) < 3:
            director_section = self._find_director_section(soup)
            if director_section:
                for bold in director_section.find_all(["b", "strong"]):
                    name_text = bold.get_text(strip=True)
                    if (
                        5 < len(name_text) < 60
                        and name_text not in seen_names
                        and not re.search(r"\d{4}", name_text)
                    ):
                        # Get surrounding text as bio
                        parent = bold.parent
                        bio = parent.get_text(strip=True)[:500] if parent else ""
                        member = {
                            "name": name_text,
                            "title": self._guess_title(bio),
                            "bio": bio,
                            "is_independent": "independent" in bio.lower(),
                            "committees": self._extract_member_committees(bio),
                            "tenure_years": self._extract_tenure(bio),
                        }
                        members.append(member)
                        seen_names.add(name_text)

        logger.info(f"Extracted {len(members)} board members")
        return members

    def _find_director_section(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """Find the section of the proxy about director nominees."""
        patterns = [
            r"director\s+nominees",
            r"proposal.*election.*directors",
            r"nominees\s+for\s+election",
            r"board\s+of\s+directors",
        ]
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "div", "span"]):
            tag_text = tag.get_text(strip=True).lower()
            for pattern in patterns:
                if re.search(pattern, tag_text):
                    # Return the parent container
                    return tag.parent
        return None

    def _guess_title(self, text: str) -> str:
        """Extract a title/role from surrounding text."""
        text_lower = text.lower()
        title_patterns = [
            r"(chief\s+\w+\s+officer)",
            r"(president\s+and\s+\w+)",
            r"(chairman\b[^.]{0,30})",
            r"(lead\s+independent\s+director)",
            r"(independent\s+director)",
            r"(director)",
        ]
        for pattern in title_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1).strip().title()
        return "Director"

    def _extract_member_committees(self, text: str) -> List[str]:
        """Extract committee memberships from text."""
        committees = []
        text_lower = text.lower()
        committee_names = [
            "audit", "compensation", "nominating", "governance",
            "technology", "risk", "finance", "executive",
            "innovation", "digital", "cyber", "data",
        ]
        for name in committee_names:
            if name in text_lower:
                committees.append(name.title() + " Committee")
        return committees

    def _extract_tenure(self, text: str) -> float:
        """Extract board tenure in years from text."""
        match = re.search(
            r"(?:since|appointed|joined|serving since)\s*(\d{4})", text.lower()
        )
        if match:
            year = int(match.group(1))
            return max(0.0, 2025 - year)
        return 0.0

    def _extract_committees(
        self, soup: BeautifulSoup, full_text: str
    ) -> List[str]:
        """Extract board committee names from the proxy."""
        committees: List[str] = []
        seen: set = set()

        committee_patterns = [
            r"(audit\s+committee)",
            r"(compensation\s+committee)",
            r"(nominating\s+(?:and\s+)?(?:corporate\s+)?governance\s+committee)",
            r"(technology\s+(?:and\s+)?(?:\w+\s+)?committee)",
            r"(risk\s+(?:management\s+)?committee)",
            r"(innovation\s+committee)",
            r"(digital\s+(?:\w+\s+)?committee)",
            r"(executive\s+committee)",
            r"(finance\s+committee)",
            r"(cyber(?:security)?\s+committee)",
            r"(data\s+(?:\w+\s+)?committee)",
        ]

        for pattern in committee_patterns:
            matches = re.findall(pattern, full_text)
            for m in matches:
                name = m.strip().title()
                if name not in seen:
                    committees.append(name)
                    seen.add(name)

        logger.info(f"Extracted {len(committees)} committees")
        return committees

    def _extract_strategy_text(self, full_text: str) -> str:
        """Extract strategy-related passages mentioning AI/ML/technology."""
        keywords = [
            "artificial intelligence",
            "machine learning",
            "ai strategy",
            "digital transformation",
            "technology strategy",
        ]

        passages: List[str] = []
        sentences = re.split(r"[.!?]+", full_text)
        for sentence in sentences:
            if any(kw in sentence for kw in keywords):
                clean = sentence.strip()
                if 20 < len(clean) < 500:
                    passages.append(clean)

        return ". ".join(passages[:10])

    # ------------------------------------------------------------------
    # Caching
    # ------------------------------------------------------------------

    def _cache_results(self, ticker: str, data: Dict) -> None:
        """Save parsed board data to JSON cache."""
        cache_file = self.data_dir / f"{ticker}.json"
        payload = {
            "ticker": ticker,
            "source": "SEC EDGAR DEF 14A",
            "collected_at": datetime.now().isoformat(),
            "member_count": len(data.get("members", [])),
            **data,
        }
        with open(cache_file, "w") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Cached board data to {cache_file}")

    def load_from_cache(self, ticker: str) -> Optional[Dict]:
        """Load board data from cache if available."""
        cache_file = self.data_dir / f"{ticker.upper()}.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            logger.info(f"Loaded board data from cache for {ticker}")
            return {
                "members": data.get("members", []),
                "committees": data.get("committees", []),
                "strategy_text": data.get("strategy_text", ""),
            }
        except Exception as e:
            logger.error(f"Error loading board cache for {ticker}: {e}")
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _member_to_dict(member: Dict) -> Dict:
        """Ensure member dict has all expected keys."""
        return {
            "name": member.get("name", ""),
            "title": member.get("title", "Director"),
            "bio": member.get("bio", ""),
            "is_independent": member.get("is_independent", False),
            "committees": member.get("committees", []),
            "tenure_years": member.get("tenure_years", 0.0),
        }
