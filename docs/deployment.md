# Deployment & Secrets

## Environment variables by service

### All services
| Var | Required | Sensitivity | Notes |
|-----|----------|-------------|-------|
| `POSTGRES_HOST`     | yes | low  | Host only; no creds in here. |
| `POSTGRES_PORT`     | no  | low  | Default 5432. |
| `POSTGRES_USER`     | yes | low  | `hearth` in dev. |
| `POSTGRES_PASSWORD` | yes | **high** | Never commit. Platform secret. |
| `LOG_LEVEL`         | no  | low  | `debug` / `info` / `warn`. |

### Orchestrator (Go)
| Var | Required | Sensitivity |
|-----|----------|-------------|
| `ORCHESTRATOR_DB`     | yes | low | Default `hearth_orchestrator`. |
| `ORCHESTRATOR_GRPC_PORT` | no | low | Default 50051. |
| `ORCHESTRATOR_HTTP_PORT` | no | low | Default 8080. |
| `REDIS_URL`           | yes | **high** (password in URL) | Sessions. |
| `TWILIO_ACCOUNT_SID`  | no  | **high** | Required for SMS channel. |
| `TWILIO_AUTH_TOKEN`   | no  | **high** | Required for SMS channel. |
| `TWILIO_PHONE_NUMBER` | no  | low      | Public, still env-var per convention. |

### Brain + Lawyer (Python)
| Var | Required | Sensitivity |
|-----|----------|-------------|
| `BRAIN_DB` / `LAWYER_DB` | yes | low | Per service name. |
| `ANTHROPIC_API_KEY`   | yes (prod) | **high** | LLM calls. Omit for dev to get rule-based fallback. |
| `MLS_RESO_API_URL`    | yes (prod) | low  | |
| `MLS_RESO_API_KEY`    | yes (prod) | **high** | |
| `TCAD_API_URL`        | no  | low  | |

### Closer (Ruby)
| Var | Required | Sensitivity |
|-----|----------|-------------|
| `CLOSER_DB` | yes | low | Default `hearth_closer`. |

## Sensitivity classes

- **low** — safe to appear in logs, images, and dashboards.
- **high** — never log, never include in error messages, never commit.

## Config validation at boot

Each service should fail fast when required vars are missing:

- Python: `src/config.py` raises `ConfigError` with the list.
- Go: `envOrDefault` for optional; `envOrDie` for required.
- Ruby: `ENV.fetch(name)` (no default) in `Config.new`.

On startup, emit a redacted summary so ops can verify which secrets are
wired without exposing them:

```
[boot] secrets loaded: POSTGRES_PASSWORD=*** ANTHROPIC_API_KEY=sk-ant-***
```

## Never commit

- `.env` (only `.env.example` with placeholders).
- Real credentials in `docker-compose.yml` (use `${VAR}` substitutions).
- TLS private keys (see issue #3).

## Platforms

- **Railway** / **Render** — set env vars via platform dashboard. `railway.toml`
  and `render.yaml` in the repo wire service definitions only, never secrets.
- **Production target** — cloud KMS or HashiCorp Vault. Rotate TWILIO and
  ANTHROPIC keys on a schedule.
