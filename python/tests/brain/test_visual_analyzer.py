"""Tests for the Visual Property Analyzer."""

from brain.visual.analyzer import VisualPropertyAnalyzer, PhotoAnalysis


class TestVisualPropertyAnalyzer:
    def setup_method(self):
        self.analyzer = VisualPropertyAnalyzer()

    def test_no_photos_returns_unknown(self):
        report = self.analyzer.analyze_property("prop-1", [])
        assert report.overall_condition == 0.5
        assert "no_photos_provided" in report.uncertainty_flags
        assert report.photos_analyzed == 0

    def test_clean_photos_high_condition(self):
        photos = [
            PhotoAnalysis(
                photo_url="http://example.com/kitchen.jpg",
                room_type="kitchen",
                detected_features=["granite_countertops", "stainless_appliances"],
                detected_issues=[],
                quality_score=0.9,
                confidence=0.85,
            ),
            PhotoAnalysis(
                photo_url="http://example.com/living.jpg",
                room_type="living_room",
                detected_features=["hardwood_floors"],
                detected_issues=[],
                quality_score=0.85,
                confidence=0.9,
            ),
        ]
        report = self.analyzer.analyze_property("prop-2", photos)
        assert report.overall_condition > 0.8
        assert report.photos_analyzed == 2
        assert len(report.flagged_repairs) == 0

    def test_issues_reduce_condition(self):
        photos = [
            PhotoAnalysis(
                photo_url="http://example.com/exterior.jpg",
                room_type="exterior",
                detected_features=[],
                detected_issues=["foundation_cracks", "roof_damage"],
                quality_score=0.3,
                confidence=0.8,
            ),
        ]
        report = self.analyzer.analyze_property("prop-3", photos)
        assert report.overall_condition < 0.8
        assert len(report.flagged_repairs) == 2
        categories = [r["category"] for r in report.flagged_repairs]
        assert "structural" in categories
        assert "roof" in categories

    def test_missing_rooms_flagged(self):
        photos = [
            PhotoAnalysis(
                photo_url="http://example.com/kitchen.jpg",
                room_type="kitchen",
                detected_features=[],
                detected_issues=[],
                quality_score=0.7,
                confidence=0.8,
            ),
        ]
        report = self.analyzer.analyze_property("prop-4", photos)
        missing_flag = [f for f in report.uncertainty_flags if "missing_photos" in f]
        assert len(missing_flag) > 0

    def test_low_confidence_photos_flagged(self):
        photos = [
            PhotoAnalysis(
                photo_url="http://example.com/blurry.jpg",
                room_type="bathroom",
                detected_features=[],
                detected_issues=[],
                quality_score=0.5,
                confidence=0.2,  # Very low confidence
            ),
        ]
        report = self.analyzer.analyze_property("prop-5", photos)
        low_conf_flag = [f for f in report.uncertainty_flags if "low_confidence" in f]
        assert len(low_conf_flag) > 0

    def test_repair_cost_estimates_present(self):
        photos = [
            PhotoAnalysis(
                photo_url="http://example.com/roof.jpg",
                room_type="exterior",
                detected_features=[],
                detected_issues=["roof_damage"],
                quality_score=0.4,
                confidence=0.9,
            ),
        ]
        report = self.analyzer.analyze_property("prop-6", photos)
        assert len(report.flagged_repairs) == 1
        repair = report.flagged_repairs[0]
        assert repair["cost_low_cents"] > 0
        assert repair["cost_high_cents"] > repair["cost_low_cents"]

    def test_component_scores_per_room(self):
        photos = [
            PhotoAnalysis(photo_url="a.jpg", room_type="kitchen",
                         detected_features=[], detected_issues=[], quality_score=0.9, confidence=0.8),
            PhotoAnalysis(photo_url="b.jpg", room_type="bathroom",
                         detected_features=[], detected_issues=[], quality_score=0.6, confidence=0.8),
        ]
        report = self.analyzer.analyze_property("prop-7", photos)
        assert "kitchen" in report.component_scores
        assert "bathroom" in report.component_scores
        assert report.component_scores["kitchen"] > report.component_scores["bathroom"]
