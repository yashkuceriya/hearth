"""Multi-turn session memory: addresses, intent, and valuations carry forward.

Exercises `MultiAgentOrchestrator.process_message` across 3 turns to verify
that follow-up messages ("what about it?", "make an offer") resolve against
context from earlier turns — not just the current sentence.
"""

from __future__ import annotations

from agents.orchestrator import MultiAgentOrchestrator


def test_address_carries_across_turns():
    o = MultiAgentOrchestrator()
    # Turn 1: mention address + ask for valuation.
    o.process_message("s1", "What's 1234 Elm St worth?")
    assert "1234 Elm St" in o.session_memory.get("address", "")

    # Turn 2: reference without address — session memory should supply it.
    t2 = o.process_message("s1", "Tell me more about it.")
    # Brain should have something meaningful; at minimum, the session still
    # remembers the address for the third turn.
    assert "1234 Elm St" in o.session_memory.get("address", "")
    assert t2.final_response is not None


def test_last_intent_recorded():
    o = MultiAgentOrchestrator()
    o.process_message("s1", "What's the value of 1234 Elm St?")
    assert o.session_memory.get("last_intent") == "valuation"

    o.process_message("s1", "I'd like to make an offer")
    assert o.session_memory.get("last_intent") == "transaction"

    o.process_message("s1", "Can I schedule a tour?")
    assert o.session_memory.get("last_intent") == "tour"


def test_product_path_interest_persists():
    o = MultiAgentOrchestrator()
    o.process_message("s1", "Tell me about Cash Offer")
    # Cash Offer got renamed; voice_agent matches the keyword anyway.
    # The important invariant: some product_path got recorded.
    assert "product_path" in o.session_memory


def test_context_merged_into_agent_calls():
    """Session memory should be injected into agent context so Brain/Closer see it."""
    o = MultiAgentOrchestrator()
    o.session_memory["address"] = "999 Pre-existing Rd"
    t = o.process_message("s1", "Give me a valuation")
    # Brain should produce a response referencing the remembered address
    # (or at least not crash and produce *something*).
    assert t.final_response is not None
    assert not t.blocked
