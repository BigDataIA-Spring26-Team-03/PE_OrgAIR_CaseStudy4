# src/scoring/evidence_mapper.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Dimension(str, Enum):
    """The 7 dimensions of AI readiness."""
    DATA_INFRASTRUCTURE = "data_infrastructure"
    AI_GOVERNANCE = "ai_governance"
    TECHNOLOGY_STACK = "technology_stack"
    TALENT = "talent"
    LEADERSHIP = "leadership"
    USE_CASE_PORTFOLIO = "use_case_portfolio"
    CULTURE = "culture"


class SignalSource(str, Enum):
    """Evidence sources from CS2 and CS3."""
    # CS2 External Signals
    TECHNOLOGY_HIRING = "technology_hiring"
    INNOVATION_ACTIVITY = "innovation_activity"
    DIGITAL_PRESENCE = "digital_presence"
    LEADERSHIP_SIGNALS = "leadership_signals"
    
    # CS2 SEC Sections
    SEC_ITEM_1 = "sec_item_1"        # Business description
    SEC_ITEM_1A = "sec_item_1a"      # Risk factors
    SEC_ITEM_7 = "sec_item_7"        # MD&A
    
    # CS3 New Sources
    GLASSDOOR_REVIEWS = "glassdoor_reviews"
    BOARD_COMPOSITION = "board_composition"


@dataclass
class DimensionMapping:
    """Maps a signal source to dimensions with weights."""
    source: SignalSource
    primary_dimension: Dimension
    primary_weight: Decimal
    secondary_mappings: Dict[Dimension, Decimal] = field(default_factory=dict)
    reliability: Decimal = Decimal("0.8")  # Source reliability score
    
    def __post_init__(self):
        """Validate that weights sum to 1.0."""
        total_weight = self.primary_weight + sum(self.secondary_mappings.values())
        if abs(total_weight - Decimal("1.0")) > Decimal("0.001"):
            raise ValueError(
                f"Weights for {self.source} must sum to 1.0, got {total_weight}"
            )


@dataclass
class EvidenceScore:
    """A score from a single evidence source."""
    source: SignalSource
    raw_score: Decimal  # 0-100
    confidence: Decimal  # 0-1
    evidence_count: int  # Number of data points
    metadata: Dict = field(default_factory=dict)


@dataclass
class DimensionScore:
    """Aggregated score for one dimension."""
    dimension: Dimension
    score: Decimal  # Final weighted score 0-100
    contributing_sources: List[SignalSource]
    total_weight: Decimal
    confidence: Decimal
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "dimension": self.dimension.value,
            "score": float(self.score),
            "contributing_sources": [s.value for s in self.contributing_sources],
            "total_weight": float(self.total_weight),
            "confidence": float(self.confidence)
        }


# ============================================================================
# THE CRITICAL MAPPING TABLE
# ============================================================================

SIGNAL_TO_DIMENSION_MAP: Dict[SignalSource, DimensionMapping] = {
    
    SignalSource.TECHNOLOGY_HIRING: DimensionMapping(
        source=SignalSource.TECHNOLOGY_HIRING,
        primary_dimension=Dimension.TALENT,
        primary_weight=Decimal("0.70"),
        secondary_mappings={
            Dimension.TECHNOLOGY_STACK: Decimal("0.20"),
            Dimension.DATA_INFRASTRUCTURE: Decimal("0.10"),
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


class EvidenceMapper:
    """
    Maps CS2 evidence to 7 V^R dimensions.
    
    Takes evidence from multiple sources and aggregates them into
    dimension scores using weighted mappings.
    """
    
    def __init__(self):
        """Initialize with mapping table."""
        self.mappings = SIGNAL_TO_DIMENSION_MAP
        logger.info(f"EvidenceMapper initialized with {len(self.mappings)} signal sources")
    
    def map_evidence_to_dimensions(
        self,
        evidence_scores: List[EvidenceScore]
    ) -> Dict[Dimension, DimensionScore]:
        """
        Map evidence from multiple sources to 7 dimensions.
        
        Algorithm:
        1. For each dimension, find all evidence sources that contribute to it
        2. Weight each source's contribution by its mapping weight
        3. Aggregate using weighted average
        4. Apply confidence adjustments
        
        Args:
            evidence_scores: List of scores from different sources
            
        Returns:
            Dictionary mapping each dimension to its aggregated score
        """
        if not evidence_scores:
            logger.warning("No evidence scores provided, returning defaults")
            return self._default_dimension_scores()
        
        # Initialize accumulators for each dimension
        dimension_accumulators: Dict[Dimension, Dict] = {
            dim: {
                "weighted_sum": Decimal("0"),
                "total_weight": Decimal("0"),
                "sources": [],
                "confidences": []
            }
            for dim in Dimension
        }
        
        # Process each evidence score
        for evidence in evidence_scores:
            if evidence.source not in self.mappings:
                logger.warning(f"No mapping found for source: {evidence.source}")
                continue
            
            mapping = self.mappings[evidence.source]
            
            # Adjust score by source reliability
            adjusted_score = evidence.raw_score * mapping.reliability
            
            # Contribute to primary dimension
            self._add_contribution(
                dimension_accumulators[mapping.primary_dimension],
                adjusted_score,
                mapping.primary_weight,
                evidence.source,
                evidence.confidence
            )
            
            # Contribute to secondary dimensions
            for dim, weight in mapping.secondary_mappings.items():
                self._add_contribution(
                    dimension_accumulators[dim],
                    adjusted_score,
                    weight,
                    evidence.source,
                    evidence.confidence
                )
        
        # Calculate final dimension scores
        dimension_scores = {}
        for dim, acc in dimension_accumulators.items():
            dimension_scores[dim] = self._finalize_dimension_score(dim, acc)
        
        logger.info(f"Mapped evidence to {len(dimension_scores)} dimensions")
        return dimension_scores
    
    def _add_contribution(
        self,
        accumulator: Dict,
        score: Decimal,
        weight: Decimal,
        source: SignalSource,
        confidence: Decimal
    ):
        """Add a contribution to a dimension accumulator."""
        contribution = score * weight
        accumulator["weighted_sum"] += contribution
        accumulator["total_weight"] += weight
        accumulator["sources"].append(source)
        accumulator["confidences"].append(confidence)
    
    def _finalize_dimension_score(
        self,
        dimension: Dimension,
        accumulator: Dict
    ) -> DimensionScore:
        """Convert accumulator to final DimensionScore."""
        total_weight = accumulator["total_weight"]
        
        if total_weight == 0:
            # No evidence for this dimension - use default
            logger.warning(f"No evidence for dimension: {dimension.value}")
            score = Decimal("50")  # Neutral score
            confidence = Decimal("0.1")  # Very low confidence
        else:
            # Weighted average
            score = accumulator["weighted_sum"] / total_weight
            
            # Clamp to 0-100
            score = max(Decimal("0"), min(Decimal("100"), score))
            
            # Average confidence across sources
            confidence = sum(accumulator["confidences"]) / len(accumulator["confidences"])
            
            # Adjust confidence based on number of sources
            source_count = len(set(accumulator["sources"]))
            if source_count == 1:
                confidence *= Decimal("0.7")  # Penalize single source
            elif source_count >= 3:
                confidence *= Decimal("1.1")  # Boost multiple sources
                confidence = min(confidence, Decimal("1.0"))
        
        return DimensionScore(
            dimension=dimension,
            score=score,
            contributing_sources=list(set(accumulator["sources"])),
            total_weight=total_weight,
            confidence=confidence
        )
    
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
    
    def get_coverage_report(
        self,
        evidence_scores: List[EvidenceScore]
    ) -> Dict:
        """
        Generate a coverage report showing which dimensions have evidence.
        
        Useful for identifying gaps in data collection.
        """
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
                "confidence": float(score.confidence)
            }
        
        report["coverage_percentage"] = (
            report["dimensions_with_evidence"] / report["total_dimensions"] * 100
        )
        
        return report


# Convenience function
def map_evidence(evidence_scores: List[EvidenceScore]) -> Dict[Dimension, DimensionScore]:
    """Convenience function to map evidence."""
    mapper = EvidenceMapper()
    return mapper.map_evidence_to_dimensions(evidence_scores)