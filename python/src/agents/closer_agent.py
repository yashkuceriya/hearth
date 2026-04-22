"""
Closer Agent - Manages transactions, negotiation, and contract operations.
"""

from agents.base import BaseAgent, AgentRole, AgentResponse, DelegationRequest, Tool
from typing import Any
import uuid as _uuid


class CloserAgent(BaseAgent):
    """
    The Closer agent manages the transaction lifecycle:
    - Generates offers within financial guardrails
    - Handles counter-offer strategy
    - Triggers TREC form population
    - Orchestrates closing milestones
    """

    GUARDRAIL_FLOOR_MARGIN = 0.02
    GUARDRAIL_CEILING_MARGIN = 0.15
    MAX_CONCESSION_PCT = 0.06

    def __init__(self, agent_id=None):
        self.transactions: dict[str, dict] = {}
        self.negotiation_rounds: dict[str, list] = {}
        super().__init__(AgentRole.CLOSER, agent_id)

    def _setup_tools(self):
        self.register_tool(Tool(
            name="create_offer",
            description="Create a new offer for a property within financial guardrails",
            handler=self._create_offer,
        ))
        self.register_tool(Tool(
            name="check_guardrails",
            description="Verify a proposed price is within Hearth's financial guardrails",
            handler=self._check_guardrails,
        ))
        self.register_tool(Tool(
            name="generate_counter",
            description="Generate a counter-offer strategy within guardrails",
            handler=self._generate_counter,
        ))
        self.register_tool(Tool(
            name="populate_trec_form",
            description="Populate a TREC promulgated form with transaction data (field fill only, no legal drafting)",
            handler=self._populate_trec_form,
            requires_compliance_check=True,
        ))

    def think(self, message: str, context: dict[str, Any]) -> AgentResponse:
        reasoning_steps = []
        tool_calls = []
        delegations = []
        claims = []
        confidence = 0.7

        transaction_id = context.get("transaction_id")
        property_id = context.get("property_id", "")
        valuation_cents = context.get("valuation_cents", 0) or context.get("last_valuation_cents", 0)

        # Check both the delegation task AND the original user message
        user_msg = context.get("message", "")
        combined = f"{message} {user_msg}".lower()
        wants_offer = any(kw in combined for kw in ["make an offer", "submit offer", "offer on", "cash offer", "buy", "purchase"])
        wants_counter = any(kw in combined for kw in ["counter", "negotiate", "come down"])
        wants_contract = any(kw in combined for kw in ["contract", "paperwork", "trec"])

        if wants_offer:
            reasoning_steps.append("Processing offer request")

            # Extract a price from the message if present
            import re
            price_match = re.search(r'\$?\s*([\d,]+(?:\.\d{2})?)\s*(?:k|K)?', message)
            if price_match:
                price_str = price_match.group(1).replace(',', '')
                parsed_price = float(price_str)
                if parsed_price < 10000:  # Probably in thousands
                    parsed_price *= 1000
                valuation_cents = int(parsed_price * 100)

            if not valuation_cents:
                valuation_cents = 48500000  # $485k Austin average

            proposed = context.get("proposed_price_cents", int(valuation_cents * 0.99))
            guardrail_result = self._check_guardrails(valuation_cents, proposed)
            tool_calls.append({"tool": "check_guardrails", "result": guardrail_result})
            reasoning_steps.append(f"Guardrail check: within_bounds={guardrail_result['within_bounds']}")

            if guardrail_result["within_bounds"]:
                offer = self._create_offer(property_id or "pending", proposed, valuation_cents)
                tool_calls.append({"tool": "create_offer", "result": offer})
                claims.append({
                    "statement": f"Offer submitted at ${proposed/100:,.0f}",
                    "source_system": "CLOSER_ENGINE",
                    "source_id": offer["transaction_id"],
                    "freshness_ttl": 86400,
                })
                discount_pct = (1 - proposed / valuation_cents) * 100
                address = context.get("address", "")
                addr_line = f" for {address}" if address else ""
                content = (
                    f"I've prepared a cash offer{addr_line} at ${proposed/100:,.0f} ({discount_pct:.0f}% below estimated value of ${valuation_cents/100:,.0f}).\n\n"
                    f"Guardrail check passed:\n"
                    f"  Floor: ${guardrail_result['floor']/100:,.0f}\n"
                    f"  Ceiling: ${guardrail_result['ceiling']/100:,.0f}\n"
                    f"  Expected margin: {guardrail_result['margin']:.1%}\n\n"
                    f"Next steps: I'll prepare the TREC One to Four Family Contract (Form 20-18) "
                    f"and pull title. Shall I proceed?"
                )
            else:
                content = (
                    f"The proposed price is outside our financial guardrails.\n"
                    f"Violations: {', '.join(guardrail_result['violations'])}.\n"
                    f"I can adjust the offer to fit within bounds — would you like me to?"
                )
                confidence = 0.5

        elif wants_counter:
            reasoning_steps.append("Processing counter-offer request")
            their_price = context.get("their_price_cents", 0)
            our_target = context.get("our_target_cents", valuation_cents)
            counter = self._generate_counter(valuation_cents, their_price, our_target)
            tool_calls.append({"tool": "generate_counter", "result": counter})
            content = (
                f"Based on the market analysis, I recommend countering at "
                f"${counter['counter_price']/100:,.0f}. "
                f"This represents a {counter['strategy']}."
            )

        elif wants_contract:
            reasoning_steps.append("Processing contract request - TREC form population")
            delegations.append(DelegationRequest(
                from_agent=self.agent_id,
                to_role=AgentRole.LAWYER,
                task="Pre-check contract data for compliance",
                context={"transaction_id": transaction_id},
            ))
            content = (
                "I'll prepare the TREC One to Four Family Residential Contract (Form 20-18). "
                "This is the standard promulgated form for Texas residential transactions. "
                "I'll populate the factual and business fields only - the form language itself "
                "is set by TREC and cannot be modified."
            )

        else:
            content = (
                "I can help with making offers, negotiating terms, preparing TREC contracts, "
                "or checking transaction status. What would you like to do?"
            )

        return AgentResponse(
            content=content,
            reasoning="\n".join(reasoning_steps),
            confidence=confidence,
            tool_calls_made=tool_calls,
            delegations_made=delegations,
            claims=claims,
        )

    def _create_offer(self, property_id: str, price_cents: int, valuation_cents: int) -> dict:
        tx_id = f"txn-{_uuid.uuid4().hex[:8]}"
        self.transactions[tx_id] = {
            "transaction_id": tx_id, "property_id": property_id,
            "offer_price_cents": price_cents, "state": "offer_submitted",
        }
        return {"transaction_id": tx_id, "price_cents": price_cents, "state": "offer_submitted"}

    def _check_guardrails(self, valuation_cents: int, proposed_cents: int, concessions_cents: int = 0) -> dict:
        floor = int(valuation_cents * (1 - self.GUARDRAIL_FLOOR_MARGIN))
        ceiling = int(valuation_cents * (1 + self.GUARDRAIL_CEILING_MARGIN))
        violations = []
        if proposed_cents < floor:
            violations.append(f"Below floor (${floor/100:,.0f})")
        if proposed_cents > ceiling:
            violations.append(f"Above ceiling (${ceiling/100:,.0f})")
        if concessions_cents > proposed_cents * self.MAX_CONCESSION_PCT:
            violations.append(f"Concessions exceed {self.MAX_CONCESSION_PCT*100}%")
        net = proposed_cents - concessions_cents
        margin = (net - valuation_cents) / valuation_cents if valuation_cents else 0
        return {"within_bounds": len(violations) == 0, "violations": violations, "floor": floor, "ceiling": ceiling, "margin": margin}

    def _generate_counter(self, valuation_cents: int, their_price: int, our_target: int) -> dict:
        gap = their_price - our_target
        counter = our_target + int(gap * 0.4)
        strategy = "splitting the difference, biased toward our target"
        return {"counter_price": counter, "strategy": strategy}

    def _populate_trec_form(self, transaction_id: str, form_type: str = "one_to_four_family") -> dict:
        tx = self.transactions.get(transaction_id, {})
        return {"form_type": form_type, "form_version": "20-18", "status": "populated" if tx else "error"}
