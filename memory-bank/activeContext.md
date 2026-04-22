# Active Context

## Current State
Rebranded from Opendoor → Hearth. Full multi-agent system built, tested (149 tests passing), with a web chat demo UI. PRD written at `/PRD.md`. Next: GitHub repo + issue backlog + P0/P1 grind.

## Recent Changes
1. **Rebrand**: global rename `Opendoor → Hearth`, `opendoor → hearth`, proto packages moved to `proto/hearth/`, Go module path (`github.com/yashkuceriya/hearth`), DB names (`hearth_*`), product names (`Cash Offer → Instant Offer`, `Cash Plus → Listing Boost`, `Key Connections → Agent Referral`).
2. **PRD written** at `/PRD.md` — describes product, personas, principles, roadmap (P0–P3), success metrics, non-goals, risks.
3. **Memory-bank updated** to reflect Hearth positioning (broker-agnostic, compliance-first, TX-first).
4. All 149 tests still pass post-rename.

## What Works
- Web chat at localhost:8000 with multi-agent pipeline
- Valuation flow: user asks about an address → Voice delegates to Brain → numbers + comps
- Offer flow: user wants to make offer → Voice delegates to Closer → guardrail check + TREC form next steps
- Fair Housing blocking: discriminatory requests blocked at inbound with educational response
- Tour gate: buyer agreement required before tours (post-NAR)
- Instant Offer / Listing Boost / Agent Referral program explanations
- Neighborhood queries → objective data framing
- Session continuity across multiple messages
- 149 tests across Go (12), Python (93), Ruby (44)

## Next Steps
1. **GitHub repo** — `yashkuceriya/hearth` public, initial commit, push main.
2. **Issue backlog** — break PRD roadmap into vertical-slice issues, all assigned to yashkuceriya.
3. **P1 grind** — real Claude API wiring, CI pipeline, auth, TLS, email adapter, session persistence.
4. **Deploy target** — Railway or Render with a domain.

## Active Decisions
- Web demo uses Python-only (FastAPI + agents), no Go/gRPC needed for demo
- Sessions stored in-memory for demo; Postgres-backed in production (P1)
- Lawyer checks both inbound AND outbound messages
- Delegated agent responses replace Voice's placeholder (not concatenated)
- Hearth is broker-agnostic — operates as a tech vendor, not a brokerage
