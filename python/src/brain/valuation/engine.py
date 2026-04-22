"""
Valuation Engine - Predictive pricing with confidence bounds and provenance.
Combines comparable sales, condition scoring, and market trends.
Every valuation includes a provenance chain for audit/litigation defense.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging
import math

logger = logging.getLogger(__name__)


@dataclass
class Money:
    amount_cents: int
    currency: str = "USD"

    @property
    def dollars(self) -> float:
        return self.amount_cents / 100

    @classmethod
    def from_dollars(cls, amount: float) -> "Money":
        return cls(amount_cents=round(amount * 100))


@dataclass
class PropertyFeatures:
    bedrooms: int = 0
    bathrooms: float = 0.0
    sqft: int = 0
    lot_sqft: int = 0
    year_built: int = 0
    stories: int = 1
    garage_spaces: int = 0
    pool: bool = False
    has_hoa: bool = False


@dataclass
class ConditionScore:
    overall: float  # 0.0 - 1.0
    components: dict[str, float] = field(default_factory=dict)
    uncertainty_flags: list[str] = field(default_factory=list)
    visual_analysis_included: bool = False
    repairs: list["RepairEstimate"] = field(default_factory=list)


@dataclass
class RepairEstimate:
    category: str
    description: str
    cost_low: Money
    cost_high: Money
    urgency: float  # 0.0 - 1.0


@dataclass
class DataProvenance:
    source_system: str
    source_id: str
    retrieved_at: datetime
    source_updated_at: Optional[datetime] = None
    license_id: Optional[str] = None
    freshness_ttl_seconds: int = 3600


@dataclass
class ComparableProperty:
    property_id: str
    address: str
    sold_price: Money
    sold_date: datetime
    sqft: int
    bedrooms: int
    bathrooms: float
    distance_miles: float
    similarity_score: float
    provenance: DataProvenance


@dataclass
class Valuation:
    property_id: str
    estimated_value: Money
    confidence_low: Money
    confidence_high: Money
    confidence_score: float  # 0.0 - 1.0
    condition_score: Optional[ConditionScore]
    comparables: list[ComparableProperty]
    sources: list[DataProvenance]
    valid_until: datetime
    product_path: Optional[str] = None


class ValuationEngine:
    """
    Produces valuations with confidence intervals and full provenance chains.

    Design notes aligned with Hearth:
    - Hearth collects 150+ data points per property via purpose-built software
    - Their pricing pipeline: algorithmic valuation + confidence -> assessment -> review
    - This engine mirrors that: comparables + condition scoring -> confidence bounds
    - Every output is tied to data sources for litigation defense
    """

    def __init__(self, data_rights_manager):
        self._data_rights = data_rights_manager

    def valuate(
        self,
        property_id: str,
        features: PropertyFeatures,
        comparables: list[ComparableProperty],
        condition: Optional[ConditionScore] = None,
        product_path: Optional[str] = None,
    ) -> Valuation:
        """
        Produce a valuation with confidence intervals and provenance chain.
        """
        if not comparables:
            raise ValueError("At least one comparable property is required for valuation")

        # Calculate base value from comparables (weighted by similarity)
        base_value = self._weighted_comparable_value(comparables, features)

        # Adjust for condition if available
        condition_adjustment = 0
        if condition:
            condition_adjustment = self._condition_adjustment(base_value, condition)

        estimated_cents = base_value + condition_adjustment

        # Calculate confidence interval
        confidence_score = self._calculate_confidence(comparables, condition)
        spread = self._confidence_spread(estimated_cents, confidence_score, len(comparables))

        # Collect all provenance
        sources = [c.provenance for c in comparables]

        # Valuation TTL: higher confidence = longer validity
        ttl_hours = max(1, int(confidence_score * 24))
        valid_until = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

        valuation = Valuation(
            property_id=property_id,
            estimated_value=Money(amount_cents=estimated_cents),
            confidence_low=Money(amount_cents=estimated_cents - spread),
            confidence_high=Money(amount_cents=estimated_cents + spread),
            confidence_score=confidence_score,
            condition_score=condition,
            comparables=comparables,
            sources=sources,
            valid_until=valid_until,
            product_path=product_path,
        )

        logger.info(
            f"Valuation for {property_id}: ${valuation.estimated_value.dollars:,.0f} "
            f"(confidence: {confidence_score:.2f}, range: "
            f"${valuation.confidence_low.dollars:,.0f}-${valuation.confidence_high.dollars:,.0f})"
        )

        return valuation

    def _weighted_comparable_value(
        self, comparables: list[ComparableProperty], features: PropertyFeatures
    ) -> int:
        """Price per sqft from comparables, weighted by similarity, applied to subject."""
        total_weight = 0.0
        weighted_ppsf = 0.0

        for comp in comparables:
            if comp.sqft <= 0:
                continue
            ppsf = comp.sold_price.amount_cents / comp.sqft
            weight = comp.similarity_score
            weighted_ppsf += ppsf * weight
            total_weight += weight

        if total_weight == 0 or features.sqft <= 0:
            # Fallback: median sold price
            prices = sorted(c.sold_price.amount_cents for c in comparables)
            return prices[len(prices) // 2]

        avg_ppsf = weighted_ppsf / total_weight
        return int(avg_ppsf * features.sqft)

    def _condition_adjustment(self, base_value: int, condition: ConditionScore) -> int:
        """Adjust value based on condition. Poor condition = negative adjustment."""
        # Scale: 1.0 = perfect, 0.5 = average, 0.0 = needs major work
        # Adjustment range: -15% to +5% of base value
        if condition.overall >= 0.8:
            factor = 0.05 * ((condition.overall - 0.8) / 0.2)
        elif condition.overall >= 0.5:
            factor = 0.0
        else:
            factor = -0.15 * ((0.5 - condition.overall) / 0.5)

        # Subtract estimated repair costs
        repair_cost = sum(
            (r.cost_low.amount_cents + r.cost_high.amount_cents) // 2
            for r in condition.repairs
        )

        return int(base_value * factor) - repair_cost

    def _calculate_confidence(
        self, comparables: list[ComparableProperty], condition: Optional[ConditionScore]
    ) -> float:
        """
        Confidence score based on:
        - Number of comparables (more = higher)
        - Similarity scores of comparables
        - Recency of sales
        - Whether visual analysis was performed
        """
        # Base confidence from comparable count (diminishing returns)
        count_score = min(1.0, math.log(len(comparables) + 1) / math.log(10))

        # Average similarity
        avg_similarity = sum(c.similarity_score for c in comparables) / len(comparables)

        # Recency penalty: older comps reduce confidence
        now = datetime.now(timezone.utc)
        recency_scores = []
        for comp in comparables:
            days_old = (now - comp.sold_date).days
            recency_scores.append(max(0.0, 1.0 - (days_old / 365)))
        avg_recency = sum(recency_scores) / len(recency_scores) if recency_scores else 0.5

        # Visual analysis bonus
        visual_bonus = 0.1 if (condition and condition.visual_analysis_included) else 0.0

        confidence = (
            count_score * 0.3 +
            avg_similarity * 0.3 +
            avg_recency * 0.3 +
            visual_bonus
        )

        return min(1.0, max(0.0, confidence))

    def _confidence_spread(self, estimated_cents: int, confidence: float, comp_count: int) -> int:
        """
        Calculate the +/- spread of the confidence interval.
        Lower confidence = wider spread.
        """
        # Base spread: 10% at 0 confidence, 2% at perfect confidence
        base_pct = 0.10 - (0.08 * confidence)
        return int(estimated_cents * base_pct)
