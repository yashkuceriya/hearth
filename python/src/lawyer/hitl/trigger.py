"""
Human-in-the-Loop Trigger Engine.
Automatically escalates to a human when:
1. Sentiment turns hostile
2. Legal complexity exceeds agent confidence
3. Transaction value exceeds autonomous authority
4. Fair Housing violation detected
"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class HITLDecision:
    escalate: bool
    reason: str
    priority: str  # "immediate", "soon", "review"
    suggested_action: str


class HITLTriggerEngine:
    """
    Determines when to hand off to a human operator.
    Thresholds are configurable per deployment.
    """

    def __init__(
        self,
        sentiment_threshold: float = -0.5,
        confidence_threshold: float = 0.3,
        max_autonomous_value_cents: int = 75000000,  # $750k
    ):
        self.sentiment_threshold = sentiment_threshold
        self.confidence_threshold = confidence_threshold
        self.max_autonomous_value_cents = max_autonomous_value_cents

    def check(
        self,
        sentiment_score: float,
        agent_confidence: float,
        transaction_value_cents: Optional[int] = None,
        fair_housing_violation: bool = False,
        context: str = "",
    ) -> HITLDecision:
        """Evaluate whether human intervention is needed."""

        # IMMEDIATE: Fair Housing violation always escalates
        if fair_housing_violation:
            return HITLDecision(
                escalate=True,
                reason="Fair Housing compliance violation detected",
                priority="immediate",
                suggested_action="Review flagged content and customer interaction before proceeding",
            )

        # IMMEDIATE: Hostile sentiment
        if sentiment_score < self.sentiment_threshold:
            return HITLDecision(
                escalate=True,
                reason=f"Hostile sentiment detected (score: {sentiment_score:.2f})",
                priority="immediate",
                suggested_action="Take over conversation, address customer concerns directly",
            )

        # SOON: Low agent confidence
        if agent_confidence < self.confidence_threshold:
            return HITLDecision(
                escalate=True,
                reason=f"Agent confidence below threshold (score: {agent_confidence:.2f})",
                priority="soon",
                suggested_action="Review agent's proposed response and provide guidance",
            )

        # SOON: High-value transaction
        if transaction_value_cents and transaction_value_cents > self.max_autonomous_value_cents:
            return HITLDecision(
                escalate=True,
                reason=f"Transaction value ${transaction_value_cents/100:,.0f} exceeds autonomous limit",
                priority="soon",
                suggested_action="Review and approve transaction parameters before proceeding",
            )

        return HITLDecision(
            escalate=False,
            reason="All thresholds within acceptable range",
            priority="review",
            suggested_action="No action needed",
        )
