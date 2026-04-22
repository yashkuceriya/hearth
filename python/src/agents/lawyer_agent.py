"""
Lawyer Agent - Compliance, truth verification, and safety enforcement.
On the CRITICAL PATH of every outbound message. Non-bypassable.
"""

from agents.base import BaseAgent, AgentRole, AgentResponse, Tool
from lawyer.fair_housing.checker import FairHousingChecker
from lawyer.claims.ledger import ClaimLedger, ClaimSource
from lawyer.audit.trail import AuditTrail
from lawyer.hitl.trigger import HITLTriggerEngine
from datetime import datetime, timezone
from typing import Any


class LawyerAgent(BaseAgent):
    """
    The Lawyer agent ensures every outbound message is:
    1. Fair Housing compliant (deterministic check)
    2. Backed by verifiable claims with data provenance
    3. Within freshness windows (fail closed if stale)
    4. Escalated to humans when appropriate

    All compliance logic is deterministic and auditable. Not LLM-based.
    """

    def __init__(self, agent_id=None):
        self.fair_housing = FairHousingChecker()
        self.claim_ledger = ClaimLedger()
        self.audit_trail = AuditTrail()
        self.hitl_engine = HITLTriggerEngine()
        super().__init__(AgentRole.LAWYER, agent_id)

    def _setup_tools(self):
        self.register_tool(Tool(
            name="check_fair_housing",
            description="Run deterministic Fair Housing compliance check on text",
            handler=self._check_fair_housing,
        ))
        self.register_tool(Tool(
            name="register_claims",
            description="Register claims from an outbound message in the claim ledger",
            handler=self._register_claims,
        ))
        self.register_tool(Tool(
            name="check_freshness",
            description="Verify all referenced claims are still within freshness window",
            handler=self._check_freshness,
        ))
        self.register_tool(Tool(
            name="check_hitl",
            description="Evaluate whether human intervention is needed",
            handler=self._check_hitl,
        ))
        self.register_tool(Tool(
            name="record_audit",
            description="Record an action in the immutable audit trail",
            handler=self._record_audit,
        ))

    def think(self, message: str, context: dict[str, Any]) -> AgentResponse:
        """
        Runs on EVERY outbound message:
        1. Fair Housing check (deterministic)
        2. Claim registration and freshness verification
        3. HITL evaluation
        4. Audit trail recording

        If ANY check fails, the message is BLOCKED (fail-closed).
        """
        session_id = context.get("session_id", "unknown")
        outbound_text = context.get("outbound_text", message)
        agent_confidence = context.get("agent_confidence", 0.5)
        sentiment_score = context.get("sentiment_score", 0.0)
        reasoning_steps = []
        tool_calls = []

        # Step 1: Fair Housing check
        fh_result = self._check_fair_housing(outbound_text, session_id)
        tool_calls.append({"tool": "check_fair_housing", "result": fh_result})
        reasoning_steps.append(f"Fair Housing check: compliant={fh_result['compliant']}")

        if not fh_result["compliant"]:
            self._record_audit(session_id, "fair_housing_violation_blocked", "lawyer_agent", {
                "violations": str(fh_result["violations"]),
            })
            return AgentResponse(
                content=f"BLOCKED: Message contains {len(fh_result['violations'])} Fair Housing violation(s). "
                        f"Violations: {', '.join(v['rule_id'] for v in fh_result['violations'])}",
                reasoning="\n".join(reasoning_steps),
                confidence=1.0,
                tool_calls_made=tool_calls,
                needs_human=True,
                human_reason="Fair Housing violation detected - requires human review",
            )

        # Step 2: Register claims
        incoming_claims = context.get("claims", [])
        registered_claim_ids = []
        for claim_data in incoming_claims:
            claim = self._register_claims(
                session_id=session_id,
                statement=claim_data["statement"],
                source_system=claim_data.get("source_system", "UNKNOWN"),
                source_id=claim_data.get("source_id", ""),
                freshness_ttl=claim_data.get("freshness_ttl", 3600),
            )
            registered_claim_ids.append(claim["claim_id"])
            tool_calls.append({"tool": "register_claims", "result": claim})

        reasoning_steps.append(f"Registered {len(registered_claim_ids)} claims")

        # Step 3: Freshness check
        existing_claim_ids = context.get("referenced_claim_ids", [])
        all_claim_ids = registered_claim_ids + existing_claim_ids
        if all_claim_ids:
            freshness = self._check_freshness(all_claim_ids)
            tool_calls.append({"tool": "check_freshness", "result": freshness})
            reasoning_steps.append(f"Freshness check: stale={freshness['stale_ids']}")

            if freshness["stale_ids"]:
                self._record_audit(session_id, "stale_claims_blocked", "lawyer_agent", {
                    "stale_claim_ids": str(freshness["stale_ids"]),
                })
                return AgentResponse(
                    content=f"BLOCKED: {len(freshness['stale_ids'])} claim(s) have expired freshness windows. "
                            "Data must be re-verified before sending.",
                    reasoning="\n".join(reasoning_steps),
                    confidence=1.0,
                    tool_calls_made=tool_calls,
                )

        # Step 4: HITL check
        hitl = self._check_hitl(sentiment_score, agent_confidence, session_id)
        tool_calls.append({"tool": "check_hitl", "result": hitl})
        reasoning_steps.append(f"HITL check: escalate={hitl['escalate']}")

        # Step 5: Audit
        self._record_audit(session_id, "outbound_message_approved", "lawyer_agent", {
            "claims_registered": str(len(registered_claim_ids)),
        })

        return AgentResponse(
            content="APPROVED: Message passed all compliance checks.",
            reasoning="\n".join(reasoning_steps),
            confidence=1.0,
            tool_calls_made=tool_calls,
            needs_human=hitl["escalate"],
            human_reason=hitl.get("reason") if hitl["escalate"] else None,
        )

    def _check_fair_housing(self, text: str, session_id: str = "") -> dict:
        result = self.fair_housing.check(text, session_id=session_id)
        return {
            "compliant": result.compliant,
            "violations": [
                {"rule_id": v.rule_id, "type": v.violation_type, "matched": v.matched_text}
                for v in result.violations
            ],
            "sanitized_text": result.sanitized_text,
        }

    def _register_claims(self, session_id: str, statement: str, source_system: str,
                         source_id: str, freshness_ttl: int = 3600) -> dict:
        source = ClaimSource(
            source_system=source_system, source_id=source_id,
            source_statement=statement, relevance_score=1.0,
            retrieved_at=datetime.now(timezone.utc),
        )
        claim = self.claim_ledger.record_claim(
            session_id=session_id, statement=statement,
            sources=[source], freshness_ttl_seconds=freshness_ttl,
        )
        return {"claim_id": claim.id, "status": claim.status.value}

    def _check_freshness(self, claim_ids: list[str]) -> dict:
        results = self.claim_ledger.check_freshness(claim_ids)
        stale = [cid for cid, fresh in results.items() if not fresh]
        return {"all_fresh": len(stale) == 0, "stale_ids": stale}

    def _check_hitl(self, sentiment_score: float, agent_confidence: float, session_id: str = "") -> dict:
        decision = self.hitl_engine.check(sentiment_score=sentiment_score, agent_confidence=agent_confidence)
        return {"escalate": decision.escalate, "reason": decision.reason, "priority": decision.priority}

    def _record_audit(self, session_id: str, action: str, actor: str, details: dict = None) -> dict:
        entry = self.audit_trail.record(session_id, action, actor, details)
        return {"audit_id": entry.id}
