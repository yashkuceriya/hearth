"""
gRPC server entry point for Brain and Lawyer services.
Determines which service to run based on SERVICE_NAME env var.
Includes health checking, graceful shutdown, and structured logging.
"""

import os
import sys
import signal
import logging
import json
from concurrent import futures
from datetime import datetime, timezone

import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc
from grpc_health.v1.health import HealthServicer

# Configure structured JSON logging for production
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": os.environ.get("SERVICE_NAME", "unknown"),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging():
    level = os.environ.get("LOG_LEVEL", "info").upper()
    handler = logging.StreamHandler(sys.stdout)
    if os.environ.get("LOG_FORMAT") == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
    logging.basicConfig(level=getattr(logging, level, logging.INFO), handlers=[handler])


def create_server(service_name: str, port: int) -> grpc.Server:
    """Create a gRPC server with health checking."""
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )

    # Health check service
    health_servicer = HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set(service_name, health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)

    server.add_insecure_port(f"0.0.0.0:{port}")
    return server


def serve():
    setup_logging()
    logger = logging.getLogger(__name__)

    service_name = os.environ.get("SERVICE_NAME", "brain")
    grpc_port = int(os.environ.get("GRPC_PORT", "50053"))

    logger.info(f"Starting {service_name} service on port {grpc_port}")

    server = create_server(service_name, grpc_port)

    # Graceful shutdown handler
    shutdown_event = False

    def handle_signal(signum, frame):
        nonlocal shutdown_event
        if not shutdown_event:
            shutdown_event = True
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            server.stop(grace=5)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    server.start()
    logger.info(f"{service_name} service started on port {grpc_port}")

    server.wait_for_termination()
    logger.info(f"{service_name} service stopped")


if __name__ == "__main__":
    serve()
