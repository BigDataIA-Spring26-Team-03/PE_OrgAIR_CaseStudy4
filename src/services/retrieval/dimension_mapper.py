# src/services/retrieval/dimension_mapper.py
# Reuses the weight constants already validated in src/scoring/evidence_mapper.py;
# only the two CS2-only categories (CULTURE_SIGNALS, GOVERNANCE_SIGNALS) are new.

from __future__ import annotations

from typing import Dict, List, Tuple

from src.scoring.evidence_mapper import Dimension, SIGNAL_TO_DIMENSION_MAP, SignalSource
from src.services.integration.cs2_client import SignalCategory, SourceType

# ---------------------------------------------------------------------------
# SignalCategory → dimension weights
# Pull shared weights straight from CS3's map; add the two new CS2 categories.
# ---------------------------------------------------------------------------

# (primary_dimension, {dimension: weight})
_CATEGORY_WEIGHTS: Dict[SignalCategory, Tuple[Dimension, Dict[Dimension, float]]] = {
    SignalCategory.TECHNOLOGY_HIRING: (
        Dimension.TALENT,
        {
            Dimension.TALENT: float(SIGNAL_TO_DIMENSION_MAP[SignalSource.TECHNOLOGY_HIRING].primary_weight),
            Dimension.TECHNOLOGY_STACK: float(SIGNAL_TO_DIMENSION_MAP[SignalSource.TECHNOLOGY_HIRING].secondary_mappings[Dimension.TECHNOLOGY_STACK]),
            Dimension.CULTURE: 0.10,   # CS4 spec swaps DataInfra(0.10) → Culture(0.10)
        },
    ),
    SignalCategory.INNOVATION_ACTIVITY: (
        Dimension.TECHNOLOGY_STACK,
        {
            d: float(w)
            for d, w in {
                Dimension.TECHNOLOGY_STACK: SIGNAL_TO_DIMENSION_MAP[SignalSource.INNOVATION_ACTIVITY].primary_weight,
                **SIGNAL_TO_DIMENSION_MAP[SignalSource.INNOVATION_ACTIVITY].secondary_mappings,
            }.items()
        },
    ),
    SignalCategory.DIGITAL_PRESENCE: (
        Dimension.DATA_INFRASTRUCTURE,
        {
            d: float(w)
            for d, w in {
                Dimension.DATA_INFRASTRUCTURE: SIGNAL_TO_DIMENSION_MAP[SignalSource.DIGITAL_PRESENCE].primary_weight,
                **SIGNAL_TO_DIMENSION_MAP[SignalSource.DIGITAL_PRESENCE].secondary_mappings,
            }.items()
        },
    ),
    SignalCategory.LEADERSHIP_SIGNALS: (
        Dimension.LEADERSHIP,
        {
            d: float(w)
            for d, w in {
                Dimension.LEADERSHIP: SIGNAL_TO_DIMENSION_MAP[SignalSource.LEADERSHIP_SIGNALS].primary_weight,
                **SIGNAL_TO_DIMENSION_MAP[SignalSource.LEADERSHIP_SIGNALS].secondary_mappings,
            }.items()
        },
    ),
    # ── new in CS4 / CS2 ─────────────────────────────────────────────────────
    SignalCategory.CULTURE_SIGNALS: (
        Dimension.CULTURE,
        {
            Dimension.CULTURE: 0.80,
            Dimension.TALENT: 0.10,
            Dimension.LEADERSHIP: 0.10,
        },
    ),
    SignalCategory.GOVERNANCE_SIGNALS: (
        Dimension.AI_GOVERNANCE,
        {
            Dimension.AI_GOVERNANCE: 0.70,
            Dimension.LEADERSHIP: 0.30,
        },
    ),
}

# ---------------------------------------------------------------------------
# SourceType → SignalCategory  
# ---------------------------------------------------------------------------

_SOURCE_TO_CATEGORY: Dict[SourceType, SignalCategory] = {
    SourceType.SEC_10K_ITEM_1:        SignalCategory.DIGITAL_PRESENCE,
    SourceType.SEC_10K_ITEM_1A:       SignalCategory.GOVERNANCE_SIGNALS,
    SourceType.SEC_10K_ITEM_7:        SignalCategory.LEADERSHIP_SIGNALS,
    SourceType.JOB_POSTING_LINKEDIN:  SignalCategory.TECHNOLOGY_HIRING,
    SourceType.JOB_POSTING_INDEED:    SignalCategory.TECHNOLOGY_HIRING,
    SourceType.PATENT_USPTO:          SignalCategory.INNOVATION_ACTIVITY,
    SourceType.PRESS_RELEASE:         SignalCategory.INNOVATION_ACTIVITY,
    SourceType.GLASSDOOR_REVIEW:      SignalCategory.CULTURE_SIGNALS,
    SourceType.BOARD_PROXY_DEF14A:    SignalCategory.GOVERNANCE_SIGNALS,
    SourceType.ANALYST_INTERVIEW:     SignalCategory.LEADERSHIP_SIGNALS,
    SourceType.DD_DATA_ROOM:          SignalCategory.DIGITAL_PRESENCE,
}


# ---------------------------------------------------------------------------
# DimensionMapper
# ---------------------------------------------------------------------------

class DimensionMapper:
    """
    Maps CS2 SignalCategory (and SourceType) to CS3 Dimension weights.

    """

    def get_dimension_weights(self, category: SignalCategory) -> Dict[Dimension, float]:
        """Return {Dimension: weight} for the given SignalCategory."""
        entry = _CATEGORY_WEIGHTS.get(category)
        if entry is None:
            return {}
        _, weights = entry
        return dict(weights)

    def get_primary_dimension(self, category: SignalCategory) -> Dimension | None:
        """Return the primary (highest-weight) Dimension for the category."""
        entry = _CATEGORY_WEIGHTS.get(category)
        if entry is None:
            return None
        primary, _ = entry
        return primary

    def get_all_dimensions_for_evidence(
        self, category: SignalCategory
    ) -> List[Tuple[Dimension, float]]:
        """Return [(Dimension, weight)] sorted descending by weight."""
        weights = self.get_dimension_weights(category)
        return sorted(weights.items(), key=lambda x: x[1], reverse=True)

    def source_type_to_category(self, source_type: SourceType) -> SignalCategory | None:
        """Resolve a CS2 SourceType to its SignalCategory."""
        return _SOURCE_TO_CATEGORY.get(source_type)
