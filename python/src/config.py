"""
Centralized configuration loaded from environment variables.
All config has sensible defaults for development.
"""

import logging
import os
from dataclasses import dataclass

log = logging.getLogger(__name__)


def redact(value: str, keep: int = 4) -> str:
    """Redact a secret for log output while keeping enough prefix to identify it."""
    if not value:
        return "<unset>"
    return value[:keep] + "***" if len(value) > keep else "***"


def log_redacted_secrets() -> None:
    """Emit a single line summarizing which secrets are set. Never logs values.

    Ops uses this to confirm configuration without exposing credentials.
    """
    secrets = [
        "POSTGRES_PASSWORD",
        "ANTHROPIC_API_KEY",
        "TWILIO_AUTH_TOKEN",
        "SENDGRID_API_KEY",
        "MLS_RESO_API_KEY",
        "REDIS_URL",
    ]
    parts = []
    for name in secrets:
        v = os.environ.get(name, "")
        status = "set" if v else "missing"
        parts.append(f"{name}={status}")
    log.info("secrets loaded: %s", " ".join(parts))


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    name: str

    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass(frozen=True)
class ServiceConfig:
    name: str
    grpc_port: int
    http_port: int
    log_level: str
    log_format: str  # "text" or "json"
    db: DatabaseConfig

    @classmethod
    def from_env(cls, service_name: str = "") -> "ServiceConfig":
        name = service_name or os.environ.get("SERVICE_NAME", "brain")
        db_name_key = f"{name.upper()}_DB"
        return cls(
            name=name,
            grpc_port=int(os.environ.get("GRPC_PORT", "50053")),
            http_port=int(os.environ.get("HTTP_PORT", "8082")),
            log_level=os.environ.get("LOG_LEVEL", "info"),
            log_format=os.environ.get("LOG_FORMAT", "text"),
            db=DatabaseConfig(
                host=os.environ.get("POSTGRES_HOST", "localhost"),
                port=int(os.environ.get("POSTGRES_PORT", "5432")),
                user=os.environ.get("POSTGRES_USER", "hearth"),
                password=os.environ.get("POSTGRES_PASSWORD", "hearth_dev"),
                name=os.environ.get(db_name_key, f"hearth_{name}"),
            ),
        )


@dataclass(frozen=True)
class GRPCClientConfig:
    """Config for connecting to another service."""
    host: str
    port: int

    @property
    def target(self) -> str:
        return f"{self.host}:{self.port}"

    @classmethod
    def for_service(cls, service_name: str) -> "GRPCClientConfig":
        upper = service_name.upper()
        return cls(
            host=os.environ.get(f"{upper}_GRPC_HOST", "localhost"),
            port=int(os.environ.get(f"{upper}_GRPC_PORT", "50053")),
        )
