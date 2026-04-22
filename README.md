# Hearth AI Real Estate Agent

Hearth is an AI-native real estate operating system: an autonomous multi-agent system that answers leads, values properties, generates offers, populates regulator-promulgated forms, and negotiates within guardrails — with every outbound message passing through a non-bypassable compliance gateway. Built across three languages with compliance-first design.

> **See [`PRD.md`](PRD.md) for the full product spec.**

## Architecture

| Service | Language | Port | Purpose |
|---------|----------|------|---------|
| **Orchestrator** | Go | 50051 | Session management, channel adapters, policy gateway, product-path routing |
| **Brain** | Python | 50053 | Valuation engine, data rights manager, MLS/TCAD connectors, visual analysis |
| **Lawyer** | Python | 50054 | Fair Housing checker, claim ledger, audit trail, HITL triggers |
| **Closer** | Ruby | 50055 | TREC form population, transaction state machine, negotiation with guardrails |

### Communication
- gRPC with shared Protocol Buffer definitions in `proto/`
- PostgreSQL per service + Redis for session state
- Compliance Gateway: every outbound message passes through Lawyer (non-bypassable)

## Key Differentiators

- **Product-Path Router**: Routes leads to Instant Offer / Listing Boost / Agent Referral based on intent + expected value
- **Post-NAR Compliance**: Tour Eligibility Gate enforces buyer agreement requirements (effective Aug 17, 2024)
- **Deterministic Fair Housing**: Rule-based checker with audit trail, not LLM content filtering
- **Claim Ledger**: Every outbound statement decomposed into atomic claims with data provenance + freshness contracts (fail-closed)
- **Data Rights Manager**: Gates all MLS/TCAD access through license checks; enforces TCAD no-bulk-transfer restriction
- **TREC Form Population**: Strictly populates promulgated form fields; UPL guard blocks novel legal language
- **Financial Guardrails**: Automated negotiation within configurable bounds; post-NAR concession validation

## Multi-Agent Flow

```
User Message
    │
    ▼
┌─────────┐   delegates   ┌─────────┐
│  Voice  │──────────────▶│  Brain  │  market data, valuations
│  Agent  │   delegates   │  Agent  │
│         │──────────────▶├─────────┤
│         │               │ Closer  │  offers, negotiation, TREC
│         │               │  Agent  │
└────┬────┘               └─────────┘
     │ merged response
     ▼
┌─────────┐
│ Lawyer  │  ← MANDATORY on every outbound message
│  Agent  │  Fair Housing + Claim Freshness + HITL
└────┬────┘
     │ APPROVED / BLOCKED
     ▼
  Customer
```

Each agent has its own tools, reasoning trace, confidence score, and delegation capability. The Lawyer agent is non-bypassable and fail-closed.

## Quick Start

```bash
# Development (local)
cd deploy && docker compose up -d postgres redis

cd go && go build ./... && go test ./... -race
cd python && pip install -e ".[dev]" && PYTHONPATH=src python3 -m pytest tests/ -v
cd ruby && bundle install --path vendor/bundle && bundle exec rspec

# Production (Docker Compose)
cd deploy && docker compose up -d   # All 6 services
```

## Test Results

- **Go**: 12 tests (routing, tour eligibility, compliance gateway, agent types)
- **Python**: 92 tests (agents, data rights, valuation, visual analysis, fair housing, claims, audit, HITL)
- **Ruby**: 44 tests (TREC forms, state machine, negotiation guardrails, concessions)
- **Total**: 148 tests passing

## Production Readiness

- Multi-stage Dockerfiles for all services (non-root users, minimal images)
- Docker Compose with all 6 services, health checks, dependency ordering
- Structured JSON logging for production (`LOG_FORMAT=json`)
- HTTP health endpoints (`/healthz`, `/readyz`) for load balancers
- gRPC health checking for service discovery
- Graceful shutdown handlers (SIGTERM/SIGINT)
- Centralized config from environment variables with dev defaults
- CI test Dockerfile (`deploy/docker/Dockerfile.test`)

## Project Structure

```
proto/                    # Shared Protocol Buffer definitions
  hearth/{common,brain,voice,closer,lawyer}/v1/

go/                       # Orchestrator (Go)
  cmd/orchestrator/       # Entry point with gRPC server
  internal/agents/        # Multi-agent client interface
  internal/orchestrator/  # Engine + multi-agent engine
  internal/routing/       # Product-path router, tour gate
  internal/compliance/    # Non-bypassable compliance gateway
  internal/session/       # Session management
  internal/channel/       # SMS/voice/email adapters
  Dockerfile

python/                   # Brain + Lawyer (Python)
  src/agents/             # Multi-agent framework (base, orchestrator, 4 agents)
  src/brain/              # Valuation, data rights, visual analysis
  src/lawyer/             # Fair housing, claims, audit, HITL
  src/config.py           # Centralized configuration
  src/health.py           # HTTP health endpoints
  src/run_server.py       # Production gRPC entry point
  Dockerfile

ruby/                     # Closer (Ruby)
  lib/closer/trec/        # TREC form population engine
  lib/closer/workflow/    # Transaction state machine
  lib/closer/negotiation/ # Guardrails + negotiation engine
  lib/server.rb           # Production entry point
  Dockerfile

deploy/                   # Docker Compose + infra
  docker-compose.yml      # All 6 services with health checks
  docker/Dockerfile.test  # CI test runner
```
