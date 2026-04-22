# Hearth — Product Requirements Document

**Status:** Living doc, v1.0
**Owner:** @yashkuceriya
**Last updated:** 2026-04-21

---

## 1. What is Hearth?

Hearth is an AI-native real estate operating system for brokerages and solo agents. It answers leads, values properties, generates offers, populates regulator-promulgated forms, and negotiates within guardrails — with every outbound message passing through a non-bypassable compliance gateway.

**Tagline:** *The AI real estate agent that knows the rules.*

## 2. Why this exists

The residential real estate transaction is slow, labor-intensive, and legally fraught:

- **Lead response latency**: most brokerages take 4–12 hours to respond to a new lead. ~50% of leads go with whichever agent responds first.
- **Compliance exposure**: the 2024 NAR settlement fundamentally changed buyer-agent compensation mechanics. Fair Housing missteps carry seven-figure settlements. Unauthorized practice of law (UPL) is a felony in most states.
- **Pricing inaccuracy**: bad comps → bad offers → either lost deals or balance-sheet bleeding for iBuyers.
- **Fragmented tooling**: MLS, tax records, inspections, CRMs, e-sign, comps all live in different systems.

LLMs alone can't solve this — they hallucinate claims, can accidentally draft legal language (UPL), and can't prove audit provenance. Hearth is built around the principle that **the AI must be bounded by deterministic rules in places where mistakes are unrecoverable**: Fair Housing, claim freshness, form language.

## 3. Who it's for

### Primary personas

1. **Independent Texas brokers** doing 20–200 transactions/year who can't staff 24/7 lead response.
2. **Small-to-mid brokerages** (5–50 agents) who want AI leverage without rebuilding their compliance program.
3. **iBuyers / investor groups** who need accurate, defensible valuations and fast contract turnaround.

### Non-users (at v1)

- Commercial / industrial real estate (different forms, different dynamics)
- Rental / property management (different lifecycle)
- Markets outside Texas (expansion target, not v1)

## 4. Principles

1. **Fail closed.** Stale claim, unlicensed data, failed compliance check → block the message. No "graceful degrade" that leaks.
2. **Deterministic where it matters.** Fair Housing, freshness, UPL — regex + rule IDs, not LLM classifiers. Auditable for regulators.
3. **Populate, don't draft.** TREC forms are filled with factual business data; any attempt to introduce novel legal language is blocked.
4. **Every outbound message goes through Lawyer.** Non-bypassable, implemented as a mandatory pipeline step, not optional middleware.
5. **Claim provenance or it didn't happen.** Every factual statement traces to a source + timestamp. Unknown provenance = stale.

## 5. Architecture (at a glance)

```
Customer
   │
   ▼
┌──────────────┐
│ Orchestrator │ Go · session + channel + routing
└──────┬───────┘
       │
   ┌───┼─────────────┐
   ▼   ▼             ▼
┌─────┐ ┌────────┐ ┌────────┐
│Voice│ │  Brain │ │ Closer │
│ Py  │ │   Py   │ │  Ruby  │
└──┬──┘ └────────┘ └────────┘
   │    valuation,    offers,
   │    comps, data   TREC,
   │    rights        negotiation
   │
   ▼
┌──────────────┐
│   Lawyer     │ Python · Fair Housing + Claim Ledger + HITL
└──────┬───────┘      (non-bypassable, fail-closed)
       ▼
   Customer
```

Services communicate via gRPC with shared Protocol Buffers. PostgreSQL per service; Redis for session state.

## 6. Product scope — what Hearth does

### 6.1 Lead handling
- **Omnichannel inbound** (SMS, web chat, email, voice — in that priority order)
- **Session continuity**: channel switches don't lose thread
- **Intent detection** → routes to Instant Offer / Listing Boost / Agent Referral path
- **Tour eligibility gate**: buyer-representation agreement required before tour (post-NAR)

### 6.2 Valuation (Brain)
- **Comparable-based pricing** with confidence bounds
- **Visual analysis** (photos → condition score, repair estimate)
- **Data rights manager**: every MLS/TCAD call checked against license + use-case + rate limit
- **Claim ledger**: every valuation emits atomic claims with provenance + TTL

### 6.3 Transactions (Closer)
- **TREC form population** (starting with One-to-Four Family Residential, TREC 20-18)
- **UPL guard**: blocks any text containing legal-language patterns (indemnify, waive, hereby…)
- **Event-sourced transaction state machine**: every transition is an immutable event, replayable for audit
- **Automated negotiation** within configurable floor/ceiling/concession guardrails
- **Post-NAR concession validation**

### 6.4 Compliance (Lawyer)
- **Fair Housing**: 8 deterministic rule categories (race, religion, familial status, national origin, disability, sex, color, source-of-income). Rule-ID traceability for every block.
- **Claim freshness**: TTLs per source; fail closed on unknown.
- **HITL triggers**: low confidence, hostile sentiment, high-dollar moves, FH violations → human escalation.
- **Append-only audit trail**: session-scoped, action-filterable, replayable.

## 7. What's built (v0.9)

| Component | Tests | Status |
|-----------|-------|--------|
| Go orchestrator (session, routing, SMS adapter, compliance gateway) | 12 | ✅ |
| Python Brain + Lawyer (multi-agent framework, 4 agents, valuation, data rights, FH, claim ledger, audit, HITL) | 93 | ✅ |
| Ruby Closer (TREC forms, UPL guard, state machine, negotiation guardrails) | 44 | ✅ |
| Web chat demo (FastAPI + static UI) | — | ✅ |
| **Total** | **149** | **All pass** |

## 8. What's missing (the roadmap)

### P0 — Ship-blockers
- [ ] GitHub repo + push (this doc = step 1)
- [ ] CI pipeline (GitHub Actions: lint + test on every PR, matrix over Go/Python/Ruby)
- [ ] Database migration runner wired into orchestrator boot
- [ ] TLS on gRPC endpoints
- [ ] Secrets via env/Vault, not .env committed

### P1 — Real product, not a demo
- [ ] **Real Claude API integration** in agent `think()` methods — replace keyword matching with Claude Opus 4.7 calls (prompt-cached), preserving all deterministic Lawyer gates
- [ ] Multi-turn session memory (remember address/intent within session)
- [ ] API auth (bearer tokens, per-tenant) + rate limiting
- [ ] Email channel adapter (SendGrid)
- [ ] Voice / WebRTC channel (Twilio Voice + Deepgram)
- [ ] Deploy target live (Railway or Render) with domain
- [ ] Session persistence (Postgres-backed, not in-memory)

### P2 — Production-grade
- [ ] OpenTelemetry tracing across the agent pipeline (inbound → routing → Brain/Closer → Lawyer → outbound)
- [ ] Prometheus metrics: latency, compliance block rate, confidence distribution, HITL rate, per-agent p50/p95
- [ ] Alerting: compliance-block spikes, HITL escalation backlog
- [ ] MLS production data license (Austin Board of Realtors)
- [ ] Load testing (target: p95 < 2s inbound → outbound)
- [ ] Structured error taxonomy (retryable vs fatal vs HITL)

### P3 — Market expansion & depth
- [ ] Additional TREC forms: Third Party Financing (40-10), Property Condition (12-08), Amendment (39-10), Seller's Disclosure (OP-H), Addendum for Sale of Other Property (10-7)
- [ ] Calendar integration (Google/Outlook) for tour scheduling
- [ ] Repair Co-Pilot: visual analysis → contractor scheduling → concession calculation
- [ ] Cohort analytics dashboard (days-in-possession, margin by path, per-agent performance)
- [ ] Multi-market expansion: abstract form registry per state (FL, CA, AZ next)
- [ ] Broker admin UI (rule overrides, guardrail tuning, HITL queue)

## 9. Success metrics

**North-star:** `qualified_leads_per_agent_per_week` — measures whether Hearth actually creates capacity.

**Leading indicators:**
- p50 inbound-to-first-response latency **< 10s**
- Compliance violations **= 0** (any is a P0)
- Claim-provenance coverage **= 100%** (every outbound factual statement has a source)
- Offer acceptance rate **≥ parity with human agents** in pilot market

**Operational:**
- HITL escalation rate **< 15%** of sessions (higher = too cautious or too confused)
- Test coverage **≥ 80%** for any service touching compliance
- Mean time to resolve P0 **< 4 hours**

## 10. Non-goals

- **We are not replacing licensed agents.** We are force-multiplying them. Licensed-agent handoff is a first-class feature, not a failure mode.
- **We will not generate novel legal language.** Ever. TREC forms only.
- **We will not use LLMs for Fair Housing or freshness gating.** These must remain deterministic and auditable.
- **We will not bulk-transfer TCAD data.** Single-request ingestion, rate limited.

## 11. Open questions

1. **Pricing model** — per-seat, per-transaction, per-lead, or flat? Pilot will inform.
2. **Brokerage-of-record** — does Hearth operate as a tech vendor to a brokerage, or does it need its own brokerage license in each market?
3. **LLM cost ceiling** — with prompt caching, per-conversation cost should land ~$0.03–0.08. Need to validate under real load.
4. **HITL staffing** — do brokerages provide their own humans, or does Hearth run an escalation desk?

## 12. Risks

| Risk | Mitigation |
|------|------------|
| LLM hallucinates a valuation claim that causes legal action | Claim ledger with fail-closed freshness; Lawyer blocks any unsourced claim. |
| FH regex rule misses a novel violation pattern | Rules are additive; every escalation that surfaces a new pattern adds a rule ID. HITL catches ambiguous cases. |
| UPL guard blocks legitimate business language → agent frustration | Guard is on TREC form fields only, not chat responses. Chat has its own Lawyer gate. |
| Data-rights license lapses silently | DataRightsManager checks expiry on every call. Expired = deny. |
| Compliance gateway becomes a latency bottleneck | Lawyer is stateless and parallelizable; target p95 < 200ms. |

---

*This PRD is the source of truth for what Hearth does and doesn't do. Feature work should reference a section here or open a PR against this doc first.*
