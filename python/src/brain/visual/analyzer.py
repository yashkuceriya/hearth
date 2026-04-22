"""
Visual Property Analyzer - Multimodal analysis of property photos.
Aligns with Hearth's Repair Co-Pilot: crawls imagery to highlight repair details.
Produces ConditionCertaintyScores that feed into valuation and product-path routing.
"""

from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class PhotoAnalysis:
    photo_url: str
    room_type: str
    detected_features: list[str]
    detected_issues: list[str]
    quality_score: float  # 0.0-1.0
    confidence: float


@dataclass
class VisualConditionReport:
    property_id: str
    photos_analyzed: int
    room_analyses: list[PhotoAnalysis]
    overall_condition: float  # 0.0-1.0
    component_scores: dict[str, float]
    flagged_repairs: list[dict]
    uncertainty_flags: list[str]


class VisualPropertyAnalyzer:
    """
    Analyzes property photos to:
    1. Identify high-value features (granite counters, hardwood floors, etc.)
    2. Detect potential issues (foundation cracks, water stains, roof damage)
    3. Produce a Condition Certainty Score per property
    4. Estimate repair scope and costs

    This is an underwriting control loop, NOT a novelty feature.
    The ConditionCertaintyScore directly drives:
    - Spread/guardrails on offers
    - Product-path eligibility
    - Post-acquisition repair budget variance
    """

    # Known feature indicators
    HIGH_VALUE_FEATURES = {
        "granite_countertops", "marble_countertops", "quartz_countertops",
        "hardwood_floors", "crown_molding", "stainless_appliances",
        "updated_kitchen", "updated_bathrooms", "pool", "outdoor_kitchen",
        "smart_home", "solar_panels", "new_roof", "new_hvac",
    }

    RED_FLAG_INDICATORS = {
        "foundation_cracks": {"severity": 0.9, "category": "structural"},
        "water_stains": {"severity": 0.6, "category": "water_damage"},
        "roof_damage": {"severity": 0.8, "category": "roof"},
        "mold_visible": {"severity": 0.7, "category": "health_safety"},
        "outdated_electrical": {"severity": 0.5, "category": "electrical"},
        "hvac_age_concern": {"severity": 0.4, "category": "hvac"},
        "plumbing_issues": {"severity": 0.6, "category": "plumbing"},
        "pest_damage": {"severity": 0.5, "category": "pest"},
    }

    # Repair cost estimates for Austin market (in cents)
    REPAIR_COST_RANGES = {
        "structural": (1500000, 5000000),    # $15k-$50k
        "roof": (800000, 2500000),            # $8k-$25k
        "water_damage": (300000, 1500000),    # $3k-$15k
        "health_safety": (500000, 2000000),   # $5k-$20k
        "electrical": (200000, 800000),       # $2k-$8k
        "hvac": (400000, 1200000),            # $4k-$12k
        "plumbing": (200000, 600000),         # $2k-$6k
        "pest": (100000, 500000),             # $1k-$5k
    }

    def analyze_property(
        self,
        property_id: str,
        photo_analyses: list[PhotoAnalysis],
    ) -> VisualConditionReport:
        """
        Aggregate individual photo analyses into a property-level condition report.
        In production, photo_analyses would come from a multimodal LLM (Claude Vision).
        """
        if not photo_analyses:
            return VisualConditionReport(
                property_id=property_id,
                photos_analyzed=0,
                room_analyses=[],
                overall_condition=0.5,  # Unknown = assume average
                component_scores={},
                flagged_repairs=[],
                uncertainty_flags=["no_photos_provided"],
            )

        # Aggregate issues across all photos
        all_issues: list[str] = []
        all_features: list[str] = []
        component_scores: dict[str, list[float]] = {}

        for analysis in photo_analyses:
            all_issues.extend(analysis.detected_issues)
            all_features.extend(analysis.detected_features)

            # Score per room type
            room = analysis.room_type
            if room not in component_scores:
                component_scores[room] = []
            component_scores[room].append(analysis.quality_score)

        # Calculate component averages
        avg_components = {
            room: sum(scores) / len(scores)
            for room, scores in component_scores.items()
        }

        # Identify repairs needed
        flagged_repairs = []
        for issue in set(all_issues):
            if issue in self.RED_FLAG_INDICATORS:
                indicator = self.RED_FLAG_INDICATORS[issue]
                category = indicator["category"]
                cost_range = self.REPAIR_COST_RANGES.get(category, (100000, 500000))
                flagged_repairs.append({
                    "issue": issue,
                    "category": category,
                    "severity": indicator["severity"],
                    "cost_low_cents": cost_range[0],
                    "cost_high_cents": cost_range[1],
                })

        # Overall condition: start at 1.0, reduce for each issue
        overall = 1.0
        for repair in flagged_repairs:
            overall -= repair["severity"] * 0.15
        overall = max(0.0, min(1.0, overall))

        # Uncertainty flags
        uncertainty = []
        expected_rooms = {"kitchen", "living_room", "master_bedroom", "bathroom", "exterior"}
        covered_rooms = {a.room_type for a in photo_analyses}
        missing = expected_rooms - covered_rooms
        if missing:
            uncertainty.append(f"missing_photos: {', '.join(missing)}")

        low_confidence = [a for a in photo_analyses if a.confidence < 0.5]
        if low_confidence:
            uncertainty.append(f"low_confidence_photos: {len(low_confidence)}")

        report = VisualConditionReport(
            property_id=property_id,
            photos_analyzed=len(photo_analyses),
            room_analyses=photo_analyses,
            overall_condition=overall,
            component_scores=avg_components,
            flagged_repairs=flagged_repairs,
            uncertainty_flags=uncertainty,
        )

        logger.info(
            f"Visual analysis for {property_id}: condition={overall:.2f}, "
            f"repairs={len(flagged_repairs)}, photos={len(photo_analyses)}"
        )

        return report
