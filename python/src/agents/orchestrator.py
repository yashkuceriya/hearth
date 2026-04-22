"""
Multi-Agent Orchestrator - Routes messages between agents and enforces
the mandatory compliance gateway.

Architecture:
1. Inbound message -> Voice agent (conversation + intent detection)
2. Voice delegates to Brain/Closer as needed
3. ALL outbound messages -> Lawyer agent (non-bypassable compliance check)
4. Only approved messages reach the customer
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
import logging
import uuid

from agents.base import AgentRole
from agents.brain_agent import BrainAgent
from agents.voice_agent import VoiceAgent
from agents.closer_agent import CloserAgent
from agents.lawyer_agent import LawyerAgent

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    turn_id: str
    session_id: str
    user_message: str
    agent_responses: list[dict] = field(default_factory=list)
    delegations: list[dict] = field(default_factory=list)
    final_response: Optional[str] = None
    compliance_result: Optional[str] = None
    blocked: bool = False
    needs_human: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MultiAgentOrchestrator:
    """
    Coordinates the four specialized agents:
    - Voice: customer-facing conversation
    - Brain: market intelligence
    - Closer: transaction management
    - Lawyer: compliance (mandatory on all outbound)

    The orchestrator does NOT generate content itself. It routes between
    agents and enforces that every outbound message passes through the Lawyer.
    """

    def __init__(self):
        self.brain = BrainAgent()
        self.voice = VoiceAgent()
        self.closer = CloserAgent()
        self.lawyer = LawyerAgent()
        self._agents = {
            AgentRole.BRAIN: self.brain,
            AgentRole.VOICE: self.voice,
            AgentRole.CLOSER: self.closer,
            AgentRole.LAWYER: self.lawyer,
        }
        self.conversation_history: list[ConversationTurn] = []
        # Session memory: carries forward key info between turns
        self.session_memory: dict[str, Any] = {}

    def _update_session_memory(self, user_message: str, turn: ConversationTurn):
        """Extract and remember key context from each turn."""
        lower = user_message.lower()

        # Remember address if mentioned
        import re
        addr_match = re.search(
            r'\d+\s+[\w\s]+(?:st|street|ave|avenue|rd|road|dr|drive|ln|lane|blvd|ct|way|pl|circle)\b',
            user_message, re.IGNORECASE,
        )
        if addr_match:
            self.session_memory["address"] = addr_match.group(0).strip()
            self.session_memory["property_id"] = addr_match.group(0).strip()

        # Remember product path interest
        if any(kw in lower for kw in ["cash offer", "direct offer", "sell my home"]):
            self.session_memory["product_path"] = "instant_offer"
        elif any(kw in lower for kw in ["cash plus", "cashplus"]):
            self.session_memory["product_path"] = "listing_boost"
        elif any(kw in lower for kw in ["key connections", "referral", "partner agent"]):
            self.session_memory["product_path"] = "agent_referral"

        # Remember if buyer agreement was discussed
        if "buyer" in lower and "agreement" in lower:
            self.session_memory["buyer_agreement_discussed"] = True

        # Remember valuation from agent responses
        for resp in turn.agent_responses:
            content = resp.get("content", "")
            val_match = re.search(r'estimated value is \$([\d,]+)', content)
            if val_match:
                val_str = val_match.group(1).replace(',', '')
                self.session_memory["last_valuation_cents"] = int(float(val_str) * 100)
                self.session_memory["last_valuation_display"] = f"${val_match.group(1)}"

        # Remember transaction ID
        for resp in turn.agent_responses:
            content = resp.get("content", "")
            if "txn-" in content:
                tx_match = re.search(r'txn-[a-f0-9]+', content)
                if tx_match:
                    self.session_memory["transaction_id"] = tx_match.group(0)

    def process_message(self, session_id: str, user_message: str, context: dict[str, Any] = None) -> ConversationTurn:
        """
        Process a user message through the multi-agent pipeline:

        1. Voice agent processes (intent, qualification, response)
        2. Execute delegations (Voice -> Brain, Voice -> Closer)
        3. Merge delegated results
        4. MANDATORY: Lawyer agent checks the final response
        5. Return approved response or block
        """
        context = context or {}
        context["session_id"] = session_id

        # Inject session memory into context so agents have prior conversation info
        for key, val in self.session_memory.items():
            if key not in context:
                context[key] = val

        # Build conversation summary for agents
        if self.conversation_history:
            recent = self.conversation_history[-3:]  # Last 3 turns
            summary_lines = []
            for t in recent:
                summary_lines.append(f"User: {t.user_message}")
                if t.final_response:
                    summary_lines.append(f"Agent: {t.final_response[:120]}...")
            context["conversation_summary"] = "\n".join(summary_lines)

        turn = ConversationTurn(
            turn_id=str(uuid.uuid4()),
            session_id=session_id,
            user_message=user_message,
        )

        logger.info(f"[Turn {turn.turn_id}] Processing: {user_message[:100]}")

        # Step 0: Check inbound message for Fair Housing violations
        # The user's request itself may be discriminatory — we must not engage with it
        inbound_context = {
            "session_id": session_id,
            "outbound_text": user_message,
            "claims": [],
            "agent_confidence": 1.0,
            "sentiment_score": 0.0,
        }
        inbound_check = self.lawyer.think("Check inbound message", inbound_context)
        if "BLOCKED" in inbound_check.content:
            turn.agent_responses.append({
                "agent": "lawyer",
                "content": inbound_check.content,
                "confidence": 1.0,
                "reasoning": inbound_check.reasoning,
            })
            turn.blocked = True
            turn.compliance_result = inbound_check.content
            turn.final_response = (
                "I appreciate your interest, but I'm not able to provide recommendations "
                "based on the demographic characteristics of neighborhoods. I can help you "
                "find homes based on objective criteria like price range, square footage, "
                "school ratings, commute times, and amenities. How can I help you with that?"
            )
            logger.warning(f"[Turn {turn.turn_id}] Inbound BLOCKED by Fair Housing check")
            self.conversation_history.append(turn)
            return turn

        # Step 1: Voice agent handles conversation
        voice_response = self.voice.think(user_message, context)
        turn.agent_responses.append({
            "agent": "voice",
            "content": voice_response.content,
            "confidence": voice_response.confidence,
            "reasoning": voice_response.reasoning,
        })

        # Step 2: Execute delegations
        all_claims = list(voice_response.claims)
        delegated_contents = []

        for delegation in voice_response.delegations_made:
            logger.info(f"[Turn {turn.turn_id}] Delegation: {delegation.from_agent} -> {delegation.to_role.value}")

            delegated_agent = self._agents.get(delegation.to_role)
            if delegated_agent is None:
                continue

            del_context = {**context, **delegation.context}
            del_response = delegated_agent.think(delegation.task, del_context)

            turn.agent_responses.append({
                "agent": delegation.to_role.value,
                "content": del_response.content,
                "confidence": del_response.confidence,
                "reasoning": del_response.reasoning,
            })
            turn.delegations.append({
                "from": delegation.from_agent,
                "to": delegation.to_role.value,
                "task": delegation.task,
            })

            if del_response.content and del_response.confidence > 0.3:
                delegated_contents.append(del_response.content)

            all_claims.extend(del_response.claims)

            if del_response.needs_human:
                turn.needs_human = True

        # Merge: if delegated agents returned substantive content, use it
        # and drop Voice's placeholder. Otherwise use Voice's response.
        if delegated_contents:
            merged_content = "\n\n".join(delegated_contents)
        else:
            merged_content = voice_response.content

        # Step 3: MANDATORY compliance check via Lawyer
        compliance_context = {
            "session_id": session_id,
            "outbound_text": merged_content,
            "claims": all_claims,
            "agent_confidence": voice_response.confidence,
            "sentiment_score": context.get("sentiment_score", 0.0),
        }

        lawyer_response = self.lawyer.think("Check outbound message", compliance_context)
        turn.compliance_result = lawyer_response.content

        if "BLOCKED" in lawyer_response.content:
            turn.blocked = True
            turn.needs_human = True
            turn.final_response = (
                "I apologize, but I need to rephrase my response. "
                "Let me provide you with accurate, compliant information. "
                "One moment please."
            )
            logger.warning(f"[Turn {turn.turn_id}] BLOCKED by compliance")
        else:
            turn.final_response = merged_content

        if lawyer_response.needs_human:
            turn.needs_human = True

        self.conversation_history.append(turn)
        self._update_session_memory(user_message, turn)
        return turn

    def get_agent_summary(self) -> dict:
        return {
            "agents": {
                role.value: {
                    "agent_id": agent.agent_id,
                    "tools": list(agent.tools.keys()),
                }
                for role, agent in self._agents.items()
            },
            "total_turns": len(self.conversation_history),
            "blocked_turns": sum(1 for t in self.conversation_history if t.blocked),
            "human_escalations": sum(1 for t in self.conversation_history if t.needs_human),
        }
