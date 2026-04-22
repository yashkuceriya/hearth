# Hearth AI Real Estate Agent

Autonomous multi-agent system (Go + Python + Ruby) for managing lead-to-close real estate in Austin, TX. Compliance-first design: Fair Housing, claim freshness, and UPL are deterministic rules (not LLM classifiers).

## Memory Bank
**Read ALL files in `memory-bank/` at the start of every task.**
- `projectbrief.md` - Core requirements, business context, success metrics
- `productContext.md` - Why it exists, how it works, UX goals
- `systemPatterns.md` - Architecture, service topology, key design patterns
- `techContext.md` - Languages, dependencies, dev setup, constraints
- `activeContext.md` - Current focus, recent changes, next steps
- `progress.md` - What's built, what's left, known issues, test counts

## Quick Reference

### Test Commands
```bash
cd go && go test ./... -race -count=1          # 12 tests
cd python && PYTHONPATH=src python3 -m pytest tests/ -v  # 92 tests
cd ruby && bundle exec rspec                   # 44 tests
```

### Service Ports
| Service | gRPC | HTTP | Language |
|---------|------|------|----------|
| Orchestrator | 50051 | 8080 | Go |
| Brain | 50053 | 8082 | Python |
| Lawyer | 50054 | 8083 | Python |
| Closer | 50055 | 8084 | Ruby |

### Critical Rules
1. **Lawyer agent is deterministic** — never use LLM for compliance checks
2. **Fail closed** — if data is stale or check fails, block the message
3. **TREC forms are populated, not drafted** — UPL guard blocks legal language
4. **Data rights checked before every query** — no MLS/TCAD access without license
5. **Every outbound message goes through Lawyer** — non-bypassable
6. **Post-NAR**: buyer agreement required before tours (effective Aug 2024)

### Conventions
- Go: `internal/` packages, `cmd/` entry points, table-driven tests
- Python: `src/` layout with PYTHONPATH, pydantic dataclasses, pytest
- Ruby: `lib/closer/` modules, sequel (not Rails), rspec
- Proto: `proto/hearth/{service}/v1/` with `go_package` options
- Money: always in cents (int64), never floats
