"""
Voice Agent - Handles lead qualification, intent detection, and conversation flow.
Delegates to Brain for market data and to Closer for transaction actions.
"""

from agents.base import BaseAgent, AgentRole, AgentResponse, DelegationRequest, Tool
from hearth_llm import LLMClient, get_default_client
from typing import Any, Optional
import json
import logging

log = logging.getLogger(__name__)

_VOICE_COMPOSE_SYSTEM = """You are the Voice agent in Hearth, an AI real estate system.
You talk to customers directly. Your job: write a short, warm reply grounded in FACTS.

HARD RULES — do not violate:
1. Use ONLY information in FACTS. Never invent prices, addresses, or availability.
2. Never use subjective neighborhood terms (good/bad/safe/dangerous/desirable).
3. Never reference protected classes (race, religion, family status, etc).
4. If a tour is requested and buyer_agreement_signed=false, explain the post-NAR
   requirement for a buyer representation agreement BEFORE scheduling.
5. Keep it under 100 words. Conversational, not robotic.
6. If the customer asks about an Hearth program, stick to these names:
   - Instant Offer: we buy the home directly, fast close.
   - Listing Boost: we partner with a local agent, backed by our data.
   - Agent Referral: warm referral to a vetted partner agent.
"""


class VoiceAgent(BaseAgent):
    """
    The Voice agent manages the customer-facing conversation:
    - Qualifies leads (high-intent vs looky-loo)
    - Detects intent signals from conversation
    - Routes to appropriate product path
    - Delegates to Brain for market questions, Closer for transaction actions
    """

    INTENT_KEYWORDS = {
        "high_intent": [
            "pre-approved", "preapproved", "need to move", "relocating",
            "under contract", "closing", "make an offer", "ready to buy",
            "financing approved", "loan approved", "mortgage ready",
        ],
        "medium_intent": [
            "interested in", "looking for", "how much", "what's the price",
            "schedule a tour", "see the house", "open house",
            "neighborhood", "school district",
        ],
        "looky_loo": [
            "just browsing", "just looking", "curious", "window shopping",
            "maybe someday", "not ready", "thinking about it",
        ],
    }

    def __init__(self, agent_id=None, llm: Optional[LLMClient] = None):
        self.lead_scores: dict[str, float] = {}
        self.session_intents: dict[str, list[str]] = {}
        self.llm = llm if llm is not None else get_default_client()
        super().__init__(AgentRole.VOICE, agent_id)

    def _setup_tools(self):
        self.register_tool(Tool(
            name="qualify_lead",
            description="Score a lead's intent level based on conversation signals",
            handler=self._qualify_lead,
        ))
        self.register_tool(Tool(
            name="detect_intent",
            description="Extract intent signals from a customer message",
            handler=self._detect_intent,
        ))
        self.register_tool(Tool(
            name="route_product_path",
            description="Determine the best Hearth product path for this lead",
            handler=self._route_product_path,
        ))

    def think(self, message: str, context: dict[str, Any]) -> AgentResponse:
        session_id = context.get("session_id", "default")
        lead_id = context.get("lead_id", session_id)
        reasoning_steps = []
        delegations = []
        tool_calls = []

        # Step 1: Detect intent
        intents = self._detect_intent(message)
        tool_calls.append({"tool": "detect_intent", "result": intents})
        reasoning_steps.append(f"Detected intents: {intents}")

        # Step 2: Update qualification
        qualification = self._qualify_lead(lead_id, intents)
        tool_calls.append({"tool": "qualify_lead", "result": qualification})
        reasoning_steps.append(f"Lead score: {qualification['score']:.2f}, tier: {qualification['tier']}")

        # Step 3: Check if delegation is needed
        lower_msg = message.lower()
        needs_market_data = any(kw in lower_msg for kw in [
            "value", "price", "worth", "market", "comparable", "apprais",
            "how much", "cost", "estimate", "valuation", "comps",
            "what's it worth", "home value", "property value",
        ])
        needs_transaction = any(kw in lower_msg for kw in [
            "offer", "contract", "negotiate", "close", "earnest",
            "buy", "purchase", "submit", "bid", "counter",
        ])
        needs_tour = any(kw in lower_msg for kw in [
            "tour", "visit", "see the house", "showing", "walk through",
            "schedule", "view the property", "open house", "walkthrough",
        ])

        if needs_market_data:
            delegations.append(DelegationRequest(
                from_agent=self.agent_id,
                to_role=AgentRole.BRAIN,
                task="Get valuation and market data",
                context={"property_id": context.get("property_id", ""), "message": message},
            ))
            reasoning_steps.append("Delegating market data request to Brain agent")

        if needs_transaction:
            delegations.append(DelegationRequest(
                from_agent=self.agent_id,
                to_role=AgentRole.CLOSER,
                task="Handle transaction action",
                context={"message": message, "lead_id": lead_id},
            ))
            reasoning_steps.append("Delegating transaction request to Closer agent")

        # Step 4: Generate response (LLM-composed with deterministic facts, rule-based fallback)
        tier = qualification["tier"]
        fallback = self._generate_response(message, tier, needs_market_data, needs_transaction, needs_tour, context)
        facts = {
            "lead_tier": tier,
            "lead_score": round(qualification["score"], 2),
            "needs_market_data": needs_market_data,
            "needs_transaction": needs_transaction,
            "needs_tour": needs_tour,
            "buyer_agreement_signed": bool(context.get("buyer_agreement_signed")),
            "is_delegating_to_brain": any(d.to_role == AgentRole.BRAIN for d in delegations),
            "is_delegating_to_closer": any(d.to_role == AgentRole.CLOSER for d in delegations),
        }
        response_content = self._compose_response(message, facts, fallback)
        confidence = min(0.9, qualification["score"] + 0.3)

        return AgentResponse(
            content=response_content,
            reasoning="\n".join(reasoning_steps),
            confidence=confidence,
            tool_calls_made=tool_calls,
            delegations_made=delegations,
            needs_human=tier == "looky_loo" and qualification["score"] < 0.2,
            human_reason="Very low intent - may benefit from human nurturing" if tier == "looky_loo" and qualification["score"] < 0.2 else None,
        )

    def _compose_response(self, user_message: str, facts: dict, fallback: str) -> str:
        if not self.llm.available:
            return fallback
        # When delegating, Voice's placeholder gets replaced anyway — keep it terse.
        if facts["is_delegating_to_brain"] or facts["is_delegating_to_closer"]:
            return fallback
        try:
            result = self.llm.call(
                system=_VOICE_COMPOSE_SYSTEM,
                user=(
                    f"CUSTOMER_MESSAGE: {user_message}\n\n"
                    f"FACTS:\n{json.dumps(facts, indent=2)}\n\n"
                    "Write your reply now."
                ),
            )
            text = result.text.strip()
            return text if text else fallback
        except Exception as e:
            log.warning("voice llm compose failed, falling back: %s", e)
            return fallback

    def _detect_intent(self, message: str) -> dict:
        lower = message.lower()
        signals = []
        for tier, keywords in self.INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in lower:
                    signals.append({"type": tier, "keyword": kw, "strength": 0.8 if tier == "high_intent" else 0.5})
        return {"signals": signals, "signal_count": len(signals)}

    def _qualify_lead(self, lead_id: str, intents: dict) -> dict:
        current_score = self.lead_scores.get(lead_id, 0.5)
        for signal in intents.get("signals", []):
            if signal["type"] == "high_intent":
                current_score = min(1.0, current_score + 0.15)
            elif signal["type"] == "medium_intent":
                current_score = min(1.0, current_score + 0.05)
            elif signal["type"] == "looky_loo":
                current_score = max(0.0, current_score - 0.1)
        self.lead_scores[lead_id] = current_score
        if current_score >= 0.7:
            tier = "high_intent"
        elif current_score >= 0.4:
            tier = "medium_intent"
        else:
            tier = "looky_loo"
        return {"lead_id": lead_id, "score": current_score, "tier": tier}

    def _route_product_path(self, lead_id: str) -> dict:
        score = self.lead_scores.get(lead_id, 0.5)
        if score >= 0.7:
            return {"path": "instant_offer", "reason": "High-intent buyer, direct cash offer maximizes velocity"}
        elif score >= 0.4:
            return {"path": "listing_boost", "reason": "Medium intent, Listing Boost balances conversion with capital efficiency"}
        else:
            return {"path": "agent_referral", "reason": "Low intent, route to partner agent for nurturing"}

    def _generate_response(self, message: str, tier: str, needs_market: bool, needs_tx: bool, needs_tour: bool, context: dict) -> str:
        lower_msg = message.lower()

        if needs_tour:
            has_agreement = context.get("buyer_agreement_signed", False)
            if not has_agreement:
                return (
                    "I'd love to help you schedule a tour! Before we can arrange that, "
                    "we'll need a signed buyer representation agreement on file - this is "
                    "required since the NAR settlement changes in August 2024. "
                    "I can send you the agreement to review. Shall I do that?"
                )
            return "Great! Let me check available tour times for this property."

        if needs_market:
            return "Let me pull up the latest market data for you. One moment while I analyze current valuations and recent comparable sales in the area."

        if needs_tx:
            return "I can help with that. Let me check the current transaction details and next steps."

        # Topic-specific responses
        if any(kw in lower_msg for kw in ["cash plus", "cashplus", "cash-plus"]):
            return (
                "Listing Boost is Hearth's capital-light program. Here's how it works: "
                "instead of Hearth buying the home directly, we partner you with a "
                "local agent while backing the transaction with our pricing data and "
                "competitive offers. You get Hearth certainty with the personal touch "
                "of a local agent. It's ideal if you want a guided experience. "
                "Would you like to learn more about eligibility?"
            )

        if any(kw in lower_msg for kw in ["cash offer", "direct offer", "sell my home", "sell my house"]):
            return (
                "Hearth's Instant Offer gives you a competitive, all-cash offer on your home "
                "with a flexible close date — typically in as few as 14 days. No showings, "
                "no repairs, no uncertainty. I can start a preliminary valuation if you "
                "share your property address. What's the address?"
            )

        if any(kw in lower_msg for kw in ["key connections", "referral", "partner agent"]):
            return (
                "Agent Referral pairs you with a vetted local agent from Hearth's network. "
                "It's a great option if you want full-service representation while still "
                "benefiting from Hearth's market data. There's no cost to you for the referral. "
                "Want me to match you with an agent in your area?"
            )

        if any(kw in lower_msg for kw in ["neighborhood", "area", "location", "where should", "south austin", "north austin", "east austin", "west austin", "downtown"]):
            return (
                "I can share objective data about Austin neighborhoods — things like median "
                "home prices, school ratings, walkability scores, average days on market, "
                "and commute times. Which area are you most interested in, and what factors "
                "matter most to you (schools, commute, price range)?"
            )

        if any(kw in lower_msg for kw in ["school", "education", "district"]):
            return (
                "Austin has several strong school districts. I can look up specific ratings "
                "and data for neighborhoods you're considering. Would you like me to compare "
                "school ratings for a particular area, or would you like suggestions for "
                "neighborhoods with top-rated schools within a certain budget?"
            )

        if any(kw in lower_msg for kw in ["how does", "how do", "what is", "explain", "tell me about"]):
            return (
                "I'd be happy to explain! Hearth offers three paths depending on your needs: "
                "1) Instant Offer — we buy your home directly for a competitive price. "
                "2) Listing Boost — we partner you with a local agent backed by our data. "
                "3) Agent Referral — we refer you to a vetted agent in our network. "
                "Which one would you like to know more about?"
            )

        if tier == "high_intent":
            return (
                "Based on our conversation, it sounds like you're ready to move forward. "
                "I can help you explore Hearth's cash offer option for a fast, certain close, "
                "or our Listing Boost program which pairs you with a partner agent. "
                "What works best for your timeline?"
            )
        elif tier == "medium_intent":
            return (
                "I'm here to help you explore your options in the Austin market. I can pull up "
                "property valuations, comparable sales, neighborhood data, or help you understand "
                "Hearth's programs (Instant Offer, Listing Boost, Agent Referral). What interests you most?"
            )
        else:
            return (
                "Welcome! I'm your Hearth AI assistant for the Austin market. "
                "Whether you're just starting to explore or ready to make a move, "
                "I can help with property valuations, market trends, and scheduling tours. "
                "What brings you here today?"
            )
