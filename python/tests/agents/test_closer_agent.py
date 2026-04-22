"""Tests for the Closer Agent."""

from agents.closer_agent import CloserAgent


class TestCloserAgent:
    def setup_method(self):
        self.agent = CloserAgent()

    def test_offer_creation(self):
        response = self.agent.think(
            "I want to make an offer on this property",
            {"property_id": "prop-1", "valuation_cents": 50000000},
        )
        assert response.confidence > 0
        assert len(response.tool_calls_made) > 0

    def test_guardrail_check_in_offer(self):
        response = self.agent.think(
            "Submit offer on this house",
            {"property_id": "prop-2", "valuation_cents": 50000000},
        )
        guardrail_calls = [tc for tc in response.tool_calls_made if tc.get("tool") == "check_guardrails"]
        assert len(guardrail_calls) > 0

    def test_counter_offer(self):
        response = self.agent.think(
            "Can we negotiate the price down?",
            {"valuation_cents": 50000000, "their_price_cents": 48000000, "our_target_cents": 51000000},
        )
        assert "counter" in response.content.lower() or "recommend" in response.content.lower()

    def test_contract_request(self):
        response = self.agent.think("Let's prepare the TREC contract", {"transaction_id": "txn-1"})
        assert "trec" in response.content.lower()

    def test_tools_registered(self):
        assert "create_offer" in self.agent.tools
        assert "check_guardrails" in self.agent.tools
        assert "generate_counter" in self.agent.tools
        assert "populate_trec_form" in self.agent.tools
