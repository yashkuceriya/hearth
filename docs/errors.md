# Error Taxonomy

Hearth errors fall into five buckets. Every raised exception must belong
to one — unstructured `Exception` is a bug.

| Class                 | Meaning                              | Handler behavior                               |
|-----------------------|--------------------------------------|------------------------------------------------|
| `RetryableError`      | Transient; safe to retry with backoff | Agent retries up to 3x, exponential backoff.   |
| `FatalError`          | Give up this turn                    | Return safe fallback to user; log for ops; do not retry. |
| `ComplianceBlockError`| Fair Housing / UPL / freshness block | Return user-facing block message; HITL queue; log with rule_id. |
| `HITLEscalationError` | Human review required (confidence / value / sentiment) | Polite handoff message to user; human queue. |
| `ConfigError`         | Service misconfigured                | Crash service on boot; clear error log.        |

## Per-language implementation

- **Go**: plain `error` values sentinel-typed via `errors.Is` /
  `errors.As`. Sentinel vars in `internal/errors/errors.go`:
  `ErrRetryable`, `ErrFatal`, `ErrComplianceBlock`, `ErrHITL`, `ErrConfig`.
- **Python**: exception hierarchy in `hearth_errors/`:
  `HearthError` → `RetryableError | FatalError | ComplianceBlockError |
  HITLEscalationError | ConfigError`.
- **Ruby**: module hierarchy `Closer::Errors::*` with the same five types.

## When in doubt

- Network blip on an external API → `RetryableError`
- Invalid input after validation passed → `FatalError` (bug in validator)
- Fair Housing rule fired → `ComplianceBlockError` with `rule_id`
- Confidence < threshold → `HITLEscalationError` with `reason`
- `ANTHROPIC_API_KEY` malformed at boot → `ConfigError`

## Metrics

Labeled counter per class: `hearth_errors_total{class, service, agent}`.
See issue #16.

## Do NOT

- Catch `Exception` at a service boundary without re-raising as one of the
  above.
- Return a user-facing error message that leaks internals. Compliance
  messages are the only exception — they intentionally explain the rule.
- Log at `ERROR` level for compliance blocks. That's expected behavior,
  use `INFO` with structured fields so dashboards can trend them.
