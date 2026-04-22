# Progress

## What's Built ✅

### Infrastructure
- [x] Monorepo structure (proto/, go/, python/, ruby/, deploy/, web/)
- [x] 5 Protocol Buffer definitions under `proto/hearth/`
- [x] Docker Compose with all 6 services (postgres, redis, orchestrator, brain, lawyer, closer)
- [x] Multi-stage Dockerfiles for all services
- [x] `.env.example`, `.gitignore`, Makefile, README.md, PRD.md
- [x] Database migration SQL files (Go: 3, Ruby: 1)

### Go Orchestrator (12 tests)
- [x] Session manager (create, get, update, resume across channels)
- [x] SMS channel adapter (Twilio)
- [x] Channel adapter interface (voice/SMS/email/web_chat)
- [x] Product-path router (Instant Offer / Listing Boost / Agent Referral)
- [x] Tour eligibility gate (post-NAR buyer agreement enforcement)
- [x] Compliance gateway (non-bypassable, fail-closed)
- [x] Orchestrator engine + multi-agent engine
- [x] Agent client interface + local Python client
- [x] gRPC server with health checks, graceful shutdown

### Shared Claude LLM Client (7 tests)
- [x] `python/src/hearth_llm/` — prompt caching, structured output parsing, JSON extraction
- [x] Graceful fallback when `ANTHROPIC_API_KEY` unset (`LLMClient.available` returns False)
- [x] Token + cache-hit telemetry via structured log lines

### Python Brain + Lawyer + Voice + Closer (100 tests)
- [x] Multi-agent framework (BaseAgent, Tool, DelegationRequest, AgentResponse)
- [x] Brain agent (valuation, data rights, visual analysis tools)
- [x] Voice agent (intent detection, lead scoring, product-path routing, delegation)
- [x] Closer agent (offers, guardrails, counter-offers, TREC form trigger)
- [x] Lawyer agent (fair housing, claims, freshness, HITL, audit)
- [x] MultiAgentOrchestrator (Voice → delegations → Lawyer compliance)
- [x] Data Rights Manager (license gating, rate limiting, TCAD no-bulk)
- [x] Valuation engine (comparables, condition scoring, confidence bounds)
- [x] Visual property analyzer (condition scoring, repair estimation)
- [x] Fair Housing checker (8 deterministic rule categories)
- [x] Claim ledger (append-only, fail-closed freshness, state reproduction)
- [x] Audit trail (append-only, session-scoped, action-filterable)
- [x] HITL trigger engine (sentiment, confidence, value, Fair Housing)
- [x] Config management, health checks, structured logging, server entry points

### Ruby Closer (44 tests)
- [x] TREC field definitions with type validation + UPL guard
- [x] Form registry with version tracking
- [x] One-to-Four Family form (TREC 20-18) field population
- [x] Event-sourced transaction state machine with milestones
- [x] Negotiation guardrails (floor/ceiling/concession limits)
- [x] Negotiation engine (counter-offers, round tracking)
- [x] Post-NAR concession validation
- [x] Config, health server, server entry point

### Web Demo
- [x] FastAPI web server wrapping MultiAgentOrchestrator
- [x] Chat UI (light theme, OKLCH, DM Sans/Serif)
- [x] Inbound Fair Housing check (blocks discriminatory user messages)
- [x] Rich agent responses (valuations with comps, offers with guardrails)
- [x] Delegation context forwarding (Brain/Closer read original user message)
- [x] Deploy configs (Dockerfile, render.yaml, railway.toml)

## What's Left to Build 🔲

### P0 (Deploy Blockers)
- [x] Push to GitHub (repo live at yashkuceriya/hearth)
- [x] CI pipeline (GitHub Actions matrix over Go/Python/Ruby) — issue #2
- [ ] Deploy to Railway/Render — issue #5
- [ ] Database migration runner integration — issue #1
- [ ] TLS on gRPC endpoints — issue #3
- [ ] Secrets management (not .env files) — issue #4

### P1 (Real product, not a demo)
- [x] Real Claude API integration (shared client + Brain/Voice/Closer composition with deterministic fallback) — issues #6, #7, #8
- [ ] Multi-turn session memory (address/intent within session)
- [ ] API authentication (bearer tokens, per-tenant) + rate limiting
- [ ] Email channel adapter (SendGrid)
- [ ] Voice/WebRTC channel adapter (Twilio Voice + Deepgram)
- [ ] Session persistence (Postgres-backed, not in-memory)

### P2 (Production-grade)
- [ ] OpenTelemetry tracing across agent pipeline
- [ ] Prometheus metrics (latency, compliance block rate, confidence distribution, HITL rate)
- [ ] Alerting (compliance blocks, HITL escalations)
- [ ] MLS production data license
- [ ] Load testing (target p95 < 2s inbound → outbound)
- [ ] Structured error taxonomy

### P3 (Market expansion & depth)
- [ ] Additional TREC forms (Third Party Financing 40-10, Property Condition 12-08, Amendment 39-10, Seller's Disclosure OP-H, Addendum 10-7)
- [ ] Calendar integration for tour scheduling (Google/Outlook)
- [ ] Repair Co-Pilot (visual analysis → contractor scheduling → concession calculation)
- [ ] Cohort analytics dashboard
- [ ] Multi-market expansion (FL, CA, AZ)
- [ ] Broker admin UI (rule overrides, guardrail tuning, HITL queue)

## Known Issues
- System Ruby is 2.6 — can't use google-protobuf gem. Ruby service doesn't do direct proto communication (Go calls it as HTTP/gRPC bridge).
- Python `conftest.py` adds `src/` to path; `PYTHONPATH=src` still needed for CLI runs.
- Agents use rule-based reasoning (keyword matching), not actual LLM calls yet — P1 priority.
- No Alembic migrations created yet (alembic is a dependency but no `versions/` directory).

## Test Summary
| Language | Tests | Status |
|----------|-------|--------|
| Go | 12 | ✅ All pass |
| Python | 100 | ✅ All pass |
| Ruby | 44 | ✅ All pass |
| **Total** | **156** | **✅ All pass** |
