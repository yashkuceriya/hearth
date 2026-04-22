"""Tests for the Voice Agent."""

from agents.voice_agent import VoiceAgent


class TestVoiceAgent:
    def setup_method(self):
        self.agent = VoiceAgent()

    def test_high_intent_detection(self):
        response = self.agent.think(
            "I'm pre-approved and ready to buy",
            {"session_id": "s1", "lead_id": "lead-1"},
        )
        assert response.confidence > 0.5

    def test_low_intent_detection(self):
        response = self.agent.think(
            "Just browsing, not ready yet",
            {"session_id": "s2", "lead_id": "lead-2"},
        )
        assert response.confidence <= 0.7

    def test_market_question_delegates_to_brain(self):
        response = self.agent.think(
            "What's the property value at 123 Main St?",
            {"session_id": "s3", "lead_id": "lead-3", "property_id": "prop-1"},
        )
        brain_delegations = [d for d in response.delegations_made if d.to_role.value == "brain"]
        assert len(brain_delegations) > 0

    def test_offer_request_delegates_to_closer(self):
        response = self.agent.think(
            "I want to make an offer",
            {"session_id": "s4", "lead_id": "lead-4"},
        )
        closer_delegations = [d for d in response.delegations_made if d.to_role.value == "closer"]
        assert len(closer_delegations) > 0

    def test_tour_without_agreement(self):
        response = self.agent.think(
            "Can I tour this house?",
            {"session_id": "s5", "lead_id": "lead-5", "buyer_agreement_signed": False},
        )
        assert "agreement" in response.content.lower()

    def test_lead_scoring_accumulates(self):
        self.agent.think("I'm interested in buying", {"session_id": "s6", "lead_id": "lead-6"})
        self.agent.think("I'm pre-approved for $500k", {"session_id": "s6", "lead_id": "lead-6"})
        assert self.agent.lead_scores.get("lead-6", 0) > 0.5

    def test_tools_registered(self):
        assert "qualify_lead" in self.agent.tools
        assert "detect_intent" in self.agent.tools
        assert "route_product_path" in self.agent.tools
