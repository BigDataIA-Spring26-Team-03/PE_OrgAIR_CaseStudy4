# tests/test_evidence_mapper.py

import pytest
from decimal import Decimal
from src.scoring.evidence_mapper import (
    EvidenceMapper,
    EvidenceScore,
    SignalSource,
    Dimension,
    map_evidence
)


def test_evidence_mapper_initialization():
    """Test mapper initializes correctly."""
    mapper = EvidenceMapper()
    assert len(mapper.mappings) == 9  # 9 signal sources


def test_single_evidence_source():
    """Test mapping a single evidence source."""
    mapper = EvidenceMapper()
    
    evidence = [
        EvidenceScore(
            source=SignalSource.TECHNOLOGY_HIRING,
            raw_score=Decimal("80"),
            confidence=Decimal("0.9"),
            evidence_count=10
        )
    ]
    
    dimensions = mapper.map_evidence_to_dimensions(evidence)
    
    # Should return all 7 dimensions
    assert len(dimensions) == 7
    
    # Talent should have highest score (primary 70%)
    talent_score = dimensions[Dimension.TALENT]
    assert talent_score.score > 0
    assert SignalSource.TECHNOLOGY_HIRING in talent_score.contributing_sources
    
    # Tech stack should have lower score (secondary 20%)
    tech_score = dimensions[Dimension.TECHNOLOGY_STACK]
    assert tech_score.score > 0
    assert tech_score.score == talent_score.score
    assert talent_score.total_weight > tech_score.total_weight


def test_multiple_evidence_sources():
    """Test mapping multiple evidence sources."""
    evidence = [
        EvidenceScore(
            source=SignalSource.TECHNOLOGY_HIRING,
            raw_score=Decimal("80"),
            confidence=Decimal("0.9"),
            evidence_count=10
        ),
        EvidenceScore(
            source=SignalSource.INNOVATION_ACTIVITY,
            raw_score=Decimal("70"),
            confidence=Decimal("0.8"),
            evidence_count=5
        ),
        EvidenceScore(
            source=SignalSource.GLASSDOOR_REVIEWS,
            raw_score=Decimal("75"),
            confidence=Decimal("0.7"),
            evidence_count=15
        )
    ]
    
    dimensions = map_evidence(evidence)
    
    # All dimensions should have scores
    assert len(dimensions) == 7
    
    # Culture should have evidence from Glassdoor
    culture = dimensions[Dimension.CULTURE]
    assert culture.score > 0
    assert SignalSource.GLASSDOOR_REVIEWS in culture.contributing_sources


def test_no_evidence():
    """Test behavior with no evidence."""
    mapper = EvidenceMapper()
    dimensions = mapper.map_evidence_to_dimensions([])
    
    # Should return default scores
    assert len(dimensions) == 7
    
    for dim, score in dimensions.items():
        assert score.score == Decimal("50")  # Default neutral score
        assert score.confidence == Decimal("0.1")  # Low confidence


def test_dimension_with_no_contributing_sources():
    """Test dimension that receives no evidence."""
    evidence = [
        EvidenceScore(
            source=SignalSource.TECHNOLOGY_HIRING,
            raw_score=Decimal("80"),
            confidence=Decimal("0.9"),
            evidence_count=10
        )
    ]
    
    mapper = EvidenceMapper()
    dimensions = mapper.map_evidence_to_dimensions(evidence)
    
    # Use Case Portfolio should have no direct evidence
    use_case = dimensions[Dimension.USE_CASE_PORTFOLIO]
    assert use_case.score == Decimal("50")  # Default
    assert len(use_case.contributing_sources) == 0


def test_coverage_report():
    """Test coverage report generation."""
    evidence = [
        EvidenceScore(
            source=SignalSource.TECHNOLOGY_HIRING,
            raw_score=Decimal("80"),
            confidence=Decimal("0.9"),
            evidence_count=10
        ),
        EvidenceScore(
            source=SignalSource.GLASSDOOR_REVIEWS,
            raw_score=Decimal("75"),
            confidence=Decimal("0.7"),
            evidence_count=15
        )
    ]
    
    mapper = EvidenceMapper()
    report = mapper.get_coverage_report(evidence)
    
    assert "total_dimensions" in report
    assert report["total_dimensions"] == 7
    assert "dimensions_with_evidence" in report
    assert "coverage_percentage" in report
    assert 0 <= report["coverage_percentage"] <= 100


def test_confidence_adjustment_single_source():
    """Test confidence is penalized for single source."""
    evidence = [
        EvidenceScore(
            source=SignalSource.TECHNOLOGY_HIRING,
            raw_score=Decimal("80"),
            confidence=Decimal("1.0"),  # Perfect confidence
            evidence_count=10
        )
    ]
    
    mapper = EvidenceMapper()
    dimensions = mapper.map_evidence_to_dimensions(evidence)
    
    talent = dimensions[Dimension.TALENT]
    # Confidence should be reduced (0.7x penalty for single source)
    assert talent.confidence < Decimal("1.0")


def test_scores_bounded():
    """Test all scores are bounded 0-100."""
    evidence = [
        EvidenceScore(
            source=SignalSource.TECHNOLOGY_HIRING,
            raw_score=Decimal("120"),  # Invalid high score
            confidence=Decimal("0.9"),
            evidence_count=10
        )
    ]
    
    mapper = EvidenceMapper()
    dimensions = mapper.map_evidence_to_dimensions(evidence)
    
    for dim, score in dimensions.items():
        assert Decimal("0") <= score.score <= Decimal("100")


def test_convenience_function():
    """Test the convenience function."""
    evidence = [
        EvidenceScore(
            source=SignalSource.TECHNOLOGY_HIRING,
            raw_score=Decimal("80"),
            confidence=Decimal("0.9"),
            evidence_count=10
        )
    ]
    
    dimensions = map_evidence(evidence)
    assert len(dimensions) == 7
    assert Dimension.TALENT in dimensions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])