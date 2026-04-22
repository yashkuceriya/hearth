"""Tests for the Lawyer Agent."""

from agents.lawyer_agent import LawyerAgent


class TestLawyerAgent:
    def setup_method(self):
        self.agent = LawyerAgent()

    def test_approves_clean_message(self):
        response = self.agent.think("Check outbound message", {
            "session_id": "s1",
            "outbound_text": "This 3-bedroom home is in zip 78704 near top-rated schools.",
            "agent_confidence": 0.8, "sentiment_score": 0.5, "claims": [],
        })
        assert "APPROVED" in response.content

    def test_blocks_fair_housing_violation(self):
        response = self.agent.think("Check outbound message", {
            "session_id": "s2",
            "outbound_text": "This is in a predominantly white neighborhood.",
            "agent_confidence": 0.8, "sentiment_score": 0.5, "claims": [],
        })
        assert "BLOCKED" in response.content
        assert response.needs_human

    def test_registers_claims(self):
        response = self.agent.think("Check outbound message", {
            "session_id": "s3",
            "outbound_text": "The property is valued at $450,000.",
            "agent_confidence": 0.8, "sentiment_score": 0.5,
            "claims": [{
                "statement": "Property valued at $450,000",
                "source_system": "VALUATION_ENGINE",
                "source_id": "prop-123", "freshness_ttl": 3600,
            }],
        })
        assert "APPROVED" in response.content
        register_calls = [tc for tc in response.tool_calls_made if tc.get("tool") == "register_claims"]
        assert len(register_calls) > 0

    def test_escalates_low_confidence(self):
        response = self.agent.think("Check outbound message", {
            "session_id": "s4",
            "outbound_text": "Based on limited data, value might be $400k.",
            "agent_confidence": 0.1, "sentiment_score": 0.5, "claims": [],
        })
        assert response.needs_human

    def test_audit_trail_recorded(self):
        self.agent.think("Check outbound message", {
            "session_id": "s5",
            "outbound_text": "Hello, how can I help?",
            "agent_confidence": 0.8, "sentiment_score": 0.5, "claims": [],
        })
        assert self.agent.audit_trail.total_entries > 0

    def test_tools_registered(self):
        tools = list(self.agent.tools.keys())
        assert "check_fair_housing" in tools
        assert "register_claims" in tools
        assert "check_freshness" in tools
        assert "check_hitl" in tools
        assert "record_audit" in tools
