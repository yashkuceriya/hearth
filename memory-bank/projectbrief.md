# Project Brief: Hearth

## Overview
Hearth is an AI-native real estate operating system: an autonomous multi-agent system that answers leads, values properties, generates offers, populates regulator-promulgated forms, and negotiates within guardrails — with every outbound message passing through a non-bypassable compliance gateway. Initial pilot market: Austin, TX (Travis County).

See [`PRD.md`](../PRD.md) for the full product spec.

## Core Requirements
1. **Multi-Agent Architecture**: 4 specialized agents (Voice, Brain, Closer, Lawyer) coordinated by an orchestrator.
2. **Three Languages**: Go (orchestration), Python (intelligence + compliance), Ruby (transactions + contracts).
3. **Compliance-first**: Fair Housing + claim freshness + UPL are deterministic rules, not LLM classifiers. Auditable for regulators.
4. **Production safety**: Every outbound message passes through a non-bypassable compliance gateway. Claims have freshness contracts that fail closed.
5. **Broker-agnostic**: Hearth operates as a tech vendor to licensed brokerages, not a brokerage itself.

## Target Market
- v1: Austin, TX (TREC jurisdiction, TCAD data, Austin MLS)
- v1.5: expand to other Texas markets (same TREC forms)
- v2: other states (abstract form registry per state)

## Success Metrics
- **North-star**: qualified leads per agent per week
- p50 inbound-to-first-response latency < 10s
- Zero Fair Housing violations
- 100% claim provenance coverage
- Offer acceptance rate ≥ parity with human agents

## Non-Goals (v1)
- Commercial / rental / property management
- Generating novel legal language (TREC form population only)
- Replacing licensed agents (Hearth force-multiplies them)
- Using LLMs for compliance gating (must stay deterministic)
