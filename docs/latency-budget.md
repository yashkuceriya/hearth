# Latency Budget

Target p95 inbound → outbound: **2 seconds**. If we miss this, customers
notice the lag. If we stay under, the conversation feels snappy.

## Per-stage budget

| Stage                                    | p50   | p95    | Notes                                       |
|------------------------------------------|-------|--------|---------------------------------------------|
| Channel ingest (webhook/WS → orchestrator)| 30ms  | 80ms   | Twilio/SendGrid webhook dispatch + TLS.     |
| Session lookup (Redis hot, Postgres cold)| 10ms  | 60ms   | Redis first; Postgres on miss.              |
| Inbound Fair Housing check (Lawyer)      | 40ms  | 100ms  | Regex-only, no LLM.                         |
| Voice.think() (intent + routing)         | 200ms | 800ms  | LLM call (prompt-cached).                   |
| **Brain.think() or Closer.think()**      | **400ms** | **1200ms** | LLM + valuation/guardrail computation. Parallel with other delegates when possible. |
| Lawyer outbound check                    | 50ms  | 150ms  | Regex rules + freshness TTL lookups.        |
| Outbound send (TwiML/email/WS)           | 30ms  | 80ms   | SDK dispatch.                               |
| **Total**                                | **~760ms** | **~2.0s** | Matches p95 target when parallelism works. |

## Parallelism

When Voice delegates to both Brain and Closer in the same turn, the two
should run concurrently, not serially. Current orchestrator runs them
sequentially — see follow-up work in orchestrator.py.

## Alerting

Each stage has a budget. When p95 for a stage exceeds 2x its budget for
10+ minutes, alert. See issue #17 for the Prometheus rules that wire this.

## Trade-offs

- **Prompt caching** is non-negotiable. Without cached system prompts,
  Voice.think() p95 easily hits 2s on its own.
- **Fail-closed Lawyer gate** adds ~150ms worst-case but is never
  optional. Any proposal to parallelize Lawyer with outbound dispatch
  must preserve the invariant that Lawyer approves before send.
- **LLM fallback**: when the Anthropic API returns in > 3s, drop to the
  deterministic rule-based response. See `hearth_llm/client.py` timeout
  (default 10s, but agent wrappers should be more aggressive).

## How to measure

- OpenTelemetry spans per stage (see #15).
- Prometheus histograms: `hearth_inbound_duration_seconds` with a
  `stage` label (see #16).
- Load tests with k6 under `loadtest/` (see #18).
