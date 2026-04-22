# Active Context

## Current State
Rebranded from Opendoor → Hearth. Full multi-agent system built, tested (**156 tests passing**), with a web chat demo UI. PRD at `/PRD.md`. Public repo at https://github.com/yashkuceriya/hearth with 30 issues filed. CI (GitHub Actions) runs Go/Python/Ruby on every PR. Claude API wired into all three Python agents with deterministic fallback.

## Recent Changes (this session)
1. **Rebrand** (Opendoor → Hearth): 47 files touched. Proto dir `proto/opendoor/` → `proto/hearth/`. Go module `github.com/yashkuceriya/hearth`. DB names `hearth_*`. Product names `Cash Offer → Instant Offer`, `Cash Plus → Listing Boost`, `Key Connections → Agent Referral`.
2. **PRD written** at `/PRD.md` — personas, principles, architecture, roadmap (P0–P3), success metrics, non-goals, risks.
3. **Memory-bank updated** (this file, projectbrief, productContext, systemPatterns, progress).
4. **Public repo created** at `yashkuceriya/hearth`, initial commit pushed.
5. **30 GitHub issues filed** — P0 ship-blockers (5), P1 real-product (9), P2 production-grade (6), P3 expansion (10). All assigned to yashkuceriya.
6. **CI pipeline** (issue #2 closed): `.github/workflows/ci.yml` runs Go vet+test, Python ruff+pytest, Ruby rspec on push and PR.
7. **Shared Claude client** (`python/src/hearth_llm/`): prompt caching, graceful fallback when `ANTHROPIC_API_KEY` unset, token telemetry.
8. **LLM composition** in Brain (#7 closed), Voice (#6 closed), Closer (#8 closed). All numbers remain deterministic; LLM only writes prose, constrained by hard rules per agent.

## What Works
- Web chat at localhost:8000 with multi-agent pipeline
- Valuation flow: user asks about an address → Voice delegates to Brain → numbers + comps; LLM composes prose if key set
- Offer flow: user wants to make offer → Voice delegates to Closer → guardrail check + TREC form next steps
- Fair Housing blocking: discriminatory requests blocked at inbound with educational response
- Tour gate: buyer agreement required before tours (post-NAR)
- Instant Offer / Listing Boost / Agent Referral program explanations
- Session continuity across multiple messages
- 156 tests across Go (12), Python (100), Ruby (44)
- CI gates every PR

## Next Steps (priority order)
1. **#1 DB migrations** — wire Alembic + sql migrators into service boot
2. **#3 TLS on gRPC** — non-negotiable before real traffic
3. **#5 Deploy to Railway** — public URL for demo
4. **#9 Multi-turn session memory** — unlocks natural conversation across turns
5. **#10 Postgres-backed sessions** — durability

Open issues: 26. See https://github.com/yashkuceriya/hearth/issues.

## Active Decisions
- Web demo uses Python-only (FastAPI + agents), no Go/gRPC needed for demo
- LLM composes prose; deterministic engines produce all numbers — Lawyer gate unchanged
- LLM gracefully disabled when `ANTHROPIC_API_KEY` unset (dev/test stays hermetic)
- Hearth is broker-agnostic — operates as a tech vendor, not a brokerage
