"""Tests for the Multi-Agent Orchestrator."""

from agents.orchestrator import MultiAgentOrchestrator


class TestMultiAgentOrchestrator:
    def setup_method(self):
        self.orch = MultiAgentOrchestrator()

    def test_four_agents_exist(self):
        assert self.orch.brain.role.value == "brain"
        assert self.orch.voice.role.value == "voice"
        assert self.orch.closer.role.value == "closer"
        assert self.orch.lawyer.role.value == "lawyer"

    def test_each_agent_has_tools(self):
        assert len(self.orch.brain.tools) > 0
        assert len(self.orch.voice.tools) > 0
        assert len(self.orch.closer.tools) > 0
        assert len(self.orch.lawyer.tools) > 0

    def test_basic_greeting(self):
        turn = self.orch.process_message("s1", "Hello, I'm looking for a home in Austin")
        assert turn.final_response is not None
        assert not turn.blocked
        assert len(turn.agent_responses) >= 1

    def test_valuation_triggers_brain_delegation(self):
        turn = self.orch.process_message(
            "s2", "How much is 123 Main St worth?",
            context={"property_id": "prop-123"},
        )
        assert not turn.blocked
        agents_involved = [r["agent"] for r in turn.agent_responses]
        assert "voice" in agents_involved
        assert "brain" in agents_involved
        assert len(turn.delegations) > 0

    def test_offer_triggers_closer_delegation(self):
        turn = self.orch.process_message(
            "s3", "I'd like to make an offer on this property",
            context={"property_id": "prop-456", "valuation_cents": 50000000},
        )
        assert not turn.blocked
        agents_involved = [r["agent"] for r in turn.agent_responses]
        assert "voice" in agents_involved
        assert "closer" in agents_involved

    def test_lawyer_always_runs(self):
        turn = self.orch.process_message("s4", "Hi there")
        assert turn.compliance_result is not None
        assert "APPROVED" in turn.compliance_result or "BLOCKED" in turn.compliance_result

    def test_tour_without_agreement(self):
        turn = self.orch.process_message(
            "s5", "Can I schedule a tour of the house?",
            context={"buyer_agreement_signed": False},
        )
        assert not turn.blocked
        assert "agreement" in turn.final_response.lower()

    def test_high_intent_detection(self):
        turn = self.orch.process_message(
            "s6", "I'm pre-approved for $500k and need to move within 30 days",
        )
        assert not turn.blocked
        voice_resp = next(r for r in turn.agent_responses if r["agent"] == "voice")
        assert voice_resp["confidence"] > 0.5

    def test_multiple_turns(self):
        self.orch.process_message("s7", "I'm looking to buy in Austin")
        self.orch.process_message("s7", "I'm pre-approved for a loan")
        self.orch.process_message("s7", "What's the market like?")
        assert len(self.orch.conversation_history) == 3

    def test_agent_summary(self):
        self.orch.process_message("s8", "Hello")
        summary = self.orch.get_agent_summary()
        assert "agents" in summary
        assert set(summary["agents"].keys()) == {"voice", "brain", "closer", "lawyer"}
        assert summary["total_turns"] == 1

    def test_brain_tools(self):
        tools = list(self.orch.brain.tools.keys())
        assert "check_data_rights" in tools
        assert "get_valuation" in tools

    def test_lawyer_tools(self):
        tools = list(self.orch.lawyer.tools.keys())
        assert "check_fair_housing" in tools
        assert "register_claims" in tools
        assert "check_freshness" in tools

    def test_voice_lead_scoring_accumulates(self):
        self.orch.process_message("s9", "I'm interested in buying", context={"lead_id": "lead-1"})
        self.orch.process_message("s9", "I'm pre-approved for $500k", context={"lead_id": "lead-1"})
        score = self.orch.voice.lead_scores.get("lead-1", 0)
        assert score > 0.5
