"""Tests for HITL Trigger Engine."""

from lawyer.hitl.trigger import HITLTriggerEngine


class TestHITLTriggerEngine:
    def setup_method(self):
        self.engine = HITLTriggerEngine()

    def test_no_escalation_normal_conditions(self):
        result = self.engine.check(
            sentiment_score=0.5,
            agent_confidence=0.8,
        )
        assert result.escalate is False

    def test_escalation_hostile_sentiment(self):
        result = self.engine.check(
            sentiment_score=-0.7,
            agent_confidence=0.8,
        )
        assert result.escalate is True
        assert result.priority == "immediate"

    def test_escalation_low_confidence(self):
        result = self.engine.check(
            sentiment_score=0.5,
            agent_confidence=0.2,
        )
        assert result.escalate is True
        assert result.priority == "soon"

    def test_escalation_high_value_transaction(self):
        result = self.engine.check(
            sentiment_score=0.5,
            agent_confidence=0.8,
            transaction_value_cents=100000000,  # $1M
        )
        assert result.escalate is True

    def test_escalation_fair_housing_violation(self):
        result = self.engine.check(
            sentiment_score=0.5,
            agent_confidence=0.8,
            fair_housing_violation=True,
        )
        assert result.escalate is True
        assert result.priority == "immediate"
        assert "Fair Housing" in result.reason

    def test_fair_housing_overrides_all(self):
        """Fair Housing violation ALWAYS escalates, even with positive sentiment."""
        result = self.engine.check(
            sentiment_score=1.0,
            agent_confidence=1.0,
            fair_housing_violation=True,
        )
        assert result.escalate is True
