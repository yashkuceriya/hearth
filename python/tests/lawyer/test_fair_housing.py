"""Tests for the Fair Housing Compliance Checker."""

from lawyer.fair_housing.checker import FairHousingChecker


class TestFairHousingChecker:
    def setup_method(self):
        self.checker = FairHousingChecker()

    # === COMPLIANT MESSAGES ===
    def test_compliant_property_description(self):
        result = self.checker.check(
            "This 3-bedroom home features hardwood floors, a renovated kitchen, "
            "and a large backyard. Located near top-rated schools with a walk score of 85."
        )
        assert result.compliant is True
        assert len(result.violations) == 0

    def test_compliant_neighborhood_with_objective_data(self):
        result = self.checker.check(
            "The property is in 78704, which has a median home value of $550k "
            "and is 2 miles from downtown Austin. The school district rating is 8/10."
        )
        assert result.compliant is True

    # === RACIAL STEERING ===
    def test_racial_neighborhood_description(self):
        result = self.checker.check("This is in a predominantly white neighborhood")
        assert result.compliant is False
        assert any(v.rule_id == "FH-RACE-001" for v in result.violations)

    def test_ethnic_community_reference(self):
        result = self.checker.check("Located in the hispanic area of town")
        assert result.compliant is False

    # === FAMILIAL STATUS ===
    def test_no_children_policy(self):
        result = self.checker.check("This property is adults only, no children allowed")
        assert result.compliant is False
        assert any(v.violation_type == "familial_status_discrimination" for v in result.violations)

    def test_unsuitable_for_families(self):
        result = self.checker.check("This unit is not suitable for children")
        assert result.compliant is False

    # === DISABILITY ===
    def test_no_disabled_persons(self):
        result = self.checker.check("No wheelchair users in this building")
        assert result.compliant is False
        assert any(v.rule_id == "FH-DIS-001" for v in result.violations)

    def test_no_service_animals(self):
        result = self.checker.check("No service animals allowed in this property")
        assert result.compliant is False

    # === RELIGION ===
    def test_religious_community(self):
        result = self.checker.check("Located in a Christian neighborhood")
        assert result.compliant is False
        assert any(v.rule_id == "FH-REL-001" for v in result.violations)

    # === CODED LANGUAGE ===
    def test_coded_urban_language(self):
        result = self.checker.check("This is far from the inner-city area")
        assert result.compliant is False
        assert any(v.rule_id == "FH-CODE-001" for v in result.violations)

    def test_exclusive_neighborhood(self):
        result = self.checker.check("Located in an exclusive neighborhood")
        assert result.compliant is False

    # === SUBJECTIVE NEIGHBORHOOD ===
    def test_bad_neighborhood(self):
        result = self.checker.check("Avoid the bad neighborhood to the east")
        assert result.compliant is False
        assert any(v.rule_id == "FH-STEER-001" for v in result.violations)

    def test_safe_neighborhood(self):
        result = self.checker.check("This is in a safe neighborhood")
        assert result.compliant is False

    # === SANITIZED TEXT ===
    def test_sanitized_output(self):
        result = self.checker.check("Great home in a white neighborhood with 3 beds")
        assert result.compliant is False
        assert result.sanitized_text is not None
        assert "white neighborhood" not in result.sanitized_text.lower()

    # === RULE EXPLANATIONS ===
    def test_rule_explanation_exists(self):
        explanation = self.checker.get_rule_explanation("FH-RACE-001")
        assert explanation is not None
        assert "FHA" in explanation or "3604" in explanation

    def test_unknown_rule_returns_none(self):
        explanation = self.checker.get_rule_explanation("NONEXISTENT-001")
        assert explanation is None

    # === EDGE CASES ===
    def test_empty_string(self):
        result = self.checker.check("")
        assert result.compliant is True

    def test_rules_checked_count(self):
        result = self.checker.check("Hello")
        assert result.rules_checked > 0
