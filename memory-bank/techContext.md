# Tech Context

## Languages & Versions
- **Go 1.23**: Orchestrator, session management, channel adapters, gRPC server
- **Python 3.11+**: Brain (valuation, data rights, visual analysis), Lawyer (compliance, claims, audit), Agent framework
- **Ruby 2.6+** (system): Closer (TREC forms, state machine, negotiation). Gemfile targets sequel + pg + rspec.

## Key Dependencies

### Go
- `google.golang.org/grpc` - gRPC server/client
- `google.golang.org/protobuf` - Protocol Buffers
- `github.com/google/uuid` - UUID generation
- `github.com/lib/pq` - PostgreSQL driver
- `github.com/redis/go-redis/v9` - Redis client
- `go.uber.org/zap` - Structured logging

### Python
- `grpcio` + `grpcio-tools` - gRPC server/client + code generation
- `protobuf` - Protocol Buffers
- `psycopg2-binary` - PostgreSQL driver
- `sqlalchemy` + `alembic` - ORM + migrations
- `pydantic` - Data validation
- `httpx` - HTTP client
- `pytest` + `ruff` + `mypy` - Testing + linting + type checking

### Ruby
- `sequel` ~5.76 - Database toolkit (NOT Rails)
- `pg` ~1.5 - PostgreSQL driver
- `rspec` ~3.13 - Testing

## Development Setup
```bash
# Infrastructure
cd deploy && docker compose up -d postgres redis

# Go
cd go && go mod tidy && go build ./... && go test ./...

# Python
cd python && pip install -e ".[dev]"
PYTHONPATH=src python3 -m pytest tests/ -v

# Ruby
cd ruby && bundle install --path vendor/bundle
bundle exec rspec
```

## Technical Constraints
1. **System Ruby is 2.6**: Can't use google-protobuf gem (requires 2.7+). Removed grpc/protobuf gems from Gemfile. Ruby service communicates via the Go orchestrator calling it, not direct proto.
2. **TCAD no-bulk-transfer**: Data Rights Manager enforces single-request ingestion only. Rate limited to 60 req/hour.
3. **MLS production license required**: Currently only RESO dev reference data available (previous year, not for production).
4. **Texas UPL rules**: TREC forms cannot have novel legal language. The FieldDefinition class has a `contains_legal_language?` guard.
5. **No LLM in Lawyer**: Fair Housing and compliance checks are deterministic regex rules, not LLM-based. This is by design for auditability.

## Infrastructure
- PostgreSQL 16 (4 databases, one per service)
- Redis 7 (session state)
- Docker Compose for local dev (all 6 services defined)
- Multi-stage Dockerfiles with non-root users
- Health checks: gRPC health + HTTP `/healthz` + `/readyz`

## Environment Variables
See `.env.example` for the full list. Key ones:
- `POSTGRES_*` - Database connection
- `REDIS_URL` - Session store
- `SERVICE_NAME` - Python service selector (brain/lawyer)
- `GRPC_PORT` / `HTTP_PORT` - Service ports
- `ANTHROPIC_API_KEY` - For future LLM integration
- `TWILIO_*` - SMS channel
- `MLS_RESO_*` - Market data
