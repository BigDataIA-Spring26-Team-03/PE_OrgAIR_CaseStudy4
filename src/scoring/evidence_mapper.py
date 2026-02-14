# src/scoring/evidence_mapper.py
# Evidence sources → weighted contributions → 7 final dimension scores

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from decimal import Decimal
import logging
from scoring.rubric_scorer import (
    RubricScorer,
    concatenate_evidence_chunks,
    extract_quantitative_metrics
)
logger = logging.getLogger(__name__)

# ENUMS & DATA MODELS

class Dimension(str, Enum):
    """The 7 dimensions of organizational AI readiness."""
    DATA_INFRASTRUCTURE = "data_infrastructure"
    AI_GOVERNANCE = "ai_governance"
    TECHNOLOGY_STACK = "technology_stack"
    TALENT = "talent"
    LEADERSHIP = "leadership"
    USE_CASE_PORTFOLIO = "use_case_portfolio"
    CULTURE = "culture"


class SignalSource(str, Enum):
    """Evidence sources from CS2 and CS3."""
    
    # CS2 External Signals (from external_signals table)
    TECHNOLOGY_HIRING = "technology_hiring"
    INNOVATION_ACTIVITY = "innovation_activity"
    DIGITAL_PRESENCE = "digital_presence"
    LEADERSHIP_SIGNALS = "leadership_signals"
    
    # CS2 SEC Sections (from document_chunks_sec.section column)
    SEC_ITEM_1 = "Item 1 (Business)"
    SEC_ITEM_1A = "Item 1A (Risk)"
    SEC_ITEM_7 = "Item 7 (MD&A)"
    SEC_ITEM_2 = "Item 2 (MD&A)"
    SEC_ITEM_8_01 = "Item 8.01 (Events)"
    
    # CS3 New Sources
    GLASSDOOR_REVIEWS = "glassdoor_reviews"
    BOARD_COMPOSITION = "board_composition"


@dataclass
# Describes how one source contributes to mapping
class DimensionMapping:
    source: SignalSource
    primary_dimension: Dimension
    primary_weight: Decimal
    secondary_mappings: Dict[Dimension, Decimal] = field(default_factory=dict)
    reliability: Decimal = Decimal("0.8")  # Source reliability (0-1)
    
    def __post_init__(self):
        """Validate that weights sum to 1.0."""
        total_weight = self.primary_weight + sum(self.secondary_mappings.values())
        if abs(total_weight - Decimal("1.0")) > Decimal("0.001"):
            raise ValueError(
                f"Weights for {self.source.value} must sum to 1.0, got {total_weight}"
            )


@dataclass
# Score from a single evidence source Eg: All Item 1 chunks, ALL job postings
class EvidenceScore:
    source: SignalSource
    raw_score: Decimal  # 0-100
    confidence: Decimal  # 0-1
    evidence_count: int  # Number of data points
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate score and confidence bounds."""
        if not (Decimal("0") <= self.raw_score <= Decimal("100")):
            raise ValueError(f"raw_score must be in [0, 100], got {self.raw_score}")
        if not (Decimal("0") <= self.confidence <= Decimal("1")):
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")


@dataclass
# Final score per dimension
class DimensionScore:
    dimension: Dimension
    score: Decimal  # Final weighted score (0-100)
    contributing_sources: List[SignalSource]
    total_weight: Decimal
    confidence: Decimal
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "dimension": self.dimension.value,
            "score": float(self.score),
            "contributing_sources": [s.value for s in self.contributing_sources],
            "total_weight": float(self.total_weight),
            "confidence": float(self.confidence)
        }


# THE CRITICAL MAPPING TABLE

SIGNAL_TO_DIMENSION_MAP: Dict[SignalSource, DimensionMapping] = {
    
    # CS2 External Signals
    
    SignalSource.TECHNOLOGY_HIRING: DimensionMapping(
        source=SignalSource.TECHNOLOGY_HIRING,
        primary_dimension=Dimension.TALENT,
        primary_weight=Decimal("0.70"),
        secondary_mappings={
            Dimension.TECHNOLOGY_STACK: Decimal("0.20"),
            Dimension.CULTURE: Decimal("0.10"),
        },
        reliability=Decimal("0.85"),
    ),
    
    SignalSource.INNOVATION_ACTIVITY: DimensionMapping(
        source=SignalSource.INNOVATION_ACTIVITY,
        primary_dimension=Dimension.TECHNOLOGY_STACK,
        primary_weight=Decimal("0.50"),
        secondary_mappings={
            Dimension.USE_CASE_PORTFOLIO: Decimal("0.30"),
            Dimension.DATA_INFRASTRUCTURE: Decimal("0.20"),
        },
        reliability=Decimal("0.80"),
    ),
    
    SignalSource.DIGITAL_PRESENCE: DimensionMapping(
        source=SignalSource.DIGITAL_PRESENCE,
        primary_dimension=Dimension.DATA_INFRASTRUCTURE,
        primary_weight=Decimal("0.60"),
        secondary_mappings={
            Dimension.TECHNOLOGY_STACK: Decimal("0.40"),
        },
        reliability=Decimal("0.75"),
    ),
    
    SignalSource.LEADERSHIP_SIGNALS: DimensionMapping(
        source=SignalSource.LEADERSHIP_SIGNALS,
        primary_dimension=Dimension.LEADERSHIP,
        primary_weight=Decimal("0.60"),
        secondary_mappings={
            Dimension.AI_GOVERNANCE: Decimal("0.25"),
            Dimension.CULTURE: Decimal("0.15"),
        },
        reliability=Decimal("0.80"),
    ),
    
    # CS2 SEC Sections
    # ----------------
    
    SignalSource.SEC_ITEM_1: DimensionMapping(
        source=SignalSource.SEC_ITEM_1,
        primary_dimension=Dimension.USE_CASE_PORTFOLIO,
        primary_weight=Decimal("0.70"),
        secondary_mappings={
            Dimension.TECHNOLOGY_STACK: Decimal("0.30"),
        },
        reliability=Decimal("0.90"),
    ),
    
    SignalSource.SEC_ITEM_1A: DimensionMapping(
        source=SignalSource.SEC_ITEM_1A,
        primary_dimension=Dimension.AI_GOVERNANCE,
        primary_weight=Decimal("0.80"),
        secondary_mappings={
            Dimension.DATA_INFRASTRUCTURE: Decimal("0.20"),
        },
        reliability=Decimal("0.90"),
    ),
    
    SignalSource.SEC_ITEM_7: DimensionMapping(
        source=SignalSource.SEC_ITEM_7,
        primary_dimension=Dimension.LEADERSHIP,
        primary_weight=Decimal("0.50"),
        secondary_mappings={
            Dimension.USE_CASE_PORTFOLIO: Decimal("0.30"),
            Dimension.DATA_INFRASTRUCTURE: Decimal("0.20"),
        },
        reliability=Decimal("0.85"),
    ),
    
    SignalSource.SEC_ITEM_2: DimensionMapping(
        source=SignalSource.SEC_ITEM_2,
        primary_dimension=Dimension.LEADERSHIP,
        primary_weight=Decimal("0.50"),
        secondary_mappings={
            Dimension.USE_CASE_PORTFOLIO: Decimal("0.30"),
            Dimension.DATA_INFRASTRUCTURE: Decimal("0.20"),
        },
        reliability=Decimal("0.85"),
    ),
    
    SignalSource.SEC_ITEM_8_01: DimensionMapping(
        source=SignalSource.SEC_ITEM_8_01,
        primary_dimension=Dimension.LEADERSHIP,
        primary_weight=Decimal("1.0"),
        secondary_mappings={},
        reliability=Decimal("0.70"),
    ),
    
    # CS3 New Sources
    
    SignalSource.GLASSDOOR_REVIEWS: DimensionMapping(
        source=SignalSource.GLASSDOOR_REVIEWS,
        primary_dimension=Dimension.CULTURE,
        primary_weight=Decimal("0.80"),
        secondary_mappings={
            Dimension.TALENT: Decimal("0.10"),
            Dimension.LEADERSHIP: Decimal("0.10"),
        },
        reliability=Decimal("0.70"),
    ),
    
    SignalSource.BOARD_COMPOSITION: DimensionMapping(
        source=SignalSource.BOARD_COMPOSITION,
        primary_dimension=Dimension.AI_GOVERNANCE,
        primary_weight=Decimal("0.70"),
        secondary_mappings={
            Dimension.LEADERSHIP: Decimal("0.30"),
        },
        reliability=Decimal("0.85"),
    ),
}


# EVIDENCE MAPPER CLASS
# Maps CS2 evidence to 7 V^R dimensions.
class EvidenceMapper:
    
    def __init__(self):
        """Initialize with mapping table."""
        self.mappings = SIGNAL_TO_DIMENSION_MAP
        logger.info(
            "EvidenceMapper initialized",
            signal_sources=len(self.mappings),
            dimensions=len(Dimension)
        )
    
    def map_evidence_to_dimensions(
        self,
        evidence_scores: List[EvidenceScore]
    ) -> Dict[Dimension, DimensionScore]:
        
        if not evidence_scores:
            logger.warning("No evidence scores provided, returning defaults")
            return self._default_dimension_scores()
        
        # Initialize accumulators for each dimension
        dimension_sums: Dict[Dimension, Decimal] = {
            dim: Decimal("0") for dim in Dimension
        }
        dimension_weights: Dict[Dimension, Decimal] = {
            dim: Decimal("0") for dim in Dimension
        }
        dimension_sources: Dict[Dimension, List[SignalSource]] = {
            dim: [] for dim in Dimension
        }
        dimension_confidences: Dict[Dimension, List[Decimal]] = {
            dim: [] for dim in Dimension
        }
        
        # Process each evidence score
        for ev in evidence_scores:
            # Look up mapping
            mapping = self.mappings.get(ev.source)
            if not mapping:
                logger.warning(f"No mapping found for source: {ev.source.value}")
                continue
            
            # Weight by confidence and reliability
            effective_score = ev.raw_score * ev.confidence * mapping.reliability # Influence 
            effective_weight = ev.confidence * mapping.reliability
            
            # Primary contribution
            dim = mapping.primary_dimension
            weight = mapping.primary_weight
            dimension_sums[dim] += effective_score * weight
            dimension_weights[dim] += weight * effective_weight
            dimension_sources[dim].append(ev.source)
            dimension_confidences[dim].append(ev.confidence)
            
            # Secondary contributions
            for dim, weight in mapping.secondary_mappings.items():
                dimension_sums[dim] += effective_score * weight
                dimension_weights[dim] += weight * effective_weight
                dimension_sources[dim].append(ev.source)
                dimension_confidences[dim].append(ev.confidence)
        
        # Calculate weighted averages and create DimensionScore objects
        dimension_scores = {}
        
        for dim in Dimension:
            total_weight = dimension_weights[dim]
            
            if total_weight == 0:
                # No evidence for this dimension - use default
                logger.warning(f"No evidence for dimension: {dim.value}")
                score = Decimal("50")
                confidence = Decimal("0.1")
                sources = []
            else:
                # Weighted average
                score = dimension_sums[dim] / total_weight
                
                # Clamp to [0, 100]
                score = max(Decimal("0"), min(Decimal("100"), score))
                
                # Average confidence across sources
                confidences = dimension_confidences[dim]
                confidence = sum(confidences) / len(confidences) if confidences else Decimal("0.1")
                
                # Adjust confidence based on number of unique sources
                unique_sources = list(set(dimension_sources[dim]))
                source_count = len(unique_sources)
                
                if source_count == 1:
                    confidence *= Decimal("0.7")  # Penalize single source
                elif source_count == 2:
                    confidence *= Decimal("0.9")  # Slight penalty
                elif source_count >= 3:
                    confidence *= Decimal("1.1")  # Boost multiple sources
                
                # Clamp confidence to [0, 1]
                confidence = max(Decimal("0"), min(Decimal("1"), confidence))
                
                sources = unique_sources
            
            dimension_scores[dim] = DimensionScore(
                dimension=dim,
                score=score,
                contributing_sources=sources,
                total_weight=total_weight,
                confidence=confidence
            )
        
        logger.info(
            "Evidence mapping complete",
            input_evidence_count=len(evidence_scores),
            dimensions_with_evidence=sum(1 for ds in dimension_scores.values() if len(ds.contributing_sources) > 0)
        )
        
        return dimension_scores
    
    def _default_dimension_scores(self) -> Dict[Dimension, DimensionScore]:
        """Return default scores when no evidence is available."""
        return {
            dim: DimensionScore(
                dimension=dim,
                score=Decimal("50"),
                contributing_sources=[],
                total_weight=Decimal("0"),
                confidence=Decimal("0.1")
            )
            for dim in Dimension
        }
    
    # Report which dimensions have evidence and which have gaps.
    def get_coverage_report(
        self,
        evidence_scores: List[EvidenceScore]
    ) -> Dict[str, Any]:
        dimension_scores = self.map_evidence_to_dimensions(evidence_scores)
        
        report = {
            "total_dimensions": len(Dimension),
            "dimensions_with_evidence": 0,
            "dimensions_without_evidence": [],
            "coverage_by_dimension": {}
        }
        
        for dim, score in dimension_scores.items():
            has_evidence = len(score.contributing_sources) > 0
            
            if has_evidence:
                report["dimensions_with_evidence"] += 1
            else:
                report["dimensions_without_evidence"].append(dim.value)
            
            report["coverage_by_dimension"][dim.value] = {
                "has_evidence": has_evidence,
                "source_count": len(score.contributing_sources),
                "sources": [s.value for s in score.contributing_sources],
                "total_weight": float(score.total_weight),
                "confidence": float(score.confidence),
                "score": float(score.score)
            }
        
        report["coverage_percentage"] = (
            report["dimensions_with_evidence"] / report["total_dimensions"] * 100
        )
        
        return report


# SNOWFLAKE DATA LOADING FUNCTIONS


# Aggregates chunks by section and converts to EvidenceScore objects
# Load SEC document chunks from Snowflake and score using rubrics
def load_sec_evidence_from_snowflake_with_rubrics(
    ticker: str,
    snowflake_service
) -> List[EvidenceScore]:
    # Initialize rubric scorer
    scorer = RubricScorer()
    
    # Load all chunks grouped by section
    query = """
        SELECT 
            c.section,
            c.content,
            c.word_count,
            COUNT(*) OVER (PARTITION BY c.section) as section_chunk_count
        FROM document_chunks_sec c
        JOIN documents_sec d ON c.document_id = d.id
        WHERE d.ticker = %(ticker)s
        AND c.section IS NOT NULL
        AND c.section != 'Unknown'
        AND c.section != 'Intro'
        ORDER BY c.section, c.chunk_index
    """
    
    try:
        results = snowflake_service.execute_query(query, {'ticker': ticker.upper()})
    except Exception as e:
        logger.error(f"Failed to load SEC evidence for {ticker}: {e}")
        return []
    
    if not results:
        logger.info(f"No SEC evidence found for {ticker}")
        return []
    
    # Group chunks by section
    chunks_by_section = {}
    for row in results:
        section = row['section']
        content = row['content']
        
        if section not in chunks_by_section:
            chunks_by_section[section] = []
        
        chunks_by_section[section].append(content)
    
    # Map sections to dimensions and score with rubrics
    evidence_scores = []
    
    for section, chunks in chunks_by_section.items():
        # Map section to SignalSource
        try:
            source = SignalSource(section)
        except ValueError:
            logger.warning(f"Unknown section type: {section}")
            continue
        
        # Determine which dimensions this section contributes to
        mapping = SIGNAL_TO_DIMENSION_MAP.get(source)
        if not mapping:
            logger.warning(f"No dimension mapping for section: {section}")
            continue
        
        # Get all dimensions this section maps to
        dimensions = [mapping.primary_dimension]
        dimensions.extend(mapping.secondary_mappings.keys())
        
        # Concatenate chunks for analysis
        concatenated_text = concatenate_evidence_chunks(chunks)
        
        # Score each dimension using rubrics
        for dimension in dimensions:
            # Extract any quantitative metrics from metadata
            # (In practice, you'd get these from your CS2 external signals)
            metrics = {}
            
            # Score using rubric
            rubric_result = scorer.score_dimension(
                dimension.value,
                concatenated_text,
                metrics
            )
            
            # Determine weight based on primary vs secondary
            if dimension == mapping.primary_dimension:
                weight_factor = mapping.primary_weight
            else:
                weight_factor = mapping.secondary_mappings[dimension]
            
            # Create EvidenceScore with rubric-based score
            # Weight the rubric score by the mapping weight
            weighted_score = rubric_result.score * Decimal(str(float(weight_factor)))
            
            # Adjust confidence based on source reliability
            adjusted_confidence = rubric_result.confidence * mapping.reliability
            
            evidence_scores.append(EvidenceScore(
                source=source,
                raw_score=rubric_result.score,  # Keep original rubric score
                confidence=adjusted_confidence,
                evidence_count=len(chunks),
                metadata={
                    'ticker': ticker,
                    'section': section,
                    'dimension': dimension.value,
                    'rubric_level': rubric_result.level.label,
                    'matched_keywords': rubric_result.matched_keywords[:5],
                    'weight_factor': float(weight_factor)
                }
            ))
    
    logger.info(f"Loaded and scored {len(evidence_scores)} evidence items for {ticker} using rubrics")
    return evidence_scores


# Aggregates signals by category and converts to EvidenceScore objects
def load_external_signals_from_snowflake(
    ticker: str,
    snowflake_service
) -> List[EvidenceScore]:
    query = """
        SELECT 
            es.category,
            AVG(es.normalized_score) as avg_score,
            AVG(es.confidence) as avg_confidence,
            COUNT(*) as signal_count
        FROM external_signals es
        JOIN companies c ON es.company_id = c.id
        WHERE c.ticker = %(ticker)s
        GROUP BY es.category
    """
    
    try:
        results = snowflake_service.execute_query(query, {'ticker': ticker.upper()})
    except Exception as e:
        logger.warning(f"Could not load external signals for {ticker}: {e}")
        return []
    
    evidence_scores = []
    
    for row in results:
        category = row['category']
        avg_score = row['avg_score']
        avg_conf = row['avg_confidence']
        count = row['signal_count']
        
        # Map category to SignalSource
        try:
            source = SignalSource(category)
        except ValueError:
            logger.warning(f"Unknown signal category: {category}")
            continue
        
        # Use the pre-computed normalized score
        raw_score = Decimal(str(avg_score)) if avg_score else Decimal("50")
        confidence = Decimal(str(avg_conf)) if avg_conf else Decimal("0.5")
        
        # Boost confidence if we have many signals
        if count >= 10:
            confidence *= Decimal("1.1")
        confidence = min(Decimal("1.0"), confidence)
        
        evidence_scores.append(EvidenceScore(
            source=source,
            raw_score=raw_score,
            confidence=confidence,
            evidence_count=count,
            metadata={
                'ticker': ticker,
                'category': category
            }
        ))
    
    logger.info(f"Loaded {len(evidence_scores)} external signal sources for {ticker}")
    return evidence_scores


def load_culture_evidence_from_snowflake(
    ticker: str,
    snowflake_service
) -> List[EvidenceScore]:
    # Adjust table/column names based on your culture collector schema
    query = """
        SELECT 
            AVG(overall_rating) as avg_rating,
            AVG(culture_rating) as avg_culture,
            COUNT(*) as review_count
        FROM glassdoor_reviews
        WHERE ticker = %(ticker)s
    """
    
    try:
        results = snowflake_service.execute_query(query, {'ticker': ticker.upper()})
        
        if not results or not results[0]['REVIEW_COUNT']:
            logger.info(f"No culture data found for {ticker}")
            return []
        
        row = results[0]
        avg_rating = row['avg_rating']
        avg_culture = row['avg_culture']
        count = row['review_count']
        
        # Use culture rating if available, otherwise overall rating
        rating = avg_culture if avg_culture else avg_rating
        
        if not rating:
            return []
        
        # Convert 1-5 rating to 0-100 score
        raw_score = (Decimal(str(rating)) - Decimal("1")) / Decimal("4") * Decimal("100")
        
        # Confidence based on number of reviews
        confidence = min(Decimal("0.90"), Decimal(str(count)) / Decimal("100"))
        confidence = max(Decimal("0.3"), confidence)
        
        evidence_scores = [EvidenceScore(
            source=SignalSource.GLASSDOOR_REVIEWS,
            raw_score=raw_score,
            confidence=confidence,
            evidence_count=count,
            metadata={
                'ticker': ticker,
                'avg_rating': float(rating),
                'review_count': count
            }
        )]
        
        logger.info(f"Loaded culture evidence for {ticker}")
        return evidence_scores
        
    except Exception as e:
        logger.warning(f"Could not load culture signals for {ticker}: {e}")
        return []


def load_board_evidence_from_snowflake(
    ticker: str,
    snowflake_service
) -> List[EvidenceScore]:
    """Load board governance signals from Snowflake as EvidenceScore."""
    query = """
        SELECT
            governance_score,
            confidence
        FROM board_governance_signals
        WHERE ticker = %(ticker)s
        ORDER BY created_at DESC
        LIMIT 1
    """

    try:
        results = snowflake_service.execute_query(query, {'ticker': ticker.upper()})

        if not results:
            logger.info(f"No board governance data found for {ticker}")
            return []

        row = results[0]
        governance_score = row.get('governance_score') or row.get('GOVERNANCE_SCORE')
        confidence = row.get('confidence') or row.get('CONFIDENCE')

        if governance_score is None:
            return []

        evidence_scores = [EvidenceScore(
            source=SignalSource.BOARD_COMPOSITION,
            raw_score=Decimal(str(governance_score)),
            confidence=Decimal(str(confidence)),
            evidence_count=1,
            metadata={
                'ticker': ticker,
                'governance_score': float(governance_score),
            }
        )]

        logger.info(f"Loaded board governance evidence for {ticker}")
        return evidence_scores

    except Exception as e:
        logger.warning(f"Could not load board governance signals for {ticker}: {e}")
        return []


def load_all_evidence_from_snowflake(
    ticker: str,
    snowflake_service
) -> List[EvidenceScore]:
    logger.info(f"Loading all evidence for {ticker}")

    evidence_scores = []

    # Load SEC evidence
    sec_evidence = load_sec_evidence_from_snowflake_with_rubrics(ticker, snowflake_service)
    evidence_scores.extend(sec_evidence)
    logger.info(f"  ✓ {len(sec_evidence)} SEC sources")

    # Load external signals
    external_evidence = load_external_signals_from_snowflake(ticker, snowflake_service)
    evidence_scores.extend(external_evidence)
    logger.info(f"  ✓ {len(external_evidence)} external signal sources")

    # Load culture signals
    culture_evidence = load_culture_evidence_from_snowflake(ticker, snowflake_service)
    evidence_scores.extend(culture_evidence)
    logger.info(f"  ✓ {len(culture_evidence)} culture sources")

    # Load board governance signals
    board_evidence = load_board_evidence_from_snowflake(ticker, snowflake_service)
    evidence_scores.extend(board_evidence)
    logger.info(f"  ✓ {len(board_evidence)} board governance sources")

    logger.info(f"Total evidence sources for {ticker}: {len(evidence_scores)}")

    return evidence_scores


# Convenience function
def map_evidence(evidence_scores: List[EvidenceScore]) -> Dict[Dimension, DimensionScore]:
    """Convenience function to map evidence without creating mapper instance."""
    mapper = EvidenceMapper()
    return mapper.map_evidence_to_dimensions(evidence_scores)