"""Tests for the Brain Agent."""

from agents.brain_agent import BrainAgent


class TestBrainAgent:
    def setup_method(self):
        self.agent = BrainAgent()

    def test_valuation_request(self):
        response = self.agent.think(
            "What is this property worth?",
            {"property_id": "prop-123", "features": {"sqft": 2000, "bedrooms": 3, "bathrooms": 2.0}},
        )
        assert response.confidence > 0
        assert len(response.tool_calls_made) > 0
        assert len(response.claims) > 0

    def test_data_rights_checked_first(self):
        response = self.agent.think("Get me the property value", {"property_id": "prop-456"})
        assert any(tc.get("tool") == "check_data_rights" for tc in response.tool_calls_made)

    def test_no_property_id_still_responds(self):
        response = self.agent.think("What properties are available?", {})
        assert response.content

    def test_tools_registered(self):
        assert "check_data_rights" in self.agent.tools
        assert "get_valuation" in self.agent.tools
        assert "analyze_property_photos" in self.agent.tools
        assert "get_comparables" in self.agent.tools
