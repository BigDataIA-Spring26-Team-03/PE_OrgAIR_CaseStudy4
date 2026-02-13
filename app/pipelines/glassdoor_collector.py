# app/pipelines/glassdoor_collector.py
# (We'll keep the filename but scrape Indeed instead)

import asyncio
import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime

from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


@dataclass
class CompanyReview:
    """Single company review (from Indeed)."""
    review_id: str
    date: str
    rating: float
    title: str
    pros: str
    cons: str
    job_title: str
    location: str
    helpful_count: int = 0
    
    @property
    def full_text(self) -> str:
        """Combine all text fields for analysis."""
        return f"{self.title} {self.pros} {self.cons}".lower()


@dataclass
class CultureSignals:
    """Analyzed culture signals from reviews."""
    innovation_score: Decimal
    data_driven_score: Decimal
    change_readiness_score: Decimal
    experimentation_score: Decimal
    avg_rating: Decimal
    review_count: int
    positive_sentiment_ratio: Decimal
    innovation_keyword_count: int
    data_keyword_count: int
    individual_mentions: int = 0


@dataclass
class CultureScore:
    """Final culture assessment."""
    overall_score: Decimal  # 0-100
    signals: CultureSignals
    confidence: Decimal
    rationale: str


class IndeedCultureCollector:
    """
    Scrape and analyze Indeed company reviews to assess culture.
    
    Indeed is easier to scrape than Glassdoor and has similar data.
    """
    
    # Culture keywords
    INNOVATION_KEYWORDS = [
        "innovative", "innovation", "cutting-edge", "pioneering",
        "breakthrough", "experimental", "novel", "creative",
        "forward-thinking", "disruptive", "ai", "ml", "machine learning",
        "technology", "tech-forward"
    ]
    
    DATA_DRIVEN_KEYWORDS = [
        "data-driven", "data driven", "analytics", "metrics",
        "data science", "evidence-based", "data literacy",
        "data culture", "measurement", "kpi", "analysis"
    ]
    
    CHANGE_READINESS_KEYWORDS = [
        "open to change", "adaptable", "flexible", "agile",
        "embrace change", "transformation", "evolving",
        "progressive", "modern", "dynamic", "responsive"
    ]
    
    EXPERIMENTATION_KEYWORDS = [
        "experiment", "experimentation", "fail-fast", "fail fast",
        "try new things", "pilot", "prototype", "poc",
        "proof of concept", "testing", "iteration", "learning culture"
    ]
    
    NEGATIVE_CULTURE_KEYWORDS = [
        "bureaucratic", "resistant", "slow", "siloed",
        "hierarchical", "rigid", "outdated", "traditional",
        "conservative", "risk-averse", "hostile to change",
        "micromanagement", "toxic"
    ]
    
    # Indeed company URLs
    COMPANY_URLS = {
        "NVDA": "https://www.indeed.com/cmp/Nvidia/reviews",
        "JPM": "https://www.indeed.com/cmp/JPMorgan-Chase-and-Co/reviews",
        "WMT": "https://www.indeed.com/cmp/Walmart/reviews",
        "GE": "https://www.indeed.com/cmp/General-Electric/reviews",
        "DG": "https://www.indeed.com/cmp/Dollar-General/reviews"
    }
    
    def __init__(self, data_dir: str = "data/indeed", headless: bool = True):
        """
        Initialize collector.
        
        Args:
            data_dir: Directory to cache scraped data
            headless: Run browser in headless mode
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
    
    async def scrape_reviews(
        self, 
        ticker: str, 
        max_reviews: int = 20
    ) -> List[CompanyReview]:
        """
        Scrape Indeed reviews for a company.
        
        Args:
            ticker: Company ticker symbol
            max_reviews: Maximum number of reviews to scrape
            
        Returns:
            List of CompanyReview objects
        """
        if ticker not in self.COMPANY_URLS:
            logger.warning(f"No Indeed URL mapped for ticker: {ticker}")
            return []
        
        url = self.COMPANY_URLS[ticker]
        logger.info(f"Scraping Indeed reviews for {ticker} from {url}")
        
        reviews = []
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=self.headless)
            
            # Create context with realistic settings
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            try:
                # Navigate to Indeed
                logger.info(f"Loading page: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Wait a bit for content to load
                await page.wait_for_timeout(3000)
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Indeed review containers - try multiple selectors
                review_containers = (
                    soup.find_all('div', {'itemprop': 'review'}) or
                    soup.find_all('div', class_=re.compile('cmp-Review-container')) or
                    soup.find_all('div', class_=re.compile('css-.*review'))
                )
                
                logger.info(f"Found {len(review_containers)} review containers")
                
                if len(review_containers) == 0:
                    # Try alternative: look for any div with review-like content
                    all_divs = soup.find_all('div')
                    for div in all_divs:
                        text = div.get_text().lower()
                        if 'pros' in text and 'cons' in text:
                            review_containers.append(div)
                    
                    logger.info(f"Alternative search found {len(review_containers)} potential reviews")
                
                # Parse reviews
                for i, container in enumerate(review_containers[:max_reviews]):
                    try:
                        review = self._parse_review(container, i)
                        if review:
                            reviews.append(review)
                    except Exception as e:
                        logger.error(f"Error parsing review {i}: {e}")
                        continue
                
                logger.info(f"Successfully scraped {len(reviews)} reviews for {ticker}")
                
            except PlaywrightTimeoutError:
                logger.error(f"Timeout while loading Indeed page for {ticker}")
            except Exception as e:
                logger.error(f"Error scraping {ticker}: {e}", exc_info=True)
            finally:
                await browser.close()
        
        # Cache the results
        if reviews:
            self._cache_reviews(ticker, reviews)
        
        return reviews
    
    def _parse_review(self, container, index: int) -> Optional[CompanyReview]:
        """Parse a single review from HTML."""
        try:
            # Extract rating (1-5 stars)
            rating_elem = container.find('button', class_=re.compile('rating')) or \
                         container.find('div', class_=re.compile('rating')) or \
                         container.find('span', {'itemprop': 'ratingValue'})
            
            rating = 3.0  # Default
            if rating_elem:
                # Try to extract number from aria-label or text
                aria_label = rating_elem.get('aria-label', '')
                rating_match = re.search(r'(\d+\.?\d*)\s*out of\s*5', aria_label)
                if rating_match:
                    rating = float(rating_match.group(1))
                else:
                    # Try to count stars
                    star_count = len(container.find_all('svg', class_=re.compile('star')))
                    if star_count > 0:
                        rating = float(star_count)
            
            # Extract title
            title_elem = container.find('span', {'itemprop': 'name'}) or \
                        container.find('a', class_=re.compile('reviewLink')) or \
                        container.find('h2') or \
                        container.find('div', class_=re.compile('title'))
            title = title_elem.get_text(strip=True) if title_elem else "Review"
            
            # Extract pros
            pros_elem = container.find('span', {'itemprop': 'reviewBody'})
            if not pros_elem:
                # Look for text containing "Pros"
                for elem in container.find_all(['div', 'span', 'p']):
                    text = elem.get_text()
                    if 'Pros' in text or 'pros' in text:
                        pros_elem = elem
                        break
            pros = pros_elem.get_text(strip=True) if pros_elem else ""
            
            # Extract cons
            cons_elem = None
            for elem in container.find_all(['div', 'span', 'p']):
                text = elem.get_text()
                if 'Cons' in text or 'cons' in text:
                    cons_elem = elem
                    break
            cons = cons_elem.get_text(strip=True) if cons_elem else ""
            
            # Clean pros/cons (remove labels)
            pros = re.sub(r'^Pros:?\s*', '', pros, flags=re.IGNORECASE)
            cons = re.sub(r'^Cons:?\s*', '', cons, flags=re.IGNORECASE)
            
            # Extract job title
            job_elem = container.find('span', class_=re.compile('jobTitle')) or \
                      container.find('div', class_=re.compile('employee'))
            job_title = job_elem.get_text(strip=True) if job_elem else "Employee"
            
            # Extract location
            location_elem = container.find('span', class_=re.compile('location'))
            location = location_elem.get_text(strip=True) if location_elem else "Unknown"
            
            # Extract date
            date_elem = container.find('span', class_=re.compile('date')) or \
                       container.find('time')
            date = date_elem.get_text(strip=True) if date_elem else datetime.now().strftime("%Y-%m-%d")
            
            # Skip if no meaningful content
            if not pros and not cons:
                return None
            
            return CompanyReview(
                review_id=f"r{index}",
                date=date,
                rating=rating,
                title=title,
                pros=pros,
                cons=cons,
                job_title=job_title,
                location=location,
                helpful_count=0
            )
            
        except Exception as e:
            logger.error(f"Error parsing review: {e}", exc_info=True)
            return None
    
    def _cache_reviews(self, ticker: str, reviews: List[CompanyReview]):
        """Save reviews to JSON cache."""
        cache_file = self.data_dir / f"{ticker}.json"
        
        data = {
            "company": ticker,
            "ticker": ticker,
            "source": "Indeed",
            "scraped_at": datetime.now().isoformat(),
            "review_count": len(reviews),
            "reviews": [
                {
                    "review_id": r.review_id,
                    "date": r.date,
                    "rating": r.rating,
                    "title": r.title,
                    "pros": r.pros,
                    "cons": r.cons,
                    "job_title": r.job_title,
                    "location": r.location,
                    "helpful_count": r.helpful_count
                }
                for r in reviews
            ]
        }
        
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Cached {len(reviews)} reviews to {cache_file}")
    
    def load_from_cache(self, ticker: str) -> List[CompanyReview]:
        """Load reviews from cache if available."""
        cache_file = self.data_dir / f"{ticker}.json"
        
        if not cache_file.exists():
            return []
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            reviews = [
                CompanyReview(**review)
                for review in data.get('reviews', [])
            ]
            
            logger.info(f"Loaded {len(reviews)} reviews from cache for {ticker}")
            return reviews
            
        except Exception as e:
            logger.error(f"Error loading cache for {ticker}: {e}")
            return []
    
    async def fetch_reviews(
        self, 
        ticker: str, 
        use_cache: bool = True,
        max_reviews: int = 20
    ) -> List[CompanyReview]:
        """
        Fetch reviews (from cache or by scraping).
        """
        if use_cache:
            reviews = self.load_from_cache(ticker)
            if reviews:
                return reviews
        
        # Scrape fresh data
        return await self.scrape_reviews(ticker, max_reviews)
    
    def analyze_culture_signals(
        self, 
        reviews: List[CompanyReview]
    ) -> CultureSignals:
        """Analyze reviews to extract culture signals."""
        if not reviews:
            return CultureSignals(
                innovation_score=Decimal("50"),
                data_driven_score=Decimal("50"),
                change_readiness_score=Decimal("50"),
                experimentation_score=Decimal("50"),
                avg_rating=Decimal("3.0"),
                review_count=0,
                positive_sentiment_ratio=Decimal("0.5"),
                innovation_keyword_count=0,
                data_keyword_count=0,
                individual_mentions=0
            )
        
        # Combine all text
        all_text = " ".join(review.full_text for review in reviews)
        
        # Count keywords
        innovation_count = self._count_keywords(all_text, self.INNOVATION_KEYWORDS)
        data_count = self._count_keywords(all_text, self.DATA_DRIVEN_KEYWORDS)
        change_count = self._count_keywords(all_text, self.CHANGE_READINESS_KEYWORDS)
        experiment_count = self._count_keywords(all_text, self.EXPERIMENTATION_KEYWORDS)
        negative_count = self._count_keywords(all_text, self.NEGATIVE_CULTURE_KEYWORDS)
        
        # Calculate metrics
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
        positive_reviews = sum(1 for r in reviews if r.rating >= 4.0)
        positive_ratio = positive_reviews / len(reviews)
        
        # Calculate dimension scores
        innovation_score = self._calculate_dimension_score(
            innovation_count, len(reviews), avg_rating, negative_count
        )
        data_driven_score = self._calculate_dimension_score(
            data_count, len(reviews), avg_rating, negative_count
        )
        change_readiness_score = self._calculate_dimension_score(
            change_count, len(reviews), avg_rating, negative_count
        )
        experimentation_score = self._calculate_dimension_score(
            experiment_count, len(reviews), avg_rating, negative_count
        )
        
        # Count individual mentions
        individual_mentions = self._count_individual_mentions(all_text)
        
        return CultureSignals(
            innovation_score=Decimal(str(innovation_score)),
            data_driven_score=Decimal(str(data_driven_score)),
            change_readiness_score=Decimal(str(change_readiness_score)),
            experimentation_score=Decimal(str(experimentation_score)),
            avg_rating=Decimal(str(round(avg_rating, 2))),
            review_count=len(reviews),
            positive_sentiment_ratio=Decimal(str(round(positive_ratio, 2))),
            innovation_keyword_count=innovation_count,
            data_keyword_count=data_count,
            individual_mentions=individual_mentions
        )
    
    async def calculate_culture_score(
        self,
        ticker: str,
        use_cache: bool = True
    ) -> CultureScore:
        """
        Main method: Fetch and analyze culture score.
        """
        reviews = await self.fetch_reviews(ticker, use_cache=use_cache)
        signals = self.analyze_culture_signals(reviews)
        
        # Calculate overall score
        overall_score = (
            signals.innovation_score * Decimal("0.35") +
            signals.data_driven_score * Decimal("0.30") +
            signals.change_readiness_score * Decimal("0.20") +
            signals.experimentation_score * Decimal("0.15")
        )
        
        # Adjust for rating quality
        rating_adjustment = (signals.avg_rating - Decimal("3.0")) / Decimal("2.0")
        overall_score = overall_score + (rating_adjustment * Decimal("10"))
        
        # Clamp to 0-100
        overall_score = max(Decimal("0"), min(Decimal("100"), overall_score))
        
        # Calculate confidence
        confidence = self._calculate_confidence(signals.review_count)
        
        # Generate rationale
        rationale = self._generate_rationale(signals)
        
        return CultureScore(
            overall_score=overall_score,
            signals=signals,
            confidence=confidence,
            rationale=rationale
        )
    
    # Helper methods
    def _count_keywords(self, text: str, keywords: List[str]) -> int:
        count = 0
        for keyword in keywords:
            count += len(re.findall(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE))
        return count
    
    def _calculate_dimension_score(
        self, keyword_count: int, review_count: int, 
        avg_rating: float, negative_count: int
    ) -> float:
        if review_count == 0:
            return 50.0
        
        density = keyword_count / review_count
        base_score = min(70, density * 30)
        rating_boost = max(0, (avg_rating - 3.0) * 10)
        negative_density = negative_count / review_count
        negative_penalty = min(10, negative_density * 20)
        
        score = base_score + rating_boost - negative_penalty
        return max(0, min(100, score))
    
    def _count_individual_mentions(self, text: str) -> int:
        pattern = r'\b[A-Z][a-z]+(?:\'s|\s+is|\s+was|\s+has|\s+does)\b'
        matches = re.findall(pattern, text)
        return len(matches)
    
    def _calculate_confidence(self, review_count: int) -> Decimal:
        if review_count == 0:
            return Decimal("0.1")
        elif review_count < 5:
            return Decimal("0.4")
        elif review_count < 10:
            return Decimal("0.6")
        elif review_count < 20:
            return Decimal("0.8")
        else:
            return Decimal("0.9")
    
    def _generate_rationale(self, signals: CultureSignals) -> str:
        parts = []
        
        if signals.avg_rating >= 4.0:
            parts.append("Strong positive employee sentiment")
        elif signals.avg_rating >= 3.5:
            parts.append("Generally positive employee sentiment")
        else:
            parts.append("Mixed employee sentiment")
        
        if signals.innovation_score >= 70:
            parts.append("high innovation culture")
        elif signals.innovation_score >= 50:
            parts.append("moderate innovation culture")
        
        if signals.data_driven_score >= 70:
            parts.append("strong data-driven decision making")
        elif signals.data_driven_score >= 50:
            parts.append("emerging data culture")
        
        parts.append(f"based on {signals.review_count} reviews")
        
        return "; ".join(parts)


# Async wrapper function (keep name for compatibility)
async def collect_glassdoor_data(ticker: str, use_cache: bool = True) -> Dict:
    """
    Convenience function to collect company culture data from Indeed.
    Note: Function name kept as 'glassdoor' for compatibility.
    """
    collector = IndeedCultureCollector()
    culture_score = await collector.calculate_culture_score(ticker, use_cache=use_cache)
    
    return {
        "ticker": ticker,
        "source": "Indeed",
        "culture_score": float(culture_score.overall_score),
        "avg_rating": float(culture_score.signals.avg_rating),
        "review_count": culture_score.signals.review_count,
        "confidence": float(culture_score.confidence),
        "innovation_score": float(culture_score.signals.innovation_score),
        "data_driven_score": float(culture_score.signals.data_driven_score),
        "individual_mentions": culture_score.signals.individual_mentions,
        "rationale": culture_score.rationale
    }