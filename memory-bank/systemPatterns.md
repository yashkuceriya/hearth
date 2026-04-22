# System Patterns

## Architecture: Multi-Agent Microservices

### Service Topology
| Service | Language | gRPC Port | HTTP Port | Database |
|---------|----------|-----------|-----------|----------|
| Orchestrator | Go | 50051 | 8080 | hearth_orchestrator |
| Brain | Python | 50053 | 8082 | hearth_brain |
| Lawyer | Python | 50054 | 8083 | hearth_lawyer |
| Closer | Ruby | 50055 | 8084 | hearth_closer |

### Communication Patterns
- **gRPC** with shared Protocol Buffer definitions in `proto/hearth/`
- **PostgreSQL** per service (separate databases for data ownership/compliance)
- **Redis** for session state (Go orchestrator)
- **Event-driven**: PostgreSQL LISTEN/NOTIFY for cross-service events (no Kafka yet)

### Key Design Patterns

#### 1. Compliance Gateway (Non-Bypassable)
Every outbound message passes through the Lawyer agent. This is implemented as a mandatory step in the orchestrator pipeline, not optional middleware.
```
Voice response → Lawyer.check() → APPROVED → send to customer
                                → BLOCKED → fallback response + HITL
```

#### 2. Fail-Closed Freshness Contracts
Claims have TTLs. If data is stale, the message is blocked. Unknown claims are treated as stale. Correct default for a regulated domain.

#### 3. Data Rights Gating
All MLS/TCAD access goes through DataRightsManager. It checks license, market, use-case, rate limits, and expiry BEFORE any query. TCAD enforces no-bulk-transfer.

#### 4. Product-Path Routing
Not just "answer questions" — the system decides which product path maximizes expected value:
- Instant Offer (high-intent, agreement signed)
- Listing Boost (medium-intent, agent partnership)
- Agent Referral (low-intent, referral to vetted partner)

#### 5. Event-Sourced Transaction State Machine
Ruby Closer uses an event-sourced FSM for transactions. Every state transition is an immutable event. The machine can be reconstructed from its event log for audit.

#### 6. UPL Guard on TREC Forms
The Ruby form populator blocks any text that contains legal language patterns (hereby, indemnify, waive rights, etc.). TREC forms are populated with factual/business data ONLY.

#### 7. Deterministic Fair Housing
NOT an LLM content filter. Uses regex rules with IDs (FH-RACE-001, FH-FAM-001, etc.). Every violation traces to a specific rule with a legal explanation. This is auditable for regulators.

### Agent Delegation Pattern
Each agent has:
- A `think()` method (reasoning loop)
- Registered `Tool`s it can invoke
- Ability to create `DelegationRequest`s to other agents
- Structured `AgentResponse` with confidence, reasoning trace, and claims

Voice is the entry point. It delegates to Brain (market data) and Closer (transactions). Lawyer checks everything.
