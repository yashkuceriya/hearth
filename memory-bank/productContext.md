# Product Context

## Why Hearth Exists
Residential real estate is slow, labor-intensive, and legally fraught. Lead response takes hours; Fair Housing and UPL missteps carry seven-figure consequences; MLS, tax records, inspections, and CRMs live in different silos. LLMs alone can't fix this — they hallucinate, draft legal language accidentally, and can't prove audit provenance.

Hearth is the AI-native operating system for residential real estate built around one principle: **the AI must be bounded by deterministic rules in places where mistakes are unrecoverable.**

## Problems It Solves
1. **Lead response latency** — buyers/sellers wait hours → Hearth answers in seconds across SMS/chat/email/voice.
2. **Fragmented data** — MLS + tax records + inspections scattered → Brain cross-references with provenance.
3. **Pricing risk** — inaccurate offers = bad economics → valuation engine with confidence bounds + visual condition scoring.
4. **Compliance exposure** — Fair Housing + UPL + unsupported claims → deterministic checkers + claim ledger + UPL guard, all fail-closed.
5. **Form workload** — TREC forms eat hours → populate (never draft) promulgated fields with UPL-blocked input.

## How It Works
```
Customer → Voice Agent (qualifies intent, routes conversation)
              ↓ delegates
         Brain Agent (valuations, comparables, visual analysis)
         Closer Agent (offers, negotiation, TREC contracts)
              ↓ every outbound message
         Lawyer Agent (Fair Housing, claim verification, HITL triggers)
              ↓ APPROVED or BLOCKED
         Customer receives response
```

## User Experience Goals
- Seamless omnichannel (SMS/voice/email/web) without losing thread.
- Instant market intelligence with confidence transparency.
- Automated negotiation within broker-configurable guardrails.
- Human handoff when confidence is low, sentiment is hostile, or value is high.
- Post-NAR compliant tour scheduling (buyer agreement gate).
- Regulator-ready audit trail: every claim and every block traces to a source or rule ID.

## Product Paths
Hearth routes each lead to one of three paths based on intent + qualification:
- **Instant Offer** — high-intent, pre-qualified seller → direct cash offer, fastest velocity.
- **Listing Boost** — medium-intent → list with partner agent backed by Hearth's data.
- **Agent Referral** — low-intent / out-of-scope → warm referral to a vetted partner agent.
