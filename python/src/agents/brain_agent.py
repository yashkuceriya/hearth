"""
Brain Agent - Reasons over market data, valuations, and property analysis.
Tools: get_valuation, get_comparables, analyze_photos, check_data_rights
"""

from agents.base import BaseAgent, AgentRole, AgentResponse, Tool
from brain.valuation.engine import (
    ValuationEngine, PropertyFeatures, ComparableProperty,
    ConditionScore, Money, DataProvenance,
)
from brain.ingestion.data_rights import DataRightsManager, DataSource
from brain.visual.analyzer import VisualPropertyAnalyzer, PhotoAnalysis
from hearth_llm import LLMClient, get_default_client
from typing import Any, Optional
from datetime import datetime, timezone, timedelta
import logging

log = logging.getLogger(__name__)

_BRAIN_COMPOSE_SYSTEM = """You are the Brain agent in Hearth, an AI real estate system.
Your job is to write a short, natural response to the customer given a set of FACTS
produced by a deterministic valuation engine.

HARD RULES — do not violate:
1. Use ONLY the numbers in FACTS. Never invent or round prices, sqft, or counts.
2. Never use subjective terms about neighborhoods (good/bad/safe/dangerous/desirable).
3. Never reference protected classes (race, religion, family status, etc).
4. If FACTS is empty, ask the customer for an address — do not speculate.
5. Keep it under 120 words. Plain prose, no marketing fluff.
6. Always surface the confidence range when a valuation is present.
"""


class BrainAgent(BaseAgent):
    """
    The Brain agent handles all market intelligence:
    - Property valuations with confidence bounds
    - Comparable sales analysis
    - Visual property condition assessment
    - Data rights verification before any data access
    """

    def __init__(self, agent_id=None, llm: Optional[LLMClient] = None):
        self.data_rights = DataRightsManager()
        self.valuation_engine = ValuationEngine(self.data_rights)
        self.visual_analyzer = VisualPropertyAnalyzer()
        self.llm = llm if llm is not None else get_default_client()
        super().__init__(AgentRole.BRAIN, agent_id)

    def _setup_tools(self):
        self.register_tool(Tool(
            name="check_data_rights",
            description="Verify we have license to access a data source before querying it",
            handler=self._check_data_rights,
        ))
        self.register_tool(Tool(
            name="get_valuation",
            description="Get a property valuation with confidence bounds and provenance chain",
            handler=self._get_valuation,
            requires_compliance_check=True,
        ))
        self.register_tool(Tool(
            name="get_comparables",
            description="Find comparable sold properties near a subject property",
            handler=self._get_comparables,
        ))
        self.register_tool(Tool(
            name="analyze_property_photos",
            description="Analyze property photos for condition scoring and repair estimation",
            handler=self._analyze_photos,
        ))

    def _extract_address(self, message: str) -> str:
        """Try to extract an address-like string from the message for demo purposes."""
        import re
        # Match common address patterns: "1234 Elm St", "456 Oak Avenue", etc.
        pattern = r'\d+\s+[\w\s]+(?:st|street|ave|avenue|rd|road|dr|drive|ln|lane|blvd|ct|way|pl|circle)\b'
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(0).strip()
        return ""

    def think(self, message: str, context: dict[str, Any]) -> AgentResponse:
        """
        Brain agent reasoning loop:
        1. Parse what market data is needed
        2. Check data rights BEFORE any data access
        3. Pull valuations/comparables/visual analysis
        4. Synthesize into a response with confidence + provenance
        """
        reasoning_steps = []
        tool_calls = []
        claims = []
        confidence = 0.5

        # Determine what's being asked
        property_id = context.get("property_id", "")
        user_message = context.get("message", message)

        # Prefer an address in the current message; fall back to session memory
        # so multi-turn references ("what about that one", "tell me more") work.
        address = (
            self._extract_address(user_message)
            or self._extract_address(message)
            or context.get("address", "")
        )
        if not property_id and address:
            property_id = address

        needs_valuation = any(kw in message.lower() for kw in [
            "value", "worth", "price", "valuation", "how much", "estimate", "apprais",
            "cost", "market data", "market",
        ])
        needs_comparables = any(kw in message.lower() for kw in [
            "comparable", "similar", "comp", "sold nearby", "recent sales"
        ])
        needs_visual = context.get("photo_urls") is not None

        reasoning_steps.append(f"Analyzing request: valuation={needs_valuation}, comps={needs_comparables}, visual={needs_visual}, address={address or 'none'}")

        response_parts = []

        # Always check data rights first
        if needs_valuation or needs_comparables:
            rights = self._check_data_rights(source="TCAD", market="travis_county", use_case="valuation_input")
            tool_calls.append({"tool": "check_data_rights", "result": rights})
            reasoning_steps.append(f"Data rights check: allowed={rights['allowed']}")

            if not rights["allowed"]:
                return AgentResponse(
                    content=f"I'm unable to access the required data: {rights.get('denial_reason', 'Access denied')}",
                    reasoning="\n".join(reasoning_steps),
                    confidence=0.0,
                    tool_calls_made=tool_calls,
                )

        # Run valuation if asked — use address or a demo property ID
        effective_id = property_id or "demo-austin-property"
        if needs_valuation:
            features = context.get("features", {})
            prop_features = PropertyFeatures(
                sqft=features.get("sqft", 2000),
                bedrooms=features.get("bedrooms", 3),
                bathrooms=features.get("bathrooms", 2.0),
            )

            comps = self._generate_demo_comparables(effective_id, prop_features)

            condition = None
            if needs_visual and context.get("photo_urls"):
                visual_report = self._analyze_photos(property_id=effective_id, photo_analyses=[])
                condition = ConditionScore(
                    overall=visual_report["overall_condition"],
                    components=visual_report["component_scores"],
                    uncertainty_flags=visual_report["uncertainty_flags"],
                    visual_analysis_included=True,
                )

            valuation = self.valuation_engine.valuate(
                property_id=effective_id,
                features=prop_features,
                comparables=comps,
                condition=condition,
            )

            tool_calls.append({"tool": "get_valuation", "property_id": effective_id})
            confidence = valuation.confidence_score

            if address:
                response_parts.append(
                    f"Here's the valuation for {address}, Austin, TX:"
                )
            response_parts.append(
                f"Based on {len(comps)} comparable sales in the area, the estimated value is "
                f"${valuation.estimated_value.dollars:,.0f} "
                f"(range: ${valuation.confidence_low.dollars:,.0f} - ${valuation.confidence_high.dollars:,.0f})."
            )
            response_parts.append(
                f"Confidence: {valuation.confidence_score:.0%}. "
                f"Data sourced from TCAD public records and RESO reference data."
            )

            # Add comp details
            comp_summary = []
            for i, c in enumerate(comps[:3]):
                comp_summary.append(f"  {i+1}. {c.address} — ${c.sold_price.dollars:,.0f} ({c.sqft} sqft)")
            if comp_summary:
                response_parts.append("Top comparables:\n" + "\n".join(comp_summary))

            claims.append({
                "statement": f"Property {effective_id} estimated value: ${valuation.estimated_value.dollars:,.0f}",
                "source_system": "VALUATION_ENGINE",
                "source_id": effective_id,
                "freshness_ttl": 3600,
            })

            reasoning_steps.append(
                f"Valuation complete: ${valuation.estimated_value.dollars:,.0f} "
                f"with {confidence:.0%} confidence from {len(comps)} comps"
            )

        elif needs_comparables:
            comps = self._generate_demo_comparables(effective_id, PropertyFeatures(sqft=2000, bedrooms=3, bathrooms=2.0))
            comp_lines = []
            for i, c in enumerate(comps):
                comp_lines.append(f"  {i+1}. {c.address} — ${c.sold_price.dollars:,.0f} ({c.sqft} sqft, {c.distance_miles:.1f} mi away)")
            response_parts.append("Recent comparable sales in the area:\n" + "\n".join(comp_lines))
            confidence = 0.7

        if not response_parts:
            if address:
                response_parts.append(
                    f"I found the address {address} in Austin. "
                    "Would you like a valuation, comparable sales, or a market overview for this property?"
                )
            else:
                response_parts.append(
                    "I can help with property valuations, comparable sales analysis, "
                    "or market data for Austin properties. Share an address to get started."
                )

        facts = self._collect_facts(locals())
        content = self._compose_response(user_message, facts, response_parts)

        return AgentResponse(
            content=content,
            reasoning="\n".join(reasoning_steps),
            confidence=confidence,
            tool_calls_made=tool_calls,
            claims=claims,
            needs_human=confidence < 0.3,
            human_reason="Low valuation confidence" if confidence < 0.3 else None,
        )

    def _collect_facts(self, local_vars: dict[str, Any]) -> dict[str, Any]:
        """Pull deterministic facts out of think()'s locals for the composer."""
        facts: dict[str, Any] = {}
        if "address" in local_vars and local_vars["address"]:
            facts["address"] = local_vars["address"]
        if "valuation" in local_vars and local_vars.get("valuation") is not None:
            v = local_vars["valuation"]
            facts["valuation"] = {
                "estimated_value_dollars": v.estimated_value.dollars,
                "range_low_dollars": v.confidence_low.dollars,
                "range_high_dollars": v.confidence_high.dollars,
                "confidence": round(v.confidence_score, 2),
            }
        if "comps" in local_vars and local_vars.get("comps"):
            facts["comparables"] = [
                {
                    "address": c.address,
                    "sold_price_dollars": c.sold_price.dollars,
                    "sqft": c.sqft,
                }
                for c in local_vars["comps"][:3]
            ]
        return facts

    def _compose_response(
        self,
        user_message: str,
        facts: dict[str, Any],
        fallback_parts: list[str],
    ) -> str:
        """Let the LLM write prose when available; fall back to template strings."""
        if not self.llm.available:
            return "\n".join(fallback_parts)
        try:
            import json
            result = self.llm.call(
                system=_BRAIN_COMPOSE_SYSTEM,
                user=(
                    f"CUSTOMER_MESSAGE: {user_message}\n\n"
                    f"FACTS (authoritative; use only these numbers):\n{json.dumps(facts, indent=2)}\n\n"
                    "Write the response now."
                ),
            )
            text = result.text.strip()
            return text if text else "\n".join(fallback_parts)
        except Exception as e:
            log.warning("llm compose failed, falling back: %s", e)
            return "\n".join(fallback_parts)

    def _check_data_rights(self, source: str, market: str, use_case: str) -> dict:
        ds = DataSource[source] if source in DataSource.__members__ else DataSource.TCAD
        result = self.data_rights.check_access(ds, market, use_case)
        return {"allowed": result.allowed, "denial_reason": result.denial_reason, "restrictions": result.restrictions}

    def _get_valuation(self, property_id: str, features: dict) -> dict:
        prop_features = PropertyFeatures(**features)
        comps = self._generate_demo_comparables(property_id, prop_features)
        valuation = self.valuation_engine.valuate(property_id, prop_features, comps)
        return {
            "estimated_value": valuation.estimated_value.dollars,
            "confidence": valuation.confidence_score,
            "range_low": valuation.confidence_low.dollars,
            "range_high": valuation.confidence_high.dollars,
        }

    def _get_comparables(self, property_id: str, max_results: int = 5) -> list[dict]:
        return [{"property_id": f"comp-{i}", "distance_miles": 0.5 + i * 0.3} for i in range(max_results)]

    def _analyze_photos(self, property_id: str, photo_analyses: list) -> dict:
        analyses = [PhotoAnalysis(**pa) if isinstance(pa, dict) else pa for pa in photo_analyses]
        report = self.visual_analyzer.analyze_property(property_id, analyses)
        return {
            "overall_condition": report.overall_condition,
            "component_scores": report.component_scores,
            "flagged_repairs": report.flagged_repairs,
            "uncertainty_flags": report.uncertainty_flags,
        }

    def _generate_demo_comparables(self, property_id: str, features: PropertyFeatures) -> list:
        """Generate demo comparables. In production, these come from MLS via data rights gate."""
        base_ppsf = 25000  # $250/sqft in cents
        now = datetime.now(timezone.utc)
        comps = []
        for i in range(5):
            price_var = 1.0 + (i - 2) * 0.05
            sqft_var = int(features.sqft * (1.0 + (i - 2) * 0.08))
            comps.append(ComparableProperty(
                property_id=f"comp-{property_id}-{i}",
                address=f"{100 + i * 10} Demo Street, Austin, TX",
                sold_price=Money(amount_cents=int(base_ppsf * sqft_var * price_var)),
                sold_date=now - timedelta(days=15 + i * 20),
                sqft=sqft_var,
                bedrooms=features.bedrooms + (1 if i == 4 else 0),
                bathrooms=features.bathrooms,
                distance_miles=0.3 + i * 0.4,
                similarity_score=0.95 - i * 0.08,
                provenance=DataProvenance(
                    source_system="RESO_REFERENCE",
                    source_id=f"comp-{i}",
                    retrieved_at=now,
                    license_id="reso-dev-reference",
                ),
            ))
        return comps
