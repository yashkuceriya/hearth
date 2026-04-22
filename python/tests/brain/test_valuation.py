"""Tests for the Valuation Engine."""

from datetime import datetime, timezone, timedelta
from brain.valuation.engine import (
    ValuationEngine, PropertyFeatures, ComparableProperty,
    ConditionScore, RepairEstimate, Money, DataProvenance,
)
from brain.ingestion.data_rights import DataRightsManager


class TestValuationEngine:
    def setup_method(self):
        self.drm = DataRightsManager()
        self.engine = ValuationEngine(self.drm)

    def _make_comparable(self, price_cents: int, sqft: int, similarity: float = 0.8) -> ComparableProperty:
        return ComparableProperty(
            property_id="comp-1",
            address="123 Test St",
            sold_price=Money(amount_cents=price_cents),
            sold_date=datetime.now(timezone.utc) - timedelta(days=30),
            sqft=sqft,
            bedrooms=3,
            bathrooms=2.0,
            distance_miles=0.5,
            similarity_score=similarity,
            provenance=DataProvenance(
                source_system="MLS",
                source_id="comp-1",
                retrieved_at=datetime.now(timezone.utc),
            ),
        )

    def test_basic_valuation(self):
        comps = [
            self._make_comparable(45000000, 2000),  # $450k, 2000sqft = $225/sqft
            self._make_comparable(50000000, 2200),  # $500k, 2200sqft = $227/sqft
        ]
        features = PropertyFeatures(sqft=2100, bedrooms=3, bathrooms=2.0)

        valuation = self.engine.valuate("prop-1", features, comps)

        assert valuation.estimated_value.amount_cents > 0
        assert valuation.confidence_low.amount_cents < valuation.estimated_value.amount_cents
        assert valuation.confidence_high.amount_cents > valuation.estimated_value.amount_cents
        assert 0 < valuation.confidence_score <= 1.0
        assert valuation.valid_until > datetime.now(timezone.utc)

    def test_valuation_requires_comparables(self):
        features = PropertyFeatures(sqft=2000)
        try:
            self.engine.valuate("prop-1", features, [])
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_condition_reduces_value(self):
        comps = [self._make_comparable(50000000, 2000)]
        features = PropertyFeatures(sqft=2000)

        # Good condition
        good = self.engine.valuate("prop-1", features, comps)

        # Poor condition with repairs
        poor_condition = ConditionScore(
            overall=0.3,
            components={"roof": 0.2, "foundation": 0.3},
            repairs=[RepairEstimate(
                category="roof",
                description="Needs replacement",
                cost_low=Money(amount_cents=800000),
                cost_high=Money(amount_cents=2500000),
                urgency=0.8,
            )],
        )
        poor = self.engine.valuate("prop-1", features, comps, condition=poor_condition)

        assert poor.estimated_value.amount_cents < good.estimated_value.amount_cents

    def test_confidence_increases_with_more_comps(self):
        features = PropertyFeatures(sqft=2000)
        few_comps = [self._make_comparable(50000000, 2000)]
        many_comps = [self._make_comparable(50000000 + i * 100000, 2000) for i in range(8)]

        val_few = self.engine.valuate("prop-1", features, few_comps)
        val_many = self.engine.valuate("prop-1", features, many_comps)

        assert val_many.confidence_score > val_few.confidence_score

    def test_provenance_chain(self):
        comps = [self._make_comparable(50000000, 2000)]
        features = PropertyFeatures(sqft=2000)
        valuation = self.engine.valuate("prop-1", features, comps)

        assert len(valuation.sources) == 1
        assert valuation.sources[0].source_system == "MLS"
